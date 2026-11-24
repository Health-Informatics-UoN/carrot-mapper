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
import logging
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


def rules_to_json_v2(
    rules: Iterable[Row],
    metadata: Mapping[str, Any],
    tables: Iterable[Row] = (),
    field_mappings: Iterable[Row] = (),
    type_fields: Mapping[str, str] | None = None,
    nlp_exclusions: Iterable[Row] = (),
    domain_concepts: Mapping[str, int] | None = None,
) -> str:
    """
    Rules grouped by OMOP table, then by source table, with each source table's
    person_id mapping, date mapping and concept mappings (per source field).

    ``tables``, ``field_mappings``, ``type_fields``, ``nlp_exclusions`` and
    ``domain_concepts`` add the scan report tables' roles, field mappings, type
    concepts and NLP-derived record settings; see ``add_table_level_mappings``.
    Rules for fields that take concepts from a column's values (field mappings
    with ``map_values``) become that block's ``value_mappings``.
    """
    result: dict[str, Any] = {}
    rules = list(rules)
    field_mappings = list(field_mappings)
    value_mapped = {
        (mapping["source_table"], mapping["omop_field"])
        for mapping in field_mappings
        # A note_nlp table's term column keeps its usual rules
        if mapping.get("map_values") and mapping["omop_field"] != TERM_CONCEPT_FIELD
    }
    value_rules = [
        rule
        for rule in rules
        if rule["dest_table"] in (NOTE_TABLE, NOTE_NLP_TABLE)
        and (rule["source_table"], rule["dest_field"]) in value_mapped
    ]
    if value_rules:
        value_rule_ids = {id(rule) for rule in value_rules}
        rules = [rule for rule in rules if id(rule) not in value_rule_ids]

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
                # (which should always have at least one _source_value field). note_nlp has no
                # *_source_value field, so its concept groups only need concept mappings.
                if concept_mapping and (
                    concept_mapping.get("original_value")
                    or (dest_table_str == "note_nlp" and len(concept_mapping) > 1)
                ):
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

    add_table_level_mappings(
        result,
        tables,
        field_mappings,
        type_fields or {},
        nlp_exclusions,
        domain_concepts or {},
        value_rules,
    )

    return json.dumps({"metadata": dict(metadata), "cdm": result}, indent=2)


# The table holding the notes that note_nlp records refer to, and the OMOP
# field naming a note's key (see the API's services/table_field_mappings.py).
NOTE_TABLE = "note"
NOTE_KEY_FIELD = "note_id"
NOTE_NLP_TABLE = "note_nlp"
# The note_nlp field holding each term's concept
TERM_CONCEPT_FIELD = "note_nlp_concept_id"
# The note_nlp field holding each term's text, required like note_id
NOTE_NLP_TERM_TEXT_FIELD = "lexical_variant"

# The vocabulary domain of each OMOP table records can be derived into from NLP
# output, for fact_relationship's domain_concept_ids (looked up in omop.domain).
DERIVED_TABLE_DOMAINS = {
    "condition_occurrence": "Condition",
    "drug_exposure": "Drug",
    "procedure_occurrence": "Procedure",
    "measurement": "Measurement",
    "observation": "Observation",
    "device_exposure": "Device",
    "specimen": "Specimen",
}


def _clean(name: Any) -> str:
    return str(name).replace("\ufeff", "")


def _constant(omop_field: str, value: str) -> int | str:
    """Concept id fields are exported as numbers, everything else as text"""
    return int(value) if omop_field.endswith("_concept_id") else value


def add_table_level_mappings(
    result: dict[str, Any],
    tables: Iterable[Row],
    field_mappings: Iterable[Row],
    type_fields: Mapping[str, str],
    nlp_exclusions: Iterable[Row] = (),
    domain_concepts: Mapping[str, int] | None = None,
    value_rules: Iterable[Row] = (),
) -> None:
    """
    Add each Scan Report Table's role, type concept and field mappings to the v2
    rules in ``result``, as the record-level keys Carrot Transform understands
    (see its docs/rules_v2_record_extensions.md):

    - type concept: a constant for the <table>_type_concept_id field of every
      block built from the table.
    - note tables: a note block, one record per row, keyed by the note_id
      mapping and filled from the other field mappings.
    - note_nlp tables: field mappings and constants on the note_nlp block built
      from the table's concepts, with note_id as a reference to the note table.
      Every other block built from the table (e.g. condition_occurrence) gets
      ``derived_from``: its records are only written for rows that give a
      note_nlp record and match none of the table's exclusions, and are linked
      to it in fact_relationship if the table's link concepts are set.

    Args:
        - tables: rows of source_table, table_role, type_concept_id,
          person_field and date_field (field names, or None), and for note_nlp
          tables source_domain_concept_id, relationship_concept_id and
          reverse_relationship_concept_id (or None)
        - field_mappings: rows of source_table, omop_field, source_field (a
          field name, or None) and constant_value
        - type_fields: OMOP table -> its *_type_concept_id field
        - nlp_exclusions: rows of source_table, source_field (a field name) and
          excluded_values (a list)
        - domain_concepts: OMOP table -> its domain's concept id
        - value_rules: rules (rows of the rules export) for fields that take
          their concept from a column's values; they become the block's
          ``value_mappings``: field -> {"source_field", "values": {value:
          concept id}}. A value with more than one concept keeps the first.
    """
    mappings_by_table: dict[Any, list[Row]] = {}
    for mapping in field_mappings:
        mappings_by_table.setdefault(mapping["source_table"], []).append(mapping)
    value_mappings_by_table: dict[str, dict[str, dict[str, Any]]] = {}
    for rule in sorted(value_rules, key=lambda r: r["sr_concept_id"]):
        if rule["term_mapping_value"] is None or rule["concept_id"] is None:
            continue
        lookup = value_mappings_by_table.setdefault(
            _clean(rule["source_table"]), {}
        ).setdefault(
            rule["dest_field"],
            {"source_field": _clean(rule["source_field"]), "values": {}},
        )
        lookup["values"].setdefault(
            str(rule["term_mapping_value"]), int(rule["concept_id"])
        )
    exclusions_by_table: dict[Any, dict[str, list[str]]] = {}
    for exclusion in nlp_exclusions:
        exclusions_by_table.setdefault(exclusion["source_table"], {})[
            _clean(exclusion["source_field"])
        ] = list(exclusion["excluded_values"])

    for table in tables:
        source_table = _clean(table["source_table"])
        role = table["table_role"]

        copies: dict[str, str] = {}
        constants: dict[str, int | str] = {}
        note_key = None
        code_lookup = None
        for mapping in mappings_by_table.get(table["source_table"], []):
            omop_field = mapping["omop_field"]
            if mapping.get("map_values"):
                continue  # from value_rules, or the term column's own rules
            if omop_field == TERM_CONCEPT_FIELD:
                if mapping.get("vocabulary_id") and mapping["source_field"]:
                    code_lookup = {
                        "source_field": _clean(mapping["source_field"]),
                        "vocabulary_id": mapping["vocabulary_id"],
                    }
                continue
            if omop_field == NOTE_KEY_FIELD:
                note_key = _clean(mapping["source_field"])
            elif mapping["source_field"] is not None:
                copies[omop_field] = _clean(mapping["source_field"])
            else:
                constants[omop_field] = _constant(omop_field, mapping["constant_value"])

        if role == "note":
            if not (note_key and table["person_field"] and table["date_field"]):
                # The caller logs nothing per table, so say why the notes are missing
                logging.warning(
                    f"Note table {source_table} needs a person ID, a date event and a "
                    "note_id field mapping; it is left out of the rules"
                )
                continue
            result.setdefault(NOTE_TABLE, {})[source_table] = {
                "person_id_mapping": {
                    "source_field": _clean(table["person_field"]),
                    "dest_field": "person_id",
                },
                "date_mapping": {
                    "source_field": _clean(table["date_field"]),
                    "dest_field": ["note_datetime"],
                },
                "record_key": {"source_field": note_key},
                "field_mappings": copies,
                "constant_mappings": constants,
            }
            if value_mappings_by_table.get(source_table):
                result[NOTE_TABLE][source_table]["value_mappings"] = (
                    value_mappings_by_table[source_table]
                )
        elif (
            role == "note_nlp"
            and (code_lookup or source_table in result.get(NOTE_NLP_TABLE, {}))
            and not (
                note_key
                and NOTE_NLP_TERM_TEXT_FIELD in copies | constants
                and table["person_field"]
                and table["date_field"]
            )
        ):
            # As for notes: without these its note_nlp records can't be written
            # (or linked to their notes), and its derived records would lose
            # their exclusions, so the table is left out until it's set up
            logging.warning(
                f"Note NLP table {source_table} needs a person ID, a date event and "
                f"{NOTE_KEY_FIELD} and {NOTE_NLP_TERM_TEXT_FIELD} field mappings; it is "
                "left out of the rules"
            )
            for blocks in result.values():
                blocks.pop(source_table, None)
            for dest_table in [name for name, blocks in result.items() if not blocks]:
                del result[dest_table]
            continue
        elif role == "note_nlp" and (
            code_lookup or source_table in result.get("note_nlp", {})
        ):
            if source_table not in result.get(NOTE_NLP_TABLE, {}):
                # No concepts mapped in Mapper: the block only holds the lookup
                result.setdefault(NOTE_NLP_TABLE, {})[source_table] = {
                    "date_mapping": {
                        "source_field": _clean(table["date_field"]),
                        "dest_field": ["nlp_datetime"],
                    },
                    "concept_mappings": {},
                }
            block = result["note_nlp"][source_table]
            if code_lookup:
                block["code_lookup"] = _code_lookup(
                    code_lookup,
                    table,
                    exclusions_by_table.get(table["source_table"], {}),
                    domain_concepts or {},
                )
            if note_key:
                block["references"] = {
                    NOTE_KEY_FIELD: {"table": NOTE_TABLE, "source_field": note_key}
                }
            block["field_mappings"] = copies
            block["constant_mappings"] = constants
            if value_mappings_by_table.get(source_table):
                block["value_mappings"] = value_mappings_by_table[source_table]
            _add_derived_from(
                result,
                source_table,
                table,
                exclusions_by_table.get(table["source_table"], {}),
                domain_concepts or {},
            )

        # The table's type concept goes on every record built from it
        if table["type_concept_id"] is not None:
            for dest_table, blocks in result.items():
                type_field = type_fields.get(dest_table)
                if type_field and source_table in blocks:
                    blocks[source_table].setdefault("constant_mappings", {})[
                        type_field
                    ] = int(table["type_concept_id"])


def _code_lookup(
    lookup: dict[str, str],
    table: Row,
    exclusions: dict[str, list[str]],
    domain_concepts: Mapping[str, int],
) -> dict[str, Any]:
    """
    A note_nlp block's ``code_lookup``: the column holding each term's code and
    its vocabulary, for Transform to find each code's concepts, and what it
    needs to write the records derived from them (person, date, type concept,
    exclusions and fact_relationship link), as Mapper has no rules for them.
    """
    derived: dict[str, Any] = {
        "person_id_mapping": {
            "source_field": _clean(table["person_field"]),
            "dest_field": "person_id",
        },
        "date_mapping": {"source_field": _clean(table["date_field"])},
    }
    if table["type_concept_id"] is not None:
        derived["type_concept_id"] = int(table["type_concept_id"])
    if exclusions:
        derived["exclude_values"] = exclusions
    link_ids = [
        table.get("source_domain_concept_id"),
        table.get("relationship_concept_id"),
        table.get("reverse_relationship_concept_id"),
    ]
    if all(link_ids):
        derived["fact_relationship"] = {
            "domain_concept_ids": {
                dest_table: int(concept)
                for dest_table, concept in domain_concepts.items()
            },
            "source_domain_concept_id": int(link_ids[0]),
            "relationship_concept_id": int(link_ids[1]),
            "reverse_relationship_concept_id": int(link_ids[2]),
        }
    return {**lookup, "derived_records": derived}


def _add_derived_from(
    result: dict[str, Any],
    source_table: str,
    table: Row,
    exclusions: dict[str, list[str]],
    domain_concepts: Mapping[str, int],
) -> None:
    """Mark the blocks a note_nlp table feeds (other than note_nlp) as derived"""
    link_ids = [
        table.get("source_domain_concept_id"),
        table.get("relationship_concept_id"),
        table.get("reverse_relationship_concept_id"),
    ]
    for dest_table, blocks in result.items():
        if dest_table in (NOTE_NLP_TABLE, NOTE_TABLE) or source_table not in blocks:
            continue
        derived_from: dict[str, Any] = {"table": NOTE_NLP_TABLE}
        if exclusions:
            derived_from["exclude_values"] = exclusions
        if all(link_ids):
            domain = domain_concepts.get(dest_table)
            if domain is None:
                logging.warning(
                    f"No domain concept for {dest_table} in the vocabulary; "
                    f"records derived from {source_table} won't be linked"
                )
            else:
                derived_from["fact_relationship"] = {
                    "domain_concept_id": int(domain),
                    "source_domain_concept_id": int(link_ids[0]),
                    "relationship_concept_id": int(link_ids[1]),
                    "reverse_relationship_concept_id": int(link_ids[2]),
                }
        blocks[source_table]["derived_from"] = derived_from
