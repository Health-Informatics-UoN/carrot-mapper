from libs.utils import (
    update_job_status,
    JobStageType,
    StageStatusType,
    pull_validated_params,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from django.contrib.contenttypes.models import ContentType

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def validate_params_search_recommendations(**kwargs) -> None:
    """
    Validate parameters for the search recommendations DAG.
    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    """
    from libs.utils import _validate_dag_params

    _validate_dag_params(int_params=["scan_report_id", "table_id"], **kwargs)


def process_search_recommendations(**kwargs) -> None:
    """
    Process search recommendations for a given scan report table.

    This function:
    1. Retrieves scan report value strings
    2. Searches the OMOP concept table using ILIKE queries
    3. Selects the top 3 matches for each value
    4. Inserts them as MappingRecommendations into the database

    Validated params needed are:
    - scan_report_id (int): The ID of the scan report to process
    - table_id (int): The ID of the scan report table to process
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(
        kwargs, "validate_params_search_recommendations"
    )
    scan_report_id = validated_params["scan_report_id"]
    table_id = validated_params["table_id"]

    update_job_status(
        scan_report=scan_report_id,
        scan_report_table=table_id,
        stage=JobStageType.GENERATE_RULES,
        status=StageStatusType.IN_PROGRESS,
        details="Generating search-based mapping recommendations",
    )

    try:
        # Get content type for ScanReportValue
        content_type_query = """
        SELECT id FROM django_content_type 
        WHERE app_label = 'mapping' AND model = 'scanreportvalue'
        LIMIT 1
        """
        content_type_result = pg_hook.get_first(content_type_query)
        if not content_type_result:
            raise ValueError("Could not find content type for ScanReportValue")
        content_type_id = content_type_result[0]

        # Get all scan report values for the table
        get_values_query = """
        SELECT 
            sr_value.id,
            sr_value.value,
            sr_value.scan_report_field_id
        FROM mapping_scanreportvalue sr_value
        JOIN mapping_scanreportfield sr_field ON sr_value.scan_report_field_id = sr_field.id
        WHERE sr_field.scan_report_table_id = %(table_id)s
          AND sr_value.value IS NOT NULL 
          AND TRIM(sr_value.value) <> ''
        """

        values = pg_hook.get_records(
            get_values_query, parameters={"table_id": table_id}
        )

        if not values:
            logging.info(f"No values found for table {table_id}")
            update_job_status(
                scan_report=scan_report_id,
                scan_report_table=table_id,
                stage=JobStageType.GENERATE_RULES,
                status=StageStatusType.COMPLETE,
                details="No values found for search recommendations",
            )
            return

        logging.info(
            f"Found {len(values)} values to process for search recommendations"
        )

        # Process each value
        recommendations_created = 0
        for value_id, value_string, field_id in values:
            try:
                # Search OMOP concepts using ILIKE
                search_query = """
                SELECT 
                    concept_id,
                    concept_name,
                    concept_code,
                    vocabulary_id,
                    domain_id
                FROM omop.concept 
                WHERE concept_name ILIKE %(search_term)s
                  AND invalid_reason IS NULL
                ORDER BY concept_name
                LIMIT 3
                """

                search_term = f"%{value_string}%"
                matches = pg_hook.get_records(
                    search_query, parameters={"search_term": search_term}
                )

                if matches:
                    # Insert recommendations for each match
                    for (
                        concept_id,
                        concept_name,
                        concept_code,
                        vocabulary_id,
                        domain_id,
                    ) in matches:
                        insert_query = """
                        INSERT INTO mapping_mappingrecommendation (
                            content_type_id,
                            object_id,
                            concept_id,
                            score,
                            tool_name,
                            tool_version
                        ) VALUES (
                            %(content_type_id)s,
                            %(object_id)s,
                            %(concept_id)s,
                            %(score)s,
                            %(tool_name)s,
                            %(tool_version)s
                        )
                        ON CONFLICT (content_type_id, object_id, concept_id) 
                        DO NOTHING
                        """

                        # Calculate a simple score based on string similarity
                        # For now, use a basic score - could be enhanced with more sophisticated matching
                        score = 0.5  # Base score for ILIKE matches

                        pg_hook.run(
                            insert_query,
                            parameters={
                                "content_type_id": content_type_id,
                                "object_id": value_id,
                                "concept_id": concept_id,
                                "score": score,
                                "tool_name": "string-search",
                                "tool_version": "1.0.0",
                            },
                        )

                        recommendations_created += 1

                    logging.info(
                        f"Created {len(matches)} recommendations for value '{value_string}'"
                    )
                else:
                    logging.info(f"No matches found for value '{value_string}'")

            except Exception as e:
                logging.error(f"Error processing value '{value_string}': {str(e)}")
                # Continue with next value instead of failing the entire process
                continue

        logging.info(
            f"Successfully created {recommendations_created} search recommendations"
        )

        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.COMPLETE,
            details=f"Created {recommendations_created} search-based mapping recommendations",
        )

    except Exception as e:
        logging.error(f"Error in process_search_recommendations: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            scan_report_table=table_id,
            stage=JobStageType.GENERATE_RULES,
            status=StageStatusType.FAILED,
            details=f"Error generating search recommendations: {str(e)}",
        )
        raise
