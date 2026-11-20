from collections import defaultdict

from libs.SR_processing.db_services import create_temp_field_values_table


def test_empty_table_still_gets_a_field_values_table(mocker):
    """
    A scan report table with no values (e.g. one WhiteRabbit couldn't read)
    still needs its temp table: creating the scan report values selects from
    it for every table.
    """
    mock_run = mocker.patch("libs.SR_processing.db_services.pg_hook.run")
    mock_conn = mocker.patch("libs.SR_processing.db_services.pg_hook.get_conn")

    create_temp_field_values_table(defaultdict(list), table_id=7)

    mock_run.assert_called_once()
    assert "CREATE TABLE IF NOT EXISTS temp_field_values_" in mock_run.call_args.args[0]
    assert mock_run.call_args.kwargs["parameters"] == {"table_id": 7}
    mock_conn.assert_not_called()  # nothing to copy in


def test_table_with_values_is_created_and_filled(mocker):
    mock_run = mocker.patch("libs.SR_processing.db_services.pg_hook.run")
    mock_conn = mocker.patch("libs.SR_processing.db_services.pg_hook.get_conn")
    copy = mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.copy.return_value.__enter__.return_value

    create_temp_field_values_table(
        defaultdict(list, {"sex": [("F", 3), ("M", "")]}), table_id=7
    )

    mock_run.assert_called_once()
    assert [c.args[0] for c in copy.write_row.call_args_list] == [
        ("sex", "F", 3),
        ("sex", "M", 0),
    ]
