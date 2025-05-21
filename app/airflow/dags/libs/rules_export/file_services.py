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


def build_rules_csv(processed_rules: DataFrame) -> io.StringIO:
    """
    Gets Mapping Rules in csv format.

    Args:
        - qs (QuerySet[MappingRule]) queryset of Mapping Rules.

    Returns:
        - Mapping rules as StringIO.
    """
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
    for content in processed_rules:
        # replace the django model objects with string names
        content["destination_table"] = content["destination_table"].table
        content["domain"] = content["domain"]
        content["source_table"] = content["source_table"].name
        content["source_field"] = content["source_field"].name

        # pop out the term mapping
        term_mapping = content.pop("term_mapping")
        content["isFieldMapping"] = ""
        content["validity"] = ""
        content["vocabulary"] = ""
        content["concept"] = ""
        content["class"] = ""
        # if no term mapping, set columns to blank
        if term_mapping is None:
            content["source_value"] = ""
            content["concept_id"] = ""
        elif isinstance(term_mapping, dict):
            # if is a dict, it's a map between a source value and a concept
            # set these based on the value/key
            content["source_value"] = list(term_mapping.keys())[0]
            content["concept_id"] = list(term_mapping.values())[0]
            content["isFieldMapping"] = "0"
        else:
            # otherwise it is a scalar, it is a term map of a field, so set this
            content["source_value"] = ""
            content["concept_id"] = term_mapping
            content["isFieldMapping"] = "1"

        # Lookup and extract concept
        if content["concept_id"]:
            if concept := Concept.objects.filter(
                concept_id=content["concept_id"]
            ).first():
                content["validity"] = (
                    concept.valid_start_date <= today < concept.valid_end_date
                )
                content["vocabulary"] = concept.vocabulary_id
                content["concept"] = concept.standard_concept
                content["class"] = concept.concept_class_id

        # extract and write the contents now
        content_out = [str(content[x]) for x in headers]
        writer.writerow(content_out)

    # rewind the buffer and return the response
    _buffer.seek(0)

    return _buffer
