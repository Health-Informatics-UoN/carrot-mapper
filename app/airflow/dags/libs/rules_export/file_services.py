import logging
from contextlib import closing
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any

from libs.db import pg_hook
from libs.enums import JobStageType, StageStatusType
from libs.rules_export.formats import rules_to_csv, rules_to_json_v1, rules_to_json_v2
from libs.rules_export.sssom import write_sssom_tsv
from libs.utils import update_job_status


def _fetch_rows(query: str, scan_report_id: int) -> list[dict[str, Any]]:
    """
    Run a query for a scan report and return its rows as plain dicts
    (column name -> value, NULL -> None), without building a DataFrame.
    """
    with closing(pg_hook.get_conn()) as conn, conn.cursor() as cursor:
        cursor.execute(query, {"scan_report_id": scan_report_id})
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _to_bytes(text: str) -> BytesIO:
    file = BytesIO(text.encode("utf-8"))
    file.seek(0)
    return file


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
        rules = _fetch_rows(
            "SELECT * FROM temp_rules_export_%(scan_report_id)s_csv ORDER BY sr_concept_id;",
            scan_report_id,
        )
        # Validity of each concept is checked against today's date
        return _to_bytes(rules_to_csv(rules, today=date.today()))
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
        metadata = {
            "date_created": datetime.now(timezone.utc).isoformat(),
            "dataset": scan_report_name,
        }
        rules = _fetch_rows(
            "SELECT * FROM temp_rules_export_%(scan_report_id)s_json ORDER BY sr_concept_id;",
            scan_report_id,
        )
        return _to_bytes(rules_to_json_v1(rules, metadata))
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
    Builds the rules in JSON v2 format.

    Args:
        - scan_report_name: str, the name of the scan report
        - scan_report_id: int, the id of the scan report

    Returns:
        - BytesIO, the rules in JSON v2 format
    """
    try:
        metadata = {
            "date_created": datetime.now(timezone.utc).isoformat(),
            "dataset": scan_report_name,
        }
        rules = _fetch_rows(
            "SELECT * FROM temp_rules_export_%(scan_report_id)s_json ORDER BY dest_table, source_table, source_field;",
            scan_report_id,
        )
        return _to_bytes(rules_to_json_v2(rules, metadata))
    except Exception as e:
        logging.error(f"Error building rules JSON v2: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Error building rules JSON v2 for scan report {scan_report_id}: {str(e)}",
        )
        raise e


def build_rules_sssom(
    scan_report_id: int, mapper_version: str | None = None
) -> BytesIO:
    """
    Builds the rules as an SSSOM TSV file (see libs/rules_export/sssom.py).

    Args:
        - scan_report_id: int, the id of the scan report
        - mapper_version: str, the exporting Carrot-Mapper version, if known

    Returns:
        - BytesIO, the rules in SSSOM TSV format
    """
    # Only the *_concept_id rules: each carries its mapping's concept, while the
    # other rules Mapper creates for a mapping (source values, person_id, dates)
    # aren't written to SSSOM. Concept domain, vocabulary and vocabulary version
    # are for SSSOM's object_category / other / object_source_version.
    query = """
        SELECT
            temp_rules.sr_concept_id,
            temp_rules.source_field,
            temp_rules.term_mapping_value,
            temp_rules.dest_field,
            temp_rules.concept_id,
            temp_rules.concept_name,
            temp_rules.creation_type,
            temp_rules.confidence,
            temp_rules.description,
            temp_rules.created_at,
            omop_concept.domain_id AS concept_domain,
            omop_concept.vocabulary_id AS concept_vocabulary,
            omop_vocabulary.vocabulary_version
        FROM temp_rules_export_%(scan_report_id)s_sssom AS temp_rules
        LEFT JOIN omop.concept AS omop_concept
            ON omop_concept.concept_id = temp_rules.concept_id
        LEFT JOIN omop.vocabulary AS omop_vocabulary
            ON omop_vocabulary.vocabulary_id = omop_concept.vocabulary_id
        WHERE right(temp_rules.dest_field, 11) = '_concept_id'
        ORDER BY
            temp_rules.source_table,
            temp_rules.source_field,
            temp_rules.sr_concept_id,
            temp_rules.dest_table,
            temp_rules.dest_field;
    """
    try:
        rules = _fetch_rows(query, scan_report_id)
        sssom_tsv = write_sssom_tsv(
            rules,
            created=datetime.now(timezone.utc),
            mapper_version=mapper_version,
        )
        return _to_bytes(sssom_tsv)
    except Exception as e:
        logging.error(f"Error building rules SSSOM: {str(e)}")
        update_job_status(
            scan_report=scan_report_id,
            stage=JobStageType.DOWNLOAD_RULES,
            status=StageStatusType.FAILED,
            details=f"Error building rules SSSOM for scan report {scan_report_id}: {str(e)}",
        )
        raise e
