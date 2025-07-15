from typing import Any, Dict, List
from libs.enums import JobStageType, StageStatusType
from libs.utils import update_job_status
import json
import pandas as pd
from datetime import datetime, timezone
from io import BytesIO
from airflow.providers.postgres.hooks.postgres import PostgresHook
import io
import csv
from datetime import date
import logging

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def build_rules_csv(scan_report_id: int) -> BytesIO:
    """
    Builds the rules in CSV format.

    Args:
        - scan_report_id: int, the id of the scan report

    Returns:
        - BytesIO, the rules in CSV format
    """
    try:
        #  Update the temp table with the concept information (only for CSV file generation)
        update_temp_rules_table_query = """
            UPDATE temp_rules_export_%(scan_report_id)s_csv AS temp_rules
            SET domain = omop_concept.domain_id,
                standard_concept = omop_concept.standard_concept,
                concept_class = omop_concept.concept_class_id,
                vocabulary = omop_concept.vocabulary_id,
                valid_start_date = omop_concept.valid_start_date,
                valid_end_date = omop_concept.valid_end_date
            FROM omop.concept AS omop_concept
            WHERE temp_rules.concept_id = omop_concept.concept_id;
        """
        pg_hook.run(
            update_temp_rules_table_query, parameters={"scan_report_id": scan_report_id}
        )
        #  Get the all processed rules from the temp table as dataframe in Pandas
        processed_rules = pg_hook.get_pandas_df(
            "SELECT * FROM temp_rules_export_%(scan_report_id)s_csv ORDER BY sr_concept_id;",
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
            domain = row.get("domain", "")
            rule_id = row.get("sr_concept_id", "")
            creation_type = row.get("creation_type", "")
            source_table = row.get("source_table", "")
            source_field = row.get("source_field", "")
            omop_term = row.get("concept_name", "")
            source_value = ""
            concept_id = ""
            concept_class = ""
            concept = ""
            validity = ""
            vocabulary = ""
            isFieldMapping = ""

            concept_related_rule = (
                True if row.get("dest_field", "").endswith("_concept_id") else False
            )

            if concept_related_rule:
                concept_id = row.get("concept_id", "")
                concept_class = row.get("concept_class", "")
                concept = row.get("standard_concept", "")
                validity = (
                    row.get("valid_start_date", "")
                    <= today
                    < row.get("valid_end_date", "")
                )
                vocabulary = row.get("vocabulary", "")
                source_value = row.get("term_mapping_value", "")
                isFieldMapping = "0" if source_value else "1"

            content_out = [
                source_table,
                source_field,
                source_value,
                concept_id,
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
        return io.BytesIO(_buffer.getvalue().encode("utf-8"))
    except Exception as e:
        logging.error(f"Error building rules CSV: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Error building rules CSV for scan report {scan_report_id}: {str(e)}",
        )
        raise e


def build_rules_json(scan_report_name: str, scan_report_id: int) -> BytesIO:
    """
    Builds the rules in JSON format.

    Args:
        - scan_report_name: str, the name of the scan report
        - scan_report_id: int, the id of the scan report

    Returns:
        - BytesIO, the rules in JSON format
    """
    try:
        #  Build the metadata for the JSON file
        metadata = {
            "date_created": datetime.now(timezone.utc).isoformat(),
            "dataset": scan_report_name,
        }
        #  Get the all processed rules from the temp table as dataframe in Pandas
        processed_rules = pg_hook.get_pandas_df(
            "SELECT * FROM temp_rules_export_%(scan_report_id)s_json ORDER BY sr_concept_id;",
            parameters={"scan_report_id": scan_report_id},
        )

        result: Dict[str, Any] = {}
        for _, row in processed_rules.iterrows():
            dest_table = row["dest_table"]
            concept_key = f"{row['concept_name']} {row['sr_concept_id']}"
            dest_field = row["dest_field"]
            source_table = row["source_table"].replace("\ufeff", "")
            source_field = row["source_field"].replace("\ufeff", "")

            # Prepare the term_mapping value
            # will solve #1006 here (fields end with source_concept_id and concept_id will have different values),
            # then assign term_mapping step below
            if pd.notnull(row["term_mapping_value"]):
                term_mapping = {row["term_mapping_value"]: row["concept_id"]}
            else:
                term_mapping = row["concept_id"]

            # Build the field entry
            field_entry = {"source_table": source_table, "source_field": source_field}
            # Assign term_mapping
            if dest_field.endswith("_concept_id"):
                field_entry["term_mapping"] = term_mapping

            result.setdefault(dest_table, {}).setdefault(concept_key, {})[
                dest_field
            ] = field_entry

        cdm = {
            "metadata": metadata,
            "cdm": result,
        }
        json_data = json.dumps(cdm, indent=6)
        json_bytes = BytesIO(json_data.encode("utf-8"))
        json_bytes.seek(0)
        return json_bytes
    except Exception as e:
        logging.error(f"Error building rules JSON: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Error building rules JSON for scan report {scan_report_id}: {str(e)}",
        )
        raise e


def build_rules_json_v2(scan_report_name: str, scan_report_id: int) -> BytesIO:
    try:
        metadata = {
            "date_created": datetime.now(timezone.utc).isoformat(),
            "dataset": scan_report_name,
        }

        processed_rules = pg_hook.get_pandas_df(
            "SELECT * FROM temp_rules_export_%(scan_report_id)s_json ORDER BY dest_table, source_table, source_field;",
            parameters={"scan_report_id": scan_report_id},
        )

        result: Dict[str, Any] = {}

        for dest_table, dest_table_group in processed_rules.groupby("dest_table"):
            dest_table_str = str(dest_table)
            result[dest_table_str] = {}

            for source_table, source_table_group in dest_table_group.groupby(
                "source_table"
            ):
                source_table_clean = str(source_table).replace("\ufeff", "")
                result[dest_table_str][source_table_clean] = {}

                person_id_mappings = {}
                date_mappings = {}
                concept_mappings = {}

                for source_field, source_field_group in source_table_group.groupby(
                    "source_field"
                ):
                    source_field_clean = str(source_field).replace("\ufeff", "")
                    dest_fields = source_field_group["dest_field"].dropna().unique()

                    # forming the person_id_mapping
                    if "person_id" in [d.lower() for d in dest_fields]:
                        person_id_mappings = {
                            "source_field": source_field_clean,
                            "dest_field": "person_id",
                        }

                    # forming the date_mapping
                    date_like_fields = [
                        d
                        for d in dest_fields
                        if d and d.lower().endswith(("date", "datetime"))
                    ]
                    if date_like_fields:
                        date_mappings = {
                            "source_field": source_field_clean,
                            "dest_field": date_like_fields,
                        }

                    is_measurement_observation_table = dest_table_str in [
                        "measurement",
                        "observation",
                    ]
                    field_level_mappings: Dict[str, List[int]] = {}
                    value_level_mappings: Dict[str, Dict[str, List[int]]] = {}

                    only_field_mappings = True
                    only_value_mappings = True

                    for _, row in source_field_group.iterrows():
                        dest_field = row["dest_field"]
                        concept_id = row["concept_id"]
                        term_mapping_value = row.get("term_mapping_value")

                        # Solved #1006 here
                        if pd.notnull(term_mapping_value):
                            only_field_mappings = False
                            if term_mapping_value not in value_level_mappings:
                                value_level_mappings[term_mapping_value] = {}
                            if dest_field.endswith("_concept_id"):
                                # initialize the dest_field if not exists
                                if (
                                    dest_field
                                    not in value_level_mappings[term_mapping_value]
                                ):
                                    value_level_mappings[term_mapping_value][
                                        dest_field
                                    ] = []
                                value_level_mappings[term_mapping_value][
                                    dest_field
                                ].append(concept_id)
                        else:
                            only_value_mappings = False
                            if dest_field.endswith("_concept_id"):
                                # initialize the dest_field if not exists
                                if dest_field not in field_level_mappings:
                                    field_level_mappings[dest_field] = []
                                field_level_mappings[dest_field].append(concept_id)

                    concept_mapping: Dict[str, Any] = {}

                    # Forming the concept_mapping based on the mapping types
                    if only_field_mappings:
                        # Field-only mappings: put everything under "*" key
                        concept_mapping["*"] = field_level_mappings

                    elif only_value_mappings:
                        # Value-only mappings: put each value as direct key
                        for value, mappings in value_level_mappings.items():
                            if mappings:
                                concept_mapping[value] = mappings

                    else:
                        # Mixed mappings: "*" key for field-level + individual value keys
                        # NOTE: If there are mappings at the date/pseron field and value_as_concept_id field taken into account,
                        # it will be mixed mappings automatically, which will cause issues, so we need to have a way to add this mixed case in one of the above types
                        concept_mapping["*"] = field_level_mappings

                        # For each value, create its own mapping
                        for value, value_mappings in value_level_mappings.items():
                            if value_mappings:
                                concept_mapping[value] = value_mappings

                    # Forming the original_value field
                    original_values = [
                        f for f in dest_fields if f.endswith("_source_value")
                    ]
                    # Add value_as_string/number for tables observation and measurement
                    if is_measurement_observation_table:
                        if "value_as_string" in dest_fields:
                            original_values.append("value_as_string")
                        if "value_as_number" in dest_fields:
                            original_values.append("value_as_number")
                    # Add original_value field with unique values
                    concept_mapping["original_value"] = list(set(original_values))

                    # for a mappings of a source field group to be appear in the result, it must have original_value
                    # (which should always have at least one _source_value field)
                    if concept_mapping and concept_mapping.get("original_value"):
                        concept_mappings[source_field_clean] = concept_mapping

                # Adding the person_id_mapping, date_mapping, concept_mapping to the result
                if person_id_mappings:
                    result[dest_table_str][source_table_clean][
                        "person_id_mapping"
                    ] = person_id_mappings

                if date_mappings:
                    result[dest_table_str][source_table_clean][
                        "date_mapping"
                    ] = date_mappings

                if concept_mappings:
                    result[dest_table_str][source_table_clean][
                        "concept_mappings"
                    ] = concept_mappings

        cdm = {
            "metadata": metadata,
            "cdm": result,
        }

        json_data = json.dumps(cdm, indent=2)
        json_bytes = BytesIO(json_data.encode("utf-8"))
        json_bytes.seek(0)
        return json_bytes

    except Exception as e:
        logging.error(f"Error building rules JSON v2: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Error building rules JSON v2 for scan report {scan_report_id}: {str(e)}",
        )
        raise e
