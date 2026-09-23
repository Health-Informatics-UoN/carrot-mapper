import logging

from airflow.exceptions import AirflowException
from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.settings import AIRFLOW_DAGRUN_TIMEOUT
from libs.utils import (
    JobStageType,
    StageStatusType,
    pull_validated_params,
    update_job_status,
)

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


def find_matched_concepts(**kwargs) -> None:
    """
    Maps source field values to OMOP concepts by case-insensitive name match, scoped
    to a domain configured per-field in the data dictionary (see issue #983).

    Unlike the vocabulary-based lookup (find_standard_V_concepts.py), this doesn't
    require a vocabulary/code match - it looks up each distinct source value's term
    directly against `concept_name` within the given domain, e.g. a source value
    "CYTARABINE" on a field configured with domain "Drug" is matched to the standard
    Drug concept named "Cytarabine".

    This is intentionally a simple, deterministic exact match for now. If a term
    matches more than one standard concept in the domain, one is picked
    deterministically (lowest concept_id). The `mapping_tool`/`mapping_tool_version`
    fields on ScanReportConcept are the intended seam for a future, smarter (fuzzy or
    AI-based) matcher without needing another creation_type.

    Creates a temporary table to store mapping information between source values and
    matched concepts. For each field-domain pair provided, finds corresponding
    concepts in the OMOP vocabulary and inserts them into the temporary table.
    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    - field_domain_pairs (list): List of dictionaries containing field-domain pairs
        For example:
        "field_domain_pairs": [
            {
                "sr_field_id": "437",
                "field_data_type": "VARCHAR",
                "domain_id": "Drug"
            }
        ]
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")

    field_domain_pairs = validated_params["field_domain_pairs"]
    if not field_domain_pairs:
        logging.info("Skipped, no field-domain pairs provided")
        update_job_status(
            scan_report=validated_params["scan_report_id"],
            scan_report_table=validated_params["table_id"],
            stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
            status=StageStatusType.COMPLETE,
            details="Skipped, no field-domain pairs provided",
        )
    else:
        scan_report_id = validated_params["scan_report_id"]
        table_id = validated_params["table_id"]
        # Create the temporary table once, outside the loop, with all the columns needed
        create_table_query = """
        -- Prevent duplicate creation of the temp matched concepts table, in case of re-running the DAG after a bug fix
        DROP TABLE IF EXISTS temp_matched_concepts_%(table_id)s;
        CREATE TABLE temp_matched_concepts_%(table_id)s (
            sr_value_id INTEGER,
            standard_concept_id INTEGER
        );
        """
        try:
            pg_hook.run(create_table_query, parameters={"table_id": table_id})
            logging.info(f"Successfully created temp_matched_concepts_{table_id} table")
        except Exception as e:
            logging.error(
                f"Failed to create temp_matched_concepts_{table_id} table: {str(e)}"
            )
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.FAILED,
                details=f"Error in creating temp_matched_concepts_{table_id} table: {str(e)}",
            )
            raise

        # Process each field-domain pair
        for pair in field_domain_pairs:
            sr_field_id = pair["sr_field_id"]
            domain_id = pair["domain_id"]

            if not sr_field_id or not domain_id:
                raise AirflowException(
                    "Invalid field_domain_pair: requires sr_field_id and domain_id"
                )

            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.IN_PROGRESS,
                details=f"Finding matched concepts for field ID {sr_field_id} in domain {domain_id}",
            )
            # Match each distinct source value's term to a standard concept name in the
            # given domain, case-insensitively. When more than one concept shares the
            # same name in the domain, deterministically keep the lowest concept_id.
            find_matched_concepts_query = """
            INSERT INTO temp_matched_concepts_%(table_id)s (sr_value_id, standard_concept_id)
            SELECT DISTINCT ON (sr_value.id)
                sr_value.id AS sr_value_id,
                std_concept.concept_id AS standard_concept_id
            FROM mapping_scanreportvalue AS sr_value
            JOIN omop.concept AS std_concept ON
                LOWER(TRIM(std_concept.concept_name)) = LOWER(TRIM(sr_value.value)) AND
                std_concept.domain_id = %(domain_id)s AND
                std_concept.standard_concept = 'S' AND
                std_concept.invalid_reason IS NULL
            WHERE sr_value.scan_report_field_id = %(sr_field_id)s
            ORDER BY sr_value.id, std_concept.concept_id;
            """
            try:
                pg_hook.run(
                    find_matched_concepts_query,
                    parameters={
                        "table_id": table_id,
                        "sr_field_id": sr_field_id,
                        "domain_id": domain_id,
                    },
                )
                logging.info(
                    f"Successfully inserted matched concepts for field ID {sr_field_id}"
                )
            except Exception as e:
                logging.error(
                    f"Failed to insert matched concepts for field ID {sr_field_id}: {str(e)}"
                )
                update_job_status(
                    scan_report=scan_report_id,
                    scan_report_table=table_id,
                    stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                    status=StageStatusType.FAILED,
                    details=f"Error in finding matched concepts for field ID {sr_field_id}: {str(e)}",
                )
                raise


def create_matched_concepts(**kwargs) -> None:
    """
    Create matched concepts for field values in the mapping_scanreportconcept table.
    Only inserts concepts that don't already exist.
    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")
    field_domain_pairs = validated_params["field_domain_pairs"]
    if not field_domain_pairs:
        logging.info("Skipped, no field-domain pairs provided")
    else:
        scan_report_id = validated_params["scan_report_id"]
        table_id = validated_params["table_id"]

        create_concept_query = """
            -- Insert matched concepts for field values (only if they don't already exist)
            INSERT INTO mapping_scanreportconcept (
                created_at,
                updated_at,
                object_id,
                creation_type,
                concept_id,
                content_type_id,
                confidence,
                mapping_tool,
                mapping_tool_version
            )
            SELECT
                NOW(),
                NOW(),
                temp_matched_concepts.sr_value_id,
                'X',           -- Creation type: Matched by term/domain lookup
                temp_matched_concepts.standard_concept_id,
                (SELECT id FROM django_content_type WHERE app_label = 'mapping' AND model = 'scanreportvalue'),
                1.0,
                'term-match',
                '1.0.0'
            FROM temp_matched_concepts_%(table_id)s AS temp_matched_concepts
            WHERE NOT EXISTS (
                -- Check if the concept already exists
                SELECT 1 FROM mapping_scanreportconcept
                WHERE object_id = temp_matched_concepts.sr_value_id
                AND concept_id = temp_matched_concepts.standard_concept_id
                AND content_type_id = (
                    SELECT id FROM django_content_type
                    WHERE app_label = 'mapping' AND model = 'scanreportvalue'
                )
            );
            """
        try:
            pg_hook.run(create_concept_query, parameters={"table_id": table_id})
            logging.info("Successfully created matched concepts")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.COMPLETE,
                details="Matched concepts successfully created from data dictionary",
            )
        except Exception as e:
            logging.error(f"Database error in create_matched_concepts: {str(e)}")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.BUILD_CONCEPTS_FROM_DICT,
                status=StageStatusType.FAILED,
                details=f"Error when creating matched concepts: {str(e)}",
            )
