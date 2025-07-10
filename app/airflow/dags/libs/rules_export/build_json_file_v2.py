from typing import Any, Dict, List
from libs.enums import JobStageType, StageStatusType
from libs.utils import update_job_status
import json
import pandas as pd
from datetime import datetime, timezone
from io import BytesIO
import logging
from airflow.providers.postgres.hooks.postgres import PostgresHook

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


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
                    date_source_field = False
                    person_id_source_field = False

                    if "person_id" in [d.lower() for d in dest_fields]:
                        person_id_source_field = True
                        person_id_mappings = {
                            "source_field": source_field_clean,
                            "dest_field": "person_id",
                        }

                    date_like_fields = [
                        d
                        for d in dest_fields
                        if d and d.lower().endswith(("date", "datetime"))
                    ]
                    if date_like_fields:
                        date_source_field = True
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

                    if (
                        date_source_field or person_id_source_field
                    ) and is_measurement_observation_table:
                        only_field_mappings = False
                        only_value_mappings = True

                    concept_mapping: Dict[str, Any] = {}

                    # NEW IMPROVED LOGIC
                    if only_field_mappings:
                        # Field-only mappings: put everything under "*" key
                        concept_mapping["*"] = field_level_mappings

                        # Add original_value field (no value_as_concept_id, so add value_as_string/number)
                        original_values = [
                            f for f in dest_fields if f.endswith("_source_value")
                        ]
                        if is_measurement_observation_table:
                            if "value_as_string" in dest_fields:
                                original_values.append("value_as_string")
                            if "value_as_number" in dest_fields:
                                original_values.append("value_as_number")
                        concept_mapping["original_value"] = list(set(original_values))

                    elif only_value_mappings:
                        # Value-only mappings: put each value as direct key
                        for value, mappings in value_level_mappings.items():
                            if mappings:
                                concept_mapping[value] = mappings

                        # Add original_value field (check if any value has value_as_concept_id)
                        has_value_as_concept = any(
                            "value_as_concept_id" in mappings
                            for mappings in value_level_mappings.values()
                        )
                        original_values = [
                            f for f in dest_fields if f.endswith("_source_value")
                        ]
                        if (
                            is_measurement_observation_table
                            and not has_value_as_concept
                        ):
                            if "value_as_string" in dest_fields:
                                original_values.append("value_as_string")
                            if "value_as_number" in dest_fields:
                                original_values.append("value_as_number")
                        concept_mapping["original_value"] = list(set(original_values))

                    else:
                        # Mixed mappings: "*" key for field-level + individual value keys
                        concept_mapping["*"] = field_level_mappings

                        # For each value, create its own mapping
                        for value, value_mappings in value_level_mappings.items():
                            if value_mappings:
                                concept_mapping[value] = {}

                            # Add the same field-level concept IDs to this value
                            for field_key, field_ids in field_level_mappings.items():
                                concept_mapping[value][field_key] = field_ids

                            # Add value_as_concept_id: take the first concept ID from value-level mappings
                            for dest_field, ids in value_mappings.items():
                                if (
                                    dest_field.endswith("_concept_id")
                                    and is_measurement_observation_table
                                ):
                                    concept_mapping[value]["value_as_concept_id"] = ids[
                                        0
                                    ]
                                    break

                        # Add original_value field (mixed mappings have value_as_concept_id, so don't add value_as_string/number)
                        original_values = [
                            f for f in dest_fields if f.endswith("_source_value")
                        ]
                        concept_mapping["original_value"] = list(set(original_values))

                    if concept_mapping and concept_mapping.get("original_value"):
                        concept_mappings[source_field_clean] = concept_mapping

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
