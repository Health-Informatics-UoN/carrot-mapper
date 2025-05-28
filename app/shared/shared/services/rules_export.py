import csv
import io
from datetime import date, datetime, timezone
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.query import QuerySet
from graphviz import Digraph
from shared.data.models import Concept, ConceptAncestor
from shared.mapping.models import (
    MappingRule,
    OmopField,
    OmopTable,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
)


class NonStandardConceptMapsToSelf(Exception):
    pass


def get_mapping_rules_list(
    mapping_rules: QuerySet[MappingRule],
    page_number: int | None = None,
    page_size: int | None = None,
) -> list[dict[str, Any]]:
    """
    Args:
        mapping_rules : queryset of all mapping rules
        page_number: if present, the number of the page to be returned under pagination
        page_size: if present, the size of the page to be returned under pagination (
          that is, when viewed on the mappingruleslist page. We don't supply
          `page_number` or `page_size` on other calls, so that all values are returned
          in e.g. the files for download.
    Returns:
        list : a list of rules that can be interpreted by the view.py
               page and processed to build a json
    """
    # In the case of a paginated call, calculate the slice by hand and apply.
    # page_number is 1-based.
    if page_number is not None:
        first_index = (page_number - 1) * page_size
        last_index = page_number * page_size
        mapping_rules = mapping_rules[first_index:last_index]

    # get all scan_report_concepts that are used
    # get the ids first so we can make a batch call
    scan_report_concepts = list({obj.concept_id for obj in mapping_rules})

    nmapped_concepts = len(scan_report_concepts)

    # make the batch call
    scan_report_concepts_id_to_obj_map = {
        x.id: x
        for x in list(ScanReportConcept.objects.filter(pk__in=scan_report_concepts))
    }

    ntotal_concepts = len(scan_report_concepts_id_to_obj_map.values())

    if nmapped_concepts != ntotal_concepts:
        print(
            "WARNING!! There are a differing number of scan report concepts"
            " associate to the mapping rules, and those that exist as scan report concepts"
        )

    # get all the ids for all ScanReportValues that are used (have been mapped with a concept)
    scanreportvalue_content_type = ContentType.objects.get(model="scanreportvalue")
    print(f"scanreportvalue_content_type: {scanreportvalue_content_type}")
    scan_report_values_with_scan_report_concepts = [
        obj.object_id
        for obj in ScanReportConcept.objects.filter(
            pk__in=scan_report_concepts_id_to_obj_map,
            content_type=scanreportvalue_content_type,
        )
    ]
    print(
        f"scan_report_values_with_scan_report_concepts: {scan_report_values_with_scan_report_concepts}"
    )
    # make a batch call to the ORM again..
    scan_report_values_id_to_value_map = {
        obj.id: obj.value
        for obj in list(
            ScanReportValue.objects.filter(
                pk__in=scan_report_values_with_scan_report_concepts
            )
        )
    }

    # get all destination field ids
    destination_fields_ids = [obj.omop_field_id for obj in mapping_rules]
    # batch call
    destination_fields = {
        obj.id: obj
        for obj in list(OmopField.objects.filter(pk__in=destination_fields_ids))
    }

    # again with destination table
    destination_tables_ids = [obj.table_id for obj in destination_fields.values()]
    destination_tables = {
        obj.id: obj
        for obj in list(OmopTable.objects.filter(pk__in=destination_tables_ids))
    }

    # and sources....
    source_fields_ids = [obj.source_field_id for obj in mapping_rules]
    source_fields = {
        obj.id: obj
        for obj in list(ScanReportField.objects.filter(pk__in=source_fields_ids))
    }
    source_tables_ids = [obj.scan_report_table_id for obj in source_fields.values()]
    source_tables = {
        obj.id: obj
        for obj in list(ScanReportTable.objects.filter(pk__in=source_tables_ids))
    }

    # Using select_related() means we can chain together querysets into one database
    # query rather than using multiple
    structural_mapping_rules_sr_concepts = mapping_rules.select_related("concept")
    # Generate rule.id to SRConcept.id map for all SRConcepts related to these rules.
    rule_to_srconcept_id_map = {
        obj.id: obj.concept.id for obj in structural_mapping_rules_sr_concepts
    }

    structural_mapping_rules_sr_concepts_concepts = mapping_rules.select_related(
        "concept__concept"
    )
    # Generate MappingRule.id to Concept.id map for all Concepts related to SRConcepts
    # related to these MappingRules.
    rule_id_to_concept_name_map = {
        obj.id: obj.concept.concept.concept_name
        for obj in structural_mapping_rules_sr_concepts_concepts
    }

    # Make a single query to get all ScanReportConcepts associated to
    # ScanReportValues. This means we avoid what would be more understandable,
    # but extremely slow, code to check whether each object is associated to a
    # ScanReportValue.
    scan_report_concepts_with_values = [
        obj.id
        for obj in ScanReportConcept.objects.filter(
            pk__in=scan_report_concepts_id_to_obj_map,
            content_type=scanreportvalue_content_type,
        )
    ]

    # now loop over the rules to actually create the list version of the rules
    rules = []
    for rule in mapping_rules:
        # get the fields/tables from the loop up lists
        # the speed up comes from here as we dont need to keep hitting the DB to get this data
        # we've already cached it in these dictionaries by making a batch call
        destination_field = destination_fields[rule.omop_field_id]
        destination_table = destination_tables[destination_field.table_id]

        source_field = source_fields[rule.source_field_id]
        source_table = source_tables[source_field.scan_report_table_id]

        # get the concepts again
        rule_scan_report_concept_id = rule_to_srconcept_id_map[rule.id]

        if rule.concept_id not in scan_report_concepts_id_to_obj_map:
            print(f"WARNING!! scan_report_concept {rule.concept_id} no longer exists")
            continue

        scan_report_concept = scan_report_concepts_id_to_obj_map[rule.concept_id]

        concept_id = scan_report_concept.concept_id

        concept_name = rule_id_to_concept_name_map[rule.id]

        # work out if we need term_mapping or not
        # Two TODOs below is for the issue #1006
        # TODO: add field source_concept_id to the model SCANREPORTCONCEPT (can be null because of uncoded concepts)
        # TODO: Having a separate logic for <domain>_source_concept_id
        term_mapping = None
        if "concept_id" in destination_field.field:
            if scan_report_concept.id in scan_report_concepts_with_values:
                term_mapping = {
                    scan_report_values_id_to_value_map[
                        scan_report_concept.object_id
                    ]: concept_id
                }
            else:
                term_mapping = concept_id

        creation_type = scan_report_concept.creation_type

        rules.append(
            {
                "rule_id": rule_scan_report_concept_id,
                "omop_term": concept_name,
                "destination_table": destination_table,
                "domain": scan_report_concept.concept.domain_id,
                "destination_field": destination_field,
                "source_table": source_table,
                "source_field": source_field,
                "term_mapping": term_mapping,
                "creation_type": creation_type,
            }
        )

    return rules


def get_mapping_rules_json(
    mapping_rules: QuerySet[MappingRule],
) -> dict[str, dict] | dict[str, Any]:
    """
    Args:
        - mapping_rules (QuerySet) : queryset of all mapping rules
    Returns:
        - dict : formatted json that can be eaten by the TL-Tool
    """

    # Return empty metadata and cdm if `structural_mapping_rules` is empty
    if not mapping_rules:
        return {"metadata": {}, "cdm": {}}

    # use the first_qs to get the scan_report dataset name
    # all qs items will be from the same scan_report
    first_rule = mapping_rules[0]

    # build some metadata
    metadata = {
        "date_created": datetime.now(timezone.utc).isoformat(),
        "dataset": first_rule.scan_report.dataset,
    }

    # get the list of rules
    # this is the same list/function that is used
    # !NOTE: we could cache this to speed things up, as the page load will call this once already
    all_rules = get_mapping_rules_list(mapping_rules)

    cdm: dict[str, Any] = {}
    # loop over the list of rules
    for rule in all_rules:
        # get the rule id
        # i.e. 5 rules with have the same id as they're associated to the same object e.g. person mapping of 'F' to 8532
        # append the rule_id to not overwrite mappings to the same concept ID
        _id = rule["omop_term"] + " " + str(rule["rule_id"])

        # get the table name
        table_name = rule["destination_table"].table

        # make a new object if we havent come across this cdm table yet
        if table_name not in cdm:
            cdm[table_name] = {}

        # reminder, json for ETL needs to be structured like:
        # { 'cdm': {'person': [person_0, person_1], 'condition_occurence:[c1,c2,c3...] }
        # if the sub-object (e.g. <person_0>) has not been made, create a new nested document
        if _id not in cdm[table_name]:
            cdm[table_name][_id] = {}

        # make a new mapping spec for the destination table
        destination_field = rule["destination_field"].field
        cdm[table_name][_id][destination_field] = {
            "source_table": rule["source_table"].name.replace("\ufeff", ""),
            "source_field": rule["source_field"].name.replace("\ufeff", ""),
        }
        # include term_mapping if it's needed
        # will appear for destinations with _concept_id,
        # either as a dict (value map) or as a str/int (field map)
        if rule["term_mapping"] is not None:
            cdm[table_name][_id][destination_field]["term_mapping"] = rule[
                "term_mapping"
            ]

    # add the metadata and cdm object together
    return {"metadata": metadata, "cdm": cdm}


def get_mapping_rules_as_csv(qs: QuerySet[MappingRule]) -> io.StringIO:
    """
    Gets Mapping Rules in csv format.

    Args:
        - qs (QuerySet[MappingRule]) queryset of Mapping Rules.

    Returns:
        - Mapping rules as StringIO.
    """
    # get the mapping rules as a list
    output = get_mapping_rules_list(qs)

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
    for content in output:
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


def make_dag(
    data: dict[str, dict[str, dict[str, dict[str, str]]]], colorscheme: str = "gnbu9"
) -> str:
    """
    Create a DAG given data, and a coloscheme.

    Args:
        - data (dict): The data to create the DAG for.
        - colorscheme (Optional[str]): The colorscheme of the DAG

    Returns:
        - A DAG (str) representing the data and colorscheme.
    """
    dot = Digraph(strict=True, format="svg")
    dot.attr(rankdir="RL")
    with dot.subgraph(name="cluster_0") as dest, dot.subgraph(name="cluster_1") as inp:
        dest.attr(
            style="filled",
            fillcolor="2",
            colorscheme="blues9",
            penwidth="0",
            label="Destination",
        )
        inp.attr(
            style="filled",
            fillcolor="2",
            colorscheme="greens9",
            penwidth="0",
            label="Source",
        )

        for destination_table_name, destination_tables in data.items():
            dest.node(
                destination_table_name,
                shape="folder",
                style="filled",
                fontcolor="white",
                colorscheme=colorscheme,
                fillcolor="9",
            )

            for ref_name, destination_table in destination_tables.items():
                for destination_field, source in destination_table.items():
                    source_field = source["source_field"]
                    source_table = source["source_table"]

                    table_name = f"{destination_table_name}_{destination_field}"
                    dest.node(
                        table_name,
                        label=destination_field,
                        style="filled,rounded",
                        colorscheme=colorscheme,
                        fillcolor="7",
                        shape="box",
                        fontcolor="white",
                    )

                    dest.edge(destination_table_name, table_name, arrowhead="none")

                    source_field_name = f"{source_table}_{source_field}"
                    inp.node(
                        source_field_name,
                        source_field,
                        colorscheme=colorscheme,
                        style="filled,rounded",
                        fillcolor="5",
                        shape="box",
                    )

                    if "term_mapping" in source and source["term_mapping"] is not None:
                        dot.edge(
                            table_name,
                            source_field_name,
                            dir="back",
                            color="red",
                            penwidth="2",
                        )
                    else:
                        dot.edge(
                            table_name, source_field_name, dir="back", penwidth="2"
                        )

                    inp.node(
                        source_table,
                        shape="tab",
                        fillcolor="4",
                        colorscheme=colorscheme,
                        style="filled",
                    )
                    inp.edge(source_field_name, source_table, arrowhead="none")

    return dot.pipe().decode("utf-8")


def get_concept_details(
    h_concept_id: int,
) -> tuple[str, QuerySet[MappingRule, dict[str, Any]]]:
    """
    Given a mapping rule and its descendant/ancestor concept id
    Find the source field/value that the descendant/ancestor is mapped to,
    Return the mapping rule name, the descendant/ancestor name, and the source fields/tables

    Args:
        - h_concept_id (int): The Id of the Concept to filter by.
    """
    # Get the descendant/ancestor concept name
    concept_name = Concept.objects.get(concept_id=h_concept_id).concept_name

    # Get the source field id, source field name, source table id,
    # source table name and the content type of the descendant/ancestor
    # Filter out mapping rules pointing to omop fields:
    # person id, datetime, or source_concept_id to account for duplicated mapping rules
    source_ids = (
        MappingRule.objects.filter(concept__concept=h_concept_id)
        .exclude(
            Q(omop_field__field__icontains="person_id")
            | Q(omop_field__field__icontains="datetime")
            | Q(omop_field__field__icontains="source")
        )
        .values(
            "source_field__id",
            "source_field__name",
            "source_field__scan_report_table__id",
            "source_field__scan_report_table__name",
            "source_field__scan_report_table__scan_report",
            "concept__content_type",
        )
    ).distinct()
    return (concept_name, source_ids)


def analyse_concepts(scan_report_id: int) -> dict[str, list[Any]]:
    """
    Given a scan_report_id get all the mapping rules in that Scan Report.
    Get all the mapping rules from every other Scan Report and compare them against the current ones
    If there are any ancestors/descendants of the current mapping rules mapped in another Scan Report
    Find where those ancestors/descendants are mapped to

    Args:
        - scan_report_id (int): The Id of the Scan Report to analyse for.

    Returns:
        - ?
    """

    # Get mapping rules for current scan report
    mapping_rules = (
        MappingRule.objects.all()
        .filter(scan_report_id=scan_report_id)
        .values_list("concept__concept", flat=True)
        .distinct()
    )
    # Get mapping rules for all other scan reports
    all_mapping_rules = MappingRule.objects.exclude(
        scan_report_id=scan_report_id
    ).values_list("concept__concept", flat=True)

    data = []
    descendant_list = []
    ancestors_list = []
    # For every mapping rule in the current scan report
    for rule in mapping_rules:
        # Get the name of the mapping rule concept
        rule_name = Concept.objects.get(concept_id=rule).concept_name
        # Find the descendants of that rule
        descendants = ConceptAncestor.objects.filter(ancestor_concept_id=rule)
        # Find the ancestors of that rule
        ancestors = ConceptAncestor.objects.filter(descendant_concept_id=rule)

        # For each descendant found
        for descendant in descendants:
            # get the concept id
            desc = descendant.descendant_concept_id
            desc_level = (
                str(descendant.min_levels_of_separation) + "/",
                str(descendant.max_levels_of_separation),
            )
            # Check if the descendant is a mapped concept in any other scan report
            # and that it's not the same as the original concept
            if (desc in all_mapping_rules) and (desc != rule):
                # Get all the details for that descendant:
                # descendant name, current mapping rule name, where that descendant is mapped to
                desc_name, source_ids = get_concept_details(desc)
                # Append all descendant details to a list
                descendant_list.append(
                    {
                        "d_id": desc,
                        "d_name": desc_name,
                        "source": source_ids,
                        "level": desc_level,
                    }
                )
        # For each ancestor found
        for ancestor in ancestors:
            # get the concept_id
            anc = ancestor.ancestor_concept_id
            anc_level = (
                str(ancestor.min_levels_of_separation) + "/",
                str(ancestor.max_levels_of_separation),
            )
            # If ancestor is a mapping rule in any other scan report,
            # and is not the same rule as the current one
            if (anc in all_mapping_rules) and (anc != rule):
                # Get all the details for that ancestor:
                # ancestor name, current mapping rule name, where that ancestor is mapped to
                concept, source_ids = get_concept_details(anc)
                # Append all the ancestor details to a list
                ancestors_list.append(
                    {
                        "a_id": anc,
                        "a_name": concept,
                        "source": source_ids,
                        "level": anc_level,
                    }
                )

        # Append all the descendants/ancestors of the current mapping rule in a dict
        # Do not append if both lists are empty
        if ancestors_list or descendant_list:
            data.append(
                {
                    "rule_id": rule,
                    "rule_name": rule_name,
                    "anc_desc": [
                        {
                            "descendants": descendant_list,
                            "ancestors": ancestors_list,
                        }
                    ],
                }
            )
        # Reset lists before moving on to the next mapping rule
        descendant_list = []
        ancestors_list = []

    return {"data": data}
