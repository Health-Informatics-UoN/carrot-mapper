from libs.auto_mapping.find_standard_V_concepts import find_standard_concepts


def _kwargs_with_validated_params(validated_params):
    class FakeTaskInstance:
        def xcom_pull(self, task_ids):
            assert task_ids == "validate_params_auto_mapping"
            return validated_params

    return {"ti": FakeTaskInstance()}


def test_find_standard_concepts_follows_only_valid_maps_to(mocker):
    mock_run = mocker.patch("libs.auto_mapping.find_standard_V_concepts.pg_hook.run")
    mocker.patch("libs.auto_mapping.find_standard_V_concepts.update_job_status")

    find_standard_concepts(
        **_kwargs_with_validated_params(
            {
                "scan_report_id": 1,
                "table_id": 2,
                "field_vocab_pairs": [
                    {
                        "sr_field_id": 10,
                        "field_data_type": "VARCHAR",
                        "vocabulary_id": "icd10",
                    }
                ],
            }
        )
    )

    # First call creates the temp table, second call inserts the concepts for the pair
    assert mock_run.call_count == 2
    insert_query, insert_kwargs = (
        mock_run.call_args_list[1].args[0],
        mock_run.call_args_list[1].kwargs,
    )
    assert "concept_relationship.relationship_id = 'Maps to'" in insert_query
    # A deprecated 'Maps to' row (invalid_reason 'D' or 'U') points at a concept
    # the source code no longer maps to, so it must not create a concept.
    assert "concept_relationship.invalid_reason IS NULL" in insert_query
    assert insert_kwargs["parameters"]["vocabulary_id"] == "ICD10"
