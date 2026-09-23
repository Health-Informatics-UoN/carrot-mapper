from libs.auto_mapping.find_matched_concepts import (
    create_matched_concepts,
    find_matched_concepts,
)


def _kwargs_with_validated_params(validated_params):
    class FakeTaskInstance:
        def xcom_pull(self, task_ids):
            assert task_ids == "validate_params_auto_mapping"
            return validated_params

    return {"ti": FakeTaskInstance()}


def test_find_matched_concepts_skips_when_no_pairs(mocker):
    mock_run = mocker.patch("libs.auto_mapping.find_matched_concepts.pg_hook.run")
    mock_update_job_status = mocker.patch(
        "libs.auto_mapping.find_matched_concepts.update_job_status"
    )

    find_matched_concepts(
        **_kwargs_with_validated_params(
            {
                "scan_report_id": 1,
                "table_id": 2,
                "field_domain_pairs": [],
            }
        )
    )

    mock_run.assert_not_called()
    mock_update_job_status.assert_called_once()
    assert mock_update_job_status.call_args.kwargs["details"] == (
        "Skipped, no field-domain pairs provided"
    )


def test_find_matched_concepts_queries_per_pair(mocker):
    mock_run = mocker.patch("libs.auto_mapping.find_matched_concepts.pg_hook.run")
    mocker.patch("libs.auto_mapping.find_matched_concepts.update_job_status")

    find_matched_concepts(
        **_kwargs_with_validated_params(
            {
                "scan_report_id": 1,
                "table_id": 2,
                "field_domain_pairs": [
                    {
                        "sr_field_id": 10,
                        "field_data_type": "VARCHAR",
                        "domain_id": "Drug",
                    }
                ],
            }
        )
    )

    # First call creates the temp table, second call inserts matches for the pair
    assert mock_run.call_count == 2
    create_table_call, insert_call = mock_run.call_args_list
    assert (
        "CREATE TABLE temp_matched_concepts_%(table_id)s" in create_table_call.args[0]
    )

    insert_query, insert_kwargs = insert_call.args[0], insert_call.kwargs
    assert "LOWER(TRIM(std_concept.concept_name)) = LOWER(TRIM(sr_value.value))" in (
        insert_query
    )
    assert insert_kwargs["parameters"] == {
        "table_id": 2,
        "sr_field_id": 10,
        "domain_id": "Drug",
    }


def test_create_matched_concepts_skips_when_no_pairs(mocker):
    mock_run = mocker.patch("libs.auto_mapping.find_matched_concepts.pg_hook.run")

    create_matched_concepts(
        **_kwargs_with_validated_params(
            {
                "scan_report_id": 1,
                "table_id": 2,
                "field_domain_pairs": [],
            }
        )
    )

    mock_run.assert_not_called()


def test_create_matched_concepts_inserts_with_matched_creation_type(mocker):
    mock_run = mocker.patch("libs.auto_mapping.find_matched_concepts.pg_hook.run")
    mocker.patch("libs.auto_mapping.find_matched_concepts.update_job_status")

    create_matched_concepts(
        **_kwargs_with_validated_params(
            {
                "scan_report_id": 1,
                "table_id": 2,
                "field_domain_pairs": [
                    {
                        "sr_field_id": 10,
                        "field_data_type": "VARCHAR",
                        "domain_id": "Drug",
                    }
                ],
            }
        )
    )

    mock_run.assert_called_once()
    query, kwargs = mock_run.call_args.args[0], mock_run.call_args.kwargs
    assert "'X',           -- Creation type: Matched by term/domain lookup" in query
    assert "'term-match'" in query
    assert kwargs["parameters"] == {"table_id": 2}
