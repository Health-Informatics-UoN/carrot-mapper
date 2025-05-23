from typing import List, Tuple, Any, Dict
from libs.enums import JobStageType, StageStatusType
from libs.utils import update_job_status
import json
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from io import BytesIO
from airflow.providers.postgres.hooks.postgres import PostgresHook
import io
import csv
from datetime import date

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def build_rules_json(scan_report_name: str, scan_report_id: int) -> BytesIO:
    """
    Builds the rules in JSON format.
    """
    #  Build the metadata for the JSON file
    metadata = {
        "dataset": scan_report_name,
        "date_created": datetime.now().isoformat(),
    }
    #  Get the all processed rules from the temp table as dataframe in Pandas
    processed_rules = pg_hook.get_pandas_df(
        "SELECT * FROM temp_rules_export_%(scan_report_id)s;",
        parameters={"scan_report_id": scan_report_id},
    )

    result: Dict[str, Any] = {}
    for _, row in processed_rules.iterrows():
        dest_table = row["dest_table"]
        concept_key = f"{row['concept_name']} {row['sr_concept_id']}"
        dest_field = row["dest_field"]
        source_table = row["source_table"]
        source_field = row["source_field"]

        # Prepare the term_mapping value
        # will solve #1006 here, then assign term_mapping step below
        if pd.notnull(row["term_mapping_value"]):
            term_mapping = {row["term_mapping_value"]: row["concept_id"]}
        else:
            term_mapping = row["concept_id"]

        # Build the field entry
        field_entry = {"source_table": source_table, "source_field": source_field}
        # Assign term_mapping
        if pd.notnull(row["term_mapping_value"]) and dest_field.endswith("_concept_id"):
            field_entry["term_mapping"] = term_mapping

        result.setdefault(dest_table, {}).setdefault(concept_key, {})[
            dest_field
        ] = field_entry

    cdm = {
        "metadata": metadata,
        "cdm": result,
    }
    json_data = json.dumps(cdm, indent=6)
    print(json_data)
    json_bytes = BytesIO(json_data.encode("utf-8"))
    json_bytes.seek(0)
    return json_bytes


def build_rules_csv(scan_report_id: int) -> io.StringIO:
    """
    Gets Mapping Rules in csv format.

    Args:
        - qs (QuerySet[MappingRule]) queryset of Mapping Rules.

    Returns:
        - Mapping rules as StringIO.
    """

    update_temp_rules_table_query = """
        UPDATE temp_rules_export_%(scan_report_id)s AS temp_rules
        SET temp_rules.domain = omop_concept.domain_id,
            temp_rules.standard_concept = omop_concept.standard_concept,
            temp_rules.concept_class = omop_concept.concept_class_id,
            temp_rules.vocabulary = omop_concept.vocabulary_id,
            temp_rules.valid_start_date = omop_concept.valid_start_date,
            temp_rules.valid_end_date = omop_concept.valid_end_date,
        FROM omop_concept
        WHERE temp_rules.concept_id = omop_concept.concept_id;
    """
    pg_hook.run(
        update_temp_rules_table_query, parameters={"scan_report_id": scan_report_id}
    )
    #  Get the all processed rules from the temp table as dataframe in Pandas
    processed_rules = pg_hook.get_pandas_df(
        "SELECT * FROM temp_rules_export_%(scan_report_id)s;",
        parameters={"scan_report_id": scan_report_id},
    )
    # make a string buffer
    _buffer = io.StringIO()
    # setup a csv writter
    writer = csv.writer(
        _buffer,
        lineterminator="\n",
        delimiter=",",
        quoting=csv.QUOTE_MINIMAL,
    )

    # setup the headers from the first object
    # replace term_mapping ({'source_value':'concept'}) with separate columns
    headers = [
        "source_table",
        "source_field",
        "source_value",
        "concept_id",
        "omop_term",
        "class",
        "concept",
        "validity",
        "domain",
        "vocabulary",
        "creation_type",
        "rule_id",
        "isFieldMapping",
    ]

    # write the headers to the csv
    writer.writerow(headers)

    # Get the current date to check validity
    today = date.today()

    # loop over the content
    for _, row in processed_rules.iterrows():
        # Use .get or direct attribute access for pandas Series
        destination_table = row.get("dest_table", "")
        domain = row.get("domain", "")
        source_table = row.get("source_table", "")
        source_field = row.get("source_field", "")
        omop_term = row.get("concept_name", "")
        concept_id = row.get("concept_id", "")
        creation_type = row.get("creation_type", "")
        rule_id = row.get("sr_concept_id", "")

        # Handle term_mapping
        term_mapping_value = row.get("term_mapping_value", None)
        isFieldMapping = ""
        source_value = ""
        concept_id_out = ""
        if pd.isnull(term_mapping_value):
            source_value = ""
            concept_id_out = ""
        else:
            source_value = term_mapping_value
            concept_id_out = concept_id
            isFieldMapping = "0" if source_value else "1"

        # Validity check
        validity = (
            row.get("valid_start_date", "") <= today < row.get("valid_end_date", "")
        )
        # Vocabulary id
        vocabulary = row.get("vocabulary", "")
        # Standard concept or not?
        concept = row.get("standard_concept", "")
        # Concept class
        concept_class = row.get("concept_class", "")

        content_out = [
            source_table,
            source_field,
            source_value,
            concept_id_out,
            omop_term,
            concept_class,
            concept,
            validity,
            domain,
            vocabulary,
            creation_type,
            rule_id,
            isFieldMapping,
        ]
        writer.writerow(content_out)

    _buffer.seek(0)
    return _buffer
