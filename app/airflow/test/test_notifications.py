from libs.notifications import NotificationType, create_notification


def test_create_notification_inserts_with_expected_query_and_params(mocker):
    mock_run = mocker.patch("libs.notifications.pg_hook.run")

    create_notification(
        scan_report_id=42,
        notif_type=NotificationType.SCAN_REPORT_PROCESSING_COMPLETE,
        text="Your scan report has finished processing",
        url="/scanreports/42",
    )

    mock_run.assert_called_once()
    query, kwargs = mock_run.call_args.args[0], mock_run.call_args.kwargs
    assert "INSERT INTO notifications_notification" in query
    assert "FROM mapping_scanreport" in query
    assert "WHERE id = %(scan_report_id)s" in query
    assert kwargs["parameters"] == {
        "scan_report_id": 42,
        "notif_type": NotificationType.SCAN_REPORT_PROCESSING_COMPLETE,
        "text": "Your scan report has finished processing",
        "url": "/scanreports/42",
    }


def test_create_notification_defaults_url_to_empty_string(mocker):
    mock_run = mocker.patch("libs.notifications.pg_hook.run")

    create_notification(
        scan_report_id=1,
        notif_type=NotificationType.AUTOMAP_FAILED,
        text="Auto-mapping failed for your scan report",
    )

    assert mock_run.call_args.kwargs["parameters"]["url"] == ""


def test_create_notification_swallows_db_errors(mocker):
    mock_run = mocker.patch(
        "libs.notifications.pg_hook.run", side_effect=Exception("db is down")
    )

    # Should not raise - a missing notification must never fail the DAG run.
    create_notification(
        scan_report_id=1,
        notif_type=NotificationType.RULES_EXPORT_FAILED,
        text="Your rules export failed",
    )

    mock_run.assert_called_once()
