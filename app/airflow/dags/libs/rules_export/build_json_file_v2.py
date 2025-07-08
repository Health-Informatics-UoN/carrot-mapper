from typing import Any, Dict, List
from libs.enums import JobStageType, StageStatusType
from libs.utils import update_job_status
import json
import pandas as pd
from datetime import datetime, timezone
from io import BytesIO
import logging
from libs.rules_export.helper import clean_concept_mappings
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

                    if "person_id" in [d.lower() for d in dest_fields]:
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
                        date_mappings = {
                            "source_field": source_field_clean,
                            "dest_field": date_like_fields,
                        }

                    is_measurement_observation = dest_table_str in [
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

                    concept_mapping: Dict[str, Any] = {}

                    # Detect block type
                    if only_field_mappings:
                        concept_mapping["field_level_mapping"] = field_level_mappings
                        concept_mapping["original_value"] = [
                            f for f in dest_fields if f.endswith("_source_value")
                        ]
                        if is_measurement_observation:
                            if "value_as_string" in dest_fields:
                                concept_mapping["original_value"].append(
                                    "value_as_string"
                                )
                            if "value_as_number" in dest_fields:
                                concept_mapping["original_value"].append(
                                    "value_as_number"
                                )

                    elif only_value_mappings:
                        concept_mapping["value_level_mapping"] = value_level_mappings
                        concept_mapping["original_value"] = [
                            f for f in dest_fields if f.endswith("_source_value")
                        ]
                        if is_measurement_observation:
                            if "value_as_string" in dest_fields:
                                concept_mapping["original_value"].append(
                                    "value_as_string"
                                )
                            if "value_as_number" in dest_fields:
                                concept_mapping["original_value"].append(
                                    "value_as_number"
                                )

                    else:
                        concept_mapping["field_level_mapping"] = field_level_mappings
                        value_as_concept_mappings = {}
                        for val, mappings in value_level_mappings.items():
                            for dest_field, ids in mappings.items():
                                if dest_field.endswith("_concept_id"):
                                    value_as_concept_mappings[val] = ids[0]
                                    break
                        if value_as_concept_mappings and is_measurement_observation:
                            concept_mapping["field_level_mapping"][
                                "value_as_concept_id"
                            ] = value_as_concept_mappings

                        if not is_measurement_observation:
                            concept_mapping["value_level_mapping"] = (
                                value_level_mappings
                            )

                        concept_mapping["original_value"] = [
                            f for f in dest_fields if f.endswith("_source_value")
                        ]

                    # Clean up: remove duplicates from original_value
                    if "original_value" in concept_mapping:
                        concept_mapping["original_value"] = list(
                            set(concept_mapping["original_value"])
                        )

                    if (
                        "original_value" in concept_mapping
                        and concept_mapping["original_value"]
                    ):
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
            "cdm": clean_concept_mappings(result),
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
