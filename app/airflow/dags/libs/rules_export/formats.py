"""
Render mapping rules as CSV, JSON v1 and JSON v2.

Each function takes the rows of a scan report's temp rules table as plain dicts
(column name -> value, NULL -> None), as returned by the database driver, and
returns the file's text. There is no Airflow / database code here, so the formats
can be unit tested on their own; ``file_services`` fetches the rows and calls these.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Hashable, Iterable, Mapping
from datetime import date
from typing import Any

Row = Mapping[str, Any]

CSV_HEADERS = [
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


def rules_to_csv(rules: Iterable[Row], today: date) -> str:
    """
    One CSV line per rule. ``today`` decides each concept's validity (whether today
    is within its valid_start_date / valid_end_date).
    """
    buffer = io.StringIO()
    writer = csv.writer(
        buffer,
        lineterminator="\n",
        delimiter=",",
        quoting=csv.QUOTE_MINIMAL,
    )
    # replace term_mapping ({'source_value':'concept'}) with separate columns
    writer.writerow(CSV_HEADERS)

    for row in rules:
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
        is_field_mapping = ""

        if row.get("dest_field", "").endswith("_concept_id"):
            concept_id = row.get("concept_id", "")
            concept_class = row.get("concept_class", "")
            concept = row.get("standard_concept", "")
            validity = (
                row.get("valid_start_date", "") <= today < row.get("valid_end_date", "")
            )
            vocabulary = row.get("vocabulary", "")
            source_value = row.get("term_mapping_value", "")
            is_field_mapping = "0" if source_value else "1"

        writer.writerow(
            [
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
                is_field_mapping,
            ]
        )
    return buffer.getvalue()


def rules_to_json_v1(rules: Iterable[Row], metadata: Mapping[str, Any]) -> str:
    """Rules grouped by OMOP table, then by mapped concept, then by OMOP field."""
    result: dict[str, Any] = {}
    for row in rules:
        dest_table = row["dest_table"]
        concept_key = f"{row['concept_name']} {row['sr_concept_id']}"
        dest_field = row["dest_field"]
        source_table = row["source_table"].replace("\ufeff", "")
        source_field = row["source_field"].replace("\ufeff", "")

        # Prepare the term_mapping value
        # will solve #1006 here (fields end with source_concept_id and concept_id will have different values),
        # then assign term_mapping step below
        if row["term_mapping_value"] is not None:
            term_mapping = {row["term_mapping_value"]: row["concept_id"]}
        else:
            term_mapping = row["concept_id"]

        # Build the field entry
        field_entry = {"source_table": source_table, "source_field": source_field}
        # Assign term_mapping
        if dest_field.endswith("_concept_id"):
            field_entry["term_mapping"] = term_mapping

        result.setdefault(dest_table, {}).setdefault(concept_key, {})[dest_field] = (
            field_entry
        )

    return json.dumps({"metadata": dict(metadata), "cdm": result}, indent=6)


def _sorted_groups(rows: Iterable[Row], key: str) -> list[tuple[Hashable, list[Row]]]:
    """
    Group rows by ``row[key]``: groups sorted by key, rows kept in their order
    within each group, and rows whose key is NULL left out.
    """
    groups: dict[Hashable, list[Row]] = {}
    for row in rows:
        if row[key] is not None:
            groups.setdefault(row[key], []).append(row)
    return sorted(groups.items(), key=lambda item: item[0])


def rules_to_json_v2(rules: Iterable[Row], metadata: Mapping[str, Any]) -> str:
    """
    Rules grouped by OMOP table, then by source table, with each source table's
    person_id mapping, date mapping and concept mappings (per source field).
    """
    result: dict[str, Any] = {}

    for dest_table, dest_table_group in _sorted_groups(rules, "dest_table"):
        dest_table_str = str(dest_table)
        result[dest_table_str] = {}

        for source_table, source_table_group in _sorted_groups(
            dest_table_group, "source_table"
        ):
            source_table_clean = str(source_table).replace("\ufeff", "")
            result[dest_table_str][source_table_clean] = {}

            person_id_mappings = {}
            date_mappings = {}
            concept_mappings = {}

            for source_field, source_field_group in _sorted_groups(
                source_table_group, "source_field"
            ):
                source_field_clean = str(source_field).replace("\ufeff", "")
                # unique OMOP fields, in the order they first appear
                dest_fields = list(
                    dict.fromkeys(
                        r["dest_field"]
                        for r in source_field_group
                        if r["dest_field"] is not None
                    )
                )

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
                field_level_mappings: dict[str, list[int]] = {}
                value_level_mappings: dict[str, dict[str, list[int]]] = {}

                only_field_mappings = True
                only_value_mappings = True

                for row in source_field_group:
                    dest_field = row["dest_field"]
                    concept_id = row["concept_id"]
                    term_mapping_value = row.get("term_mapping_value")

                    # Solved #1006 here
                    if term_mapping_value is not None:
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
                            value_level_mappings[term_mapping_value][dest_field].append(
                                concept_id
                            )
                    else:
                        only_value_mappings = False
                        if dest_field.endswith("_concept_id"):
                            # initialize the dest_field if not exists
                            if dest_field not in field_level_mappings:
                                field_level_mappings[dest_field] = []
                            field_level_mappings[dest_field].append(concept_id)

                concept_mapping: dict[str, Any] = {}

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
                result[dest_table_str][source_table_clean]["person_id_mapping"] = (
                    person_id_mappings
                )

            if date_mappings:
                result[dest_table_str][source_table_clean]["date_mapping"] = (
                    date_mappings
                )

            if concept_mappings:
                result[dest_table_str][source_table_clean]["concept_mappings"] = (
                    concept_mappings
                )

    return json.dumps({"metadata": dict(metadata), "cdm": result}, indent=2)
