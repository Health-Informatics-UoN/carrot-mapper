from libs.utils import (
    JobStageType,
    StageStatusType,
    pull_validated_params,
)
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def process_search_recommendations(**kwargs) -> None:
    """
    Process search recommendations for a given scan report table.

    This function:
    1. Retrieves scan report value strings
    2. Searches the OMOP concept table using ILIKE queries
    3. Selects the top 3 matches for each value
    4. Inserts them as MappingRecommendations into the database

    Parameters are validated upstream in validate_params_auto_mapping task.
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")

    if not validated_params:
        logging.error(
            "No validated parameters found. Task may not be running in proper DAG context."
        )
        raise ValueError(
            "No validated parameters found. Task requires parameters from validate_params_auto_mapping task."
        )

    scan_report_id = validated_params["scan_report_id"]
    table_id = validated_params["table_id"]

    logging.info(
        f"Processing search recommendations for scan_report_id: {scan_report_id}, table_id: {table_id}"
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

        # Single optimized query to get all values and their concept matches
        search_recommendations_query = """
        WITH value_concepts AS (
            SELECT 
                sr_value.id as value_id,
                sr_value.value as value_string,
                concept.concept_id,
                concept.concept_name,
                concept.concept_code,
                concept.vocabulary_id,
                concept.domain_id,
                ROW_NUMBER() OVER (
                    PARTITION BY sr_value.id 
                    ORDER BY concept.concept_name
                ) as rn
            FROM mapping_scanreportvalue sr_value
            JOIN mapping_scanreportfield sr_field ON sr_value.scan_report_field_id = sr_field.id
            CROSS JOIN LATERAL (
                SELECT 
                    concept_id,
                    concept_name,
                    concept_code,
                    vocabulary_id,
                    domain_id
                FROM omop.concept 
                WHERE concept_name ILIKE CONCAT('%%', sr_value.value, '%%')
                  AND invalid_reason IS NULL
                  AND standard_concept = 'S'
                ORDER BY concept_name
                LIMIT 3
            ) concept
            WHERE sr_field.scan_report_table_id = %(table_id)s
              AND sr_value.value IS NOT NULL 
              AND TRIM(sr_value.value) <> ''
        )
        SELECT 
            value_id,
            value_string,
            concept_id,
            concept_name,
            concept_code,
            vocabulary_id,
            domain_id
        FROM value_concepts
        WHERE rn <= 3
        ORDER BY value_id, concept_name
        """

        logging.info(f"Executing optimized 2-query search for table_id: {table_id}")
        matches = pg_hook.get_records(
            search_recommendations_query, parameters={"table_id": table_id}
        )

        if not matches:
            logging.info(f"No matches found for table {table_id}")
            return

        logging.info(f"Found {len(matches)} concept matches to process")

        # Batch insert all recommendations
        insert_query = """
        INSERT INTO mapping_mappingrecommendation (
            content_type_id,
            object_id,
            concept_id,
            score,
            tool_name,
            tool_version,
            created_at,
            updated_at
        ) VALUES (
            %(content_type_id)s,
            %(object_id)s,
            %(concept_id)s,
            %(score)s,
            %(tool_name)s,
            %(tool_version)s,
            NOW(),
            NOW()
        )
        """

        recommendations_created = 0
        for (
            value_id,
            value_string,
            concept_id,
            concept_name,
            concept_code,
            vocabulary_id,
            domain_id,
        ) in matches:
            try:
                pg_hook.run(
                    insert_query,
                    parameters={
                        "content_type_id": content_type_id,
                        "object_id": value_id,
                        "concept_id": concept_id,
                        "score": 0.5,  # Base score for ILIKE matches
                        "tool_name": "string-search",
                        "tool_version": "1.0.0",
                    },
                )
                recommendations_created += 1
                logging.info(
                    f"Created recommendation: value '{value_string}' -> concept '{concept_name}' (ID: {concept_id})"
                )
            except Exception as e:
                logging.error(
                    f"Error inserting recommendation for value '{value_string}' -> concept '{concept_name}': {str(e)}"
                )
                continue

        logging.info(
            f"Successfully created {recommendations_created} search recommendations"
        )

    except Exception as e:
        logging.error(f"Error in process_search_recommendations: {str(e)}")
        raise
