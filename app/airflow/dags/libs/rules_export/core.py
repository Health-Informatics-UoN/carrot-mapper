import logging
from libs.utils import pull_validated_params
from airflow.providers.postgres.hooks.postgres import PostgresHook
from libs.type import FileHandlerConfig
from libs.rules_export.file_services import build_rules_json
from typing import Dict
from datetime import datetime

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def process_rules_export(**kwargs) -> None:
    """
    Wrapper function for the rules export processing task using openpyxl

    Args:
        context: Airflow context containing task information

    Returns:
        None
    """

    validated_params = pull_validated_params(kwargs, "validate_params_rules_export")
    scan_report_id = validated_params["scan_report_id"]
    user_id = validated_params["user_id"]
    file_type = validated_params["file_type"]

    create_temp_rules_table_query = """
        DROP TABLE IF EXISTS temp_rules_export_%(scan_report_id)s;
        CREATE TABLE temp_rules_export_%(scan_report_id)s (
            sr_concept_id INT,
            concept_name TEXT,
            concept_id INT,
            dest_field TEXT,
            dest_table TEXT,
            source_field TEXT,
            source_table TEXT,
            term_mapping_value TEXT,
            domain TEXT,
            standard_concept TEXT,
            concept_class TEXT,
            vocabulary TEXT,
            valid_start_date DATE,
            valid_end_date DATE,
            creation_type TEXT
        );
        INSERT INTO temp_rules_export_%(scan_report_id)s (
            sr_concept_id,
            concept_name,
            concept_id,
            dest_field,
            dest_table,
            source_field,
            source_table,
            term_mapping_value
        )
        SELECT
            mapping_rule.concept_id AS sr_concept_id,
            omop_concept.concept_name,
            sr_concept.concept_id,
            omop_field.field AS dest_field,
            omop_table.table AS dest_table,
            sr_field.name AS source_field,
            sr_table.name AS source_table,
            CASE
                WHEN sr_concept.content_type_id = 23 THEN sr_value.value
                ELSE NULL
            END AS term_mapping_value
        FROM mapping_mappingrule AS mapping_rule
        JOIN mapping_omopfield AS omop_field ON mapping_rule.omop_field_id = omop_field.id
        JOIN mapping_omoptable AS omop_table ON omop_field.table_id = omop_table.id
        JOIN mapping_scanreportfield AS sr_field ON mapping_rule.source_field_id = sr_field.id
        JOIN mapping_scanreporttable AS sr_table ON sr_field.scan_report_table_id = sr_table.id
        JOIN mapping_scanreportconcept AS sr_concept ON mapping_rule.concept_id = sr_concept.id
        LEFT JOIN mapping_scanreportvalue AS sr_value ON sr_concept.object_id = sr_value.id AND sr_concept.content_type_id = 23
        LEFT JOIN omop.concept AS omop_concept ON sr_concept.concept_id = omop_concept.concept_id
        WHERE mapping_rule.scan_report_id = %(scan_report_id)s;
    """

    pg_hook.run(
        create_temp_rules_table_query, parameters={"scan_report_id": scan_report_id}
    )
    temp_table = f"temp_rules_export_{scan_report_id}"
    query = f"SELECT * FROM {temp_table};"
    df = pg_hook.get_pandas_df(query)

    # Setup file config
    file_handlers: Dict[str, FileHandlerConfig] = {
        # "text/csv": FileHandlerConfig(
        #     lambda rules: create_csv_rules(rules), "mapping_csv", "csv"
        # ),
        "application/json": FileHandlerConfig(
            lambda rules: build_rules_json(rules), "mapping_json", "json"
        ),
    }

    config = file_handlers[file_type]

    # Generate it
    file = config.handler(df)
    file_type_value = config.file_type_value
    file_extension = config.file_extension

    # Save to blob
    # TODO: get the SR name from config to put in here and the meta data of the json
    filename = f"Rules - test - {scan_report_id} - {datetime.now()}.{file_extension}"
