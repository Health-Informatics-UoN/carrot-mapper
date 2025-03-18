from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from openpyxl.cell.cell import Cell
from UploadQueue import (_apply_data_dictionary, _assign_order,
                         _create_field_entry, _create_table_entry,
                         _create_value_entries, _create_values_details,
                         _get_unique_table_names)


def test__get_unique_table_names():
    # Arrange
    worksheet_mock = MagicMock()

    sample_worksheet_data = [
        ["Table1"],
        ["Table2"],
        ["Table1"],
        ["Table3"],
        ["Table2"],
        ["Table4"],
    ]

    # Mock iter_rows
    worksheet_mock.iter_rows = MagicMock(
        return_value=(
            [MagicMock(value=cell_value) for cell_value in row_data]
            for row_data in sample_worksheet_data
        )
    )

    # Act
    result = _get_unique_table_names(worksheet_mock)

    # Assert
    expected_result = ["Table1", "Table2", "Table3", "Table4"]
    assert result == expected_result


def test__create_table_entry():
    # Arrange
    table_name = "SampleTableName"
    scan_report_id = "1"
    expected_datetime = "2024-02-29T00:00:00.000000Z"

    # Mock datetime to fixed
    with patch("UploadQueue.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 2, 29, tzinfo=timezone.utc)

        # Act
        result = _create_table_entry(table_name, scan_report_id)

    # Assert
    expected_result = {
        "created_at": expected_datetime,
        "updated_at": expected_datetime,
        "name": "SampleTableName",
        "scan_report": "1",
        "person_id": None,
        "birth_date": None,
        "measurement_date": None,
        "condition_date": None,
        "observation_date": None,
    }
    assert result == expected_result


def test__create_field_entry():
    # Arrange
    row = (
        Cell(None, value="empty_row"),
        Cell(None, value="sample_name"),
        Cell(None, value="sample_description"),
        Cell(None, value="sample_type"),
        Cell(None, value="sample_max_length"),
        Cell(None, value="sample_nrows"),
        Cell(None, value="sample_nrows_checked"),
        Cell(None, value=None),
        Cell(None, value="sample_nunique_values"),
        Cell(None, value=None),
    )
    scan_report_table_id = "1"
    expected_datetime = "2024-02-29T00:00:00.000000Z"

    # Mock datetime.now to fix
    with patch("UploadQueue.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 2, 29, tzinfo=timezone.utc)

        # Act
        result = _create_field_entry(row, scan_report_table_id)

    # Assert
    expected_result = {
        "scan_report_table": "1",
        "created_at": expected_datetime,
        "updated_at": expected_datetime,
        "name": "sample_name",
        "description_column": "sample_description",
        "type_column": "sample_type",
        "max_length": "sample_max_length",
        "nrows": "sample_nrows",
        "nrows_checked": "sample_nrows_checked",
        "fraction_empty": 0.0,
        "nunique_values": "sample_nunique_values",
        "fraction_unique": 0.0,
        "ignore_column": None,
    }
    assert result == expected_result


def test__create_values_details():
    # Arrange
    table_name = "test_table"

    fieldname_value_freq = {
        "field1": [("value1", "10"), ("value2", "20")],
        "field2": [("value3", "30"), ("value4", "40")],
    }

    # Act
    result = _create_values_details(fieldname_value_freq, table_name)

    # Assert
    expected = [
        {
            "full_value": "value1",
            "frequency": 10,
            "fieldname": "field1",
            "table": "test_table",
            "val_desc": None,
        },
        {
            "full_value": "value2",
            "frequency": 20,
            "fieldname": "field1",
            "table": "test_table",
            "val_desc": None,
        },
        {
            "full_value": "value3",
            "frequency": 30,
            "fieldname": "field2",
            "table": "test_table",
            "val_desc": None,
        },
        {
            "full_value": "value4",
            "frequency": 40,
            "fieldname": "field2",
            "table": "test_table",
            "val_desc": None,
        },
    ]

    assert result == expected


def test__assign_order():
    # Arrange
    values_details = [
        {
            "full_value": "value1",
            "frequency": 10,
            "fieldname": "field1",
            "table": "test_table",
            "val_desc": None,
        },
        {
            "full_value": "value2",
            "frequency": 20,
            "fieldname": "field1",
            "table": "test_table",
            "val_desc": None,
        },
        {
            "full_value": "value3",
            "frequency": 30,
            "fieldname": "field2",
            "table": "test_table",
            "val_desc": None,
        },
    ]

    # Act
    _assign_order(values_details)

    # Assert
    for i, entry in enumerate(values_details):
        assert entry["order"] == i


def test__apply_data_dictionary():
    # Arrange
    values_details = [
        {
            "full_value": "value1",
            "frequency": 10,
            "fieldname": "field1",
            "table": "test_table",
            "val_desc": None,
        },
        {
            "full_value": "value2",
            "frequency": 20,
            "fieldname": "field1",
            "table": "test_table",
            "val_desc": None,
        },
        {
            "full_value": "value3",
            "frequency": 30,
            "fieldname": "field2",
            "table": "test_table",
            "val_desc": None,
        },
    ]

    data_dictionary = {
        "test_table": {
            "field1": {
                "value1": "description1",
                "value2": "description2",
            },
            "field2": {
                "value3": "description3",
            },
        }
    }

    # Act
    _apply_data_dictionary(values_details, data_dictionary)

    # Assert
    assert values_details[0]["val_desc"] == "description1"
    assert values_details[1]["val_desc"] == "description2"
    assert values_details[2]["val_desc"] == "description3"


def test__create_value_entries():
    # Arrange
    values_details = [
        {
            "full_value": "value1",
            "frequency": 10,
            "fieldname": "field1",
            "val_desc": "description1",
        },
        {
            "full_value": "value2",
            "frequency": 20,
            "fieldname": "field1",
            "val_desc": "description2",
        },
    ]

    fieldnames_to_ids_dict = {
        "field1": "field_id_1",
        "field2": "field_id_2",
    }

    # Mock datetime
    expected_datetime = "2024-02-29T00:00:00.000000Z"
    with patch("UploadQueue.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 2, 29, tzinfo=timezone.utc)

        # Act
        result = _create_value_entries(values_details, fieldnames_to_ids_dict)

    # Assert
    for i, entry in enumerate(result):
        assert entry["created_at"] == expected_datetime
        assert entry["updated_at"] == expected_datetime
        assert entry["value"] == values_details[i]["full_value"]
        assert entry["frequency"] == values_details[i]["frequency"]
        assert entry["value_description"] == values_details[i]["val_desc"]
        assert (
            entry["scan_report_field"]
            == fieldnames_to_ids_dict[values_details[i]["fieldname"]]
        )
