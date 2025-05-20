from typing import List, Tuple, Any, Dict
from libs.enums import JobStageType, StageStatusType
from libs.utils import update_job_status
import json
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from io import BytesIO
from airflow.providers.postgres.hooks.postgres import PostgresHook

# PostgreSQL connection hook
pg_hook = PostgresHook(postgres_conn_id="postgres_db_conn")


def build_rules_json(df: DataFrame) -> BytesIO:
    metadata = {
        "dataset": "test",
        "date_created": datetime.now().isoformat(),
    }

    result: Dict[str, Any] = {}
    for _, row in df.iterrows():
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
