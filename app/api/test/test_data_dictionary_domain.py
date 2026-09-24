"""
Tests for the data dictionary "domain" column (auto-matching source terms to
OMOP concepts within a configured domain).

These exercise pure CSV-parsing logic with no database access, so they don't need
the django_db fixture.
"""

from unittest.mock import patch

from api.serializers import ScanReportFilesSerializer
from django.core.files.uploadedfile import SimpleUploadedFile
from services.storage_service import StorageService
from services.utils import process_domain_dict


def _upload(content: str) -> SimpleUploadedFile:
    return SimpleUploadedFile("dictionary.csv", content.encode("utf-8"))


def _serializer(table_names):
    serializer = ScanReportFilesSerializer()
    serializer.sr_table_names = table_names
    return serializer


def test_process_domain_dict_builds_nested_mapping():
    rows = [
        {"csv_file_name": "table1", "field_name": "field1", "domain": "Drug"},
        {"csv_file_name": "table1", "field_name": "field2", "domain": "Condition"},
        {"csv_file_name": "table2", "field_name": "field1", "domain": "Drug"},
    ]

    assert process_domain_dict(rows) == {
        "table1": {"field1": "Drug", "field2": "Condition"},
        "table2": {"field1": "Drug"},
    }


def test_existing_four_column_header_still_accepted():
    content = (
        "csv_file_name,field_name,code,value\ntable1,field1,vocab_or_code,some value\n"
    )
    serializer = _serializer({"table1"})

    validated = serializer.validate_data_dictionary_file(_upload(content))

    assert validated is not None


def test_five_column_domain_header_accepted_with_domain_only_row():
    content = "csv_file_name,field_name,code,value,domain\ntable1,field1,,,Drug\n"
    serializer = _serializer({"table1"})

    validated = serializer.validate_data_dictionary_file(_upload(content))

    assert validated is not None


def test_five_column_domain_header_accepts_vocab_and_domain_together():
    content = (
        "csv_file_name,field_name,code,value,domain\ntable1,field1,LOINC,,Measurement\n"
    )
    serializer = _serializer({"table1"})

    validated = serializer.validate_data_dictionary_file(_upload(content))

    assert validated is not None


def test_domain_only_row_is_excluded_from_vocab_dictionary():
    """
    Regression test: a domain-only row (empty "code") must not leak into the
    vocab dictionary with an empty vocabulary_id - that previously crashed the
    pre-existing V-concept lookup task, which requires a real vocabulary_id for
    every field_vocab_pair it's given (find_standard_V_concepts.py).
    """
    content = (
        "csv_file_name,field_name,code,value,domain\n"
        "table1,domain_only_field,,,Drug\n"
        "table1,vocab_only_field,LOINC,,\n"
    )
    with patch.object(StorageService, "_get_dictionary_content", return_value=content):
        storage_service = StorageService()
        _, vocab_dictionary, domain_dictionary = storage_service.get_data_dictionary(
            "dictionary.csv"
        )

    assert "domain_only_field" not in vocab_dictionary["table1"]
    assert vocab_dictionary["table1"]["vocab_only_field"] == "LOINC"
    assert domain_dictionary["table1"]["domain_only_field"] == "Drug"


def test_unrecognised_header_still_rejected():
    from rest_framework.exceptions import ParseError

    content = "csv_file_name,field_name,code,value,extra\ntable1,field1,,,x\n"
    serializer = _serializer({"table1"})

    try:
        serializer.validate_data_dictionary_file(_upload(content))
        assert False, "expected a ParseError for an unrecognised header"
    except ParseError:
        pass
