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
    """
    Builds the rules in JSON format version 2 with optimized structure.

    Args:
        - scan_report_name: str, the name of the scan report
        - scan_report_id: int, the id of the scan report

    Returns:
        - BytesIO, the rules in JSON format v2
    """
    try:
        # Build the metadata for the JSON file
        metadata = {
            "date_created": datetime.now(timezone.utc).isoformat(),
            "dataset": scan_report_name,
        }

        # Get all processed rules from the temp table as dataframe in Pandas
        processed_rules = pg_hook.get_pandas_df(
            "SELECT * FROM temp_rules_export_%(scan_report_id)s_json ORDER BY dest_table, source_table, source_field;",
            parameters={"scan_report_id": scan_report_id},
        )

        result: Dict[str, Any] = {}

        # Group by destination table, source table, and source field
        for dest_table, dest_table_group in processed_rules.groupby("dest_table"):
            dest_table = str(dest_table)
            result[dest_table] = {}

            for source_table, source_table_group in dest_table_group.groupby(
                "source_table"
            ):
                source_table_clean = str(source_table).replace("\ufeff", "")
                result[dest_table][source_table_clean] = {}

                # Initialize mappings structure
                person_id_mappings = {}
                date_mappings = {}
                concept_mappings = {}

                for source_field, source_field_group in source_table_group.groupby(
                    "source_field"
                ):
                    source_field_clean = str(source_field).replace("\ufeff", "")

                    # Handle person_id mapping
                    if source_field_clean.lower() in [
                        "personid",
                        "person_id",
                        "patientid",
                        "patient_id",
                    ]:
                        person_id_dest_fields = source_field_group[
                            source_field_group["dest_field"] == "person_id"
                        ]["dest_field"].tolist()

                        if person_id_dest_fields:
                            person_id_mappings = {
                                "source_field": source_field_clean,
                                "dest_field": "person_id",
                            }

                    # Handle date mapping
                    elif source_field_clean.lower() in [
                        "date",
                        "datetime",
                        "timestamp",
                    ]:
                        date_dest_fields = (
                            source_field_group[
                                source_field_group["dest_field"].str.contains(
                                    "datetime", case=False, na=False
                                )
                            ]["dest_field"]
                            .unique()
                            .tolist()
                        )

                        if date_dest_fields:
                            date_mappings = {
                                "source_field": source_field_clean,
                                "dest_field": date_dest_fields,
                            }

                    # Handle concept mappings
                    else:
                        concept_mapping = {}

                        # Get original value fields
                        original_value_fields = (
                            source_field_group[
                                source_field_group["dest_field"].isin(
                                    [
                                        "observation_source_value",
                                        "value_as_string",
                                        "value_as_number",
                                        "measurement_source_value",
                                        # TODO: add other original value fields here
                                        # TODO: only have value_as_string/number if no value_as_concept_id
                                    ]
                                )
                            ]["dest_field"]
                            .unique()
                            .tolist()
                        )

                        if original_value_fields:
                            concept_mapping["original_value"] = original_value_fields

                        # Determine if this is measurement/observation table
                        is_measurement_observation = dest_table in [
                            "measurement",
                            "observation",
                        ]

                        # Group by term mapping value to organize mappings
                        value_mappings: Dict[str, List[Dict[str, List[int]]]] = {}
                        field_level_mappings: Dict[str, int] = {}

                        for _, row in source_field_group.iterrows():
                            dest_field = row["dest_field"]
                            concept_id = row["concept_id"]
                            term_mapping_value = row.get("term_mapping_value")

                            if pd.notnull(term_mapping_value):
                                # Value-level mapping
                                if term_mapping_value not in value_mappings:
                                    value_mappings[term_mapping_value] = []

                                value_mappings[term_mapping_value].append(
                                    {dest_field: [concept_id]}
                                )
                            else:
                                # Field-level mapping
                                if dest_field.endswith("_concept_id"):
                                    field_level_mappings[dest_field] = concept_id

                        # Add field_level_mapping for measurement/observation tables
                        if is_measurement_observation and field_level_mappings:
                            concept_mapping["field_level_mapping"] = (
                                field_level_mappings
                            )

                            # Add value_as_concept_id mapping if there are value mappings
                            if value_mappings:
                                value_as_concept_mappings: Dict[str, int] = {}
                                for value, mappings in value_mappings.items():
                                    # Extract concept_id from the mappings for value_as_concept_id
                                    for mapping in mappings:
                                        for field_name, concept_ids in mapping.items():
                                            if field_name.endswith("_concept_id"):
                                                value_as_concept_mappings[value] = (
                                                    concept_ids[0]
                                                )
                                                break

                                if value_as_concept_mappings:
                                    concept_mapping["field_level_mapping"][
                                        "value_as_concept_id"
                                    ] = value_as_concept_mappings

                        # Add value_level_mapping for non-measurement/observation tables
                        if not is_measurement_observation and value_mappings:
                            concept_mapping["value_level_mapping"] = value_mappings

                        if concept_mapping:
                            concept_mappings[source_field_clean] = concept_mapping

                # Add mappings to result if they exist
                if person_id_mappings:
                    result[dest_table][source_table_clean][
                        "person_id_mapping"
                    ] = person_id_mappings

                if date_mappings:
                    result[dest_table][source_table_clean][
                        "date_mapping"
                    ] = date_mappings

                if concept_mappings:
                    result[dest_table][source_table_clean][
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
