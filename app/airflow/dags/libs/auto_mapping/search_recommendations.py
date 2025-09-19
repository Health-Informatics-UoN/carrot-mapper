import logging

from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.settings import AIRFLOW_DAGRUN_TIMEOUT
from libs.utils import (
    pull_validated_params,
)

# PostgreSQL connection hook
pg_hook = PostgresHook(
    postgres_conn_id="postgres_db_conn",
    options=f"-c statement_timeout={float(AIRFLOW_DAGRUN_TIMEOUT) * 60 * 1000}ms",
)


def process_search_recommendations(**kwargs) -> None:
    """
    Process search recommendations for a given scan report table.

    This function:
    1. Retrieves scan report value strings and searches the OMOP concept table using ILIKE queries
    2. Selects the top 3 matches for each value
    3. Inserts them as MappingRecommendations into the database

    Parameters are validated upstream in validate_params_auto_mapping task.
    """
    # Get validated parameters from XCom
    validated_params = pull_validated_params(kwargs, "validate_params_auto_mapping")

    table_id = validated_params["table_id"]

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
            sr_value.value
        FROM mapping_scanreportvalue sr_value
        JOIN mapping_scanreportfield sr_field ON sr_value.scan_report_field_id = sr_field.id
        WHERE sr_field.scan_report_table_id = %(table_id)s
          AND sr_value.value IS NOT NULL 
          AND TRIM(sr_value.value) <> ''
        """

        logging.info(f"Getting scan report values for table_id: {table_id}")
        values = pg_hook.get_records(
            get_values_query, parameters={"table_id": table_id}
        )

        if not values:
            logging.info(f"No values found for table {table_id}")
            return

        # Process each value with individual queries
        # This is more efficient for large concept tables because:
        # 1. Each query has LIMIT 3, stopping early
        # 2. No cross-join with 1.9M concept records
        # 3. Database can optimize each focused query
        recommendations_created = 0
        for value_id, value_string in values:
            try:
                # Search OMOP concepts using ILIKE with LIMIT 3
                # This is more efficient than cross-join approach
                search_query = """
                SELECT concept_id
                FROM omop.concept 
                WHERE concept_name ILIKE %(search_term)s
                  AND invalid_reason IS NULL
                  AND standard_concept = 'S'
                ORDER BY concept_name
                LIMIT 3
                """

                matches = pg_hook.get_records(
                    search_query, parameters={"search_term": f"%{value_string}%"}
                )

                if matches:
                    # Insert recommendations for each match
                    for (concept_id,) in matches:
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

    except Exception as e:
        logging.error(f"Error in process_search_recommendations: {str(e)}")
        raise
