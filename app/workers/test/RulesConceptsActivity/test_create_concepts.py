import pytest
from RulesConceptsActivity import (_create_concepts,
                                   _match_concepts_to_entries,
                                   _set_defaults_for_none_vocab,
                                   _update_entries_with_standard_concepts)
from shared.data.models import Concept


def test__create_concepts():
    # Arrange
    table_values = [
        {"concept_id": 1, "id": 1},
        {"concept_id": [2, 3], "id": 2},
        {"concept_id": -1, "id": 3},
        {"concept_id": 4, "id": 4},
    ]

    # Act
    result = _create_concepts(table_values)

    # Assert
    expected_result = [
        {"concept_id": 1, "object_id": 1, "creation_type": "V"},
        {"concept_id": 2, "object_id": 2, "creation_type": "V"},
        {"concept_id": 3, "object_id": 2, "creation_type": "V"},
        {"concept_id": 4, "object_id": 4, "creation_type": "V"},
    ]

    assert len(result) == len(expected_result)
    for res, exp in zip(result, expected_result):
        assert res.concept_id == exp["concept_id"]
        assert res.object_id == exp["object_id"]
        assert res.creation_type == exp["creation_type"]


def test__set_defaults_for_none_vocab():
    # Arrange
    entries = [{"concept_id": 1, "standard_concept": "test"}]

    # Act
    _set_defaults_for_none_vocab(entries)

    # Assert
    entries == [{"concept_id": -1, "standard_concept": None}]


def test__match_concepts_to_entries():
    # Arrange
    entries = [
        {"value": 1, "concept_id": 1, "standard_concept": "standard 1"},
        {"value": 2, "concept_id": 1, "standard_concept": "standard 2"},
    ]
    vocab = [Concept(concept_code=2, concept_id="200", standard_concept="S")]

    # Act
    _match_concepts_to_entries(entries, vocab)

    # Assert
    assert entries == [
        {"value": 1, "concept_id": -1, "standard_concept": None},
        {"value": 2, "concept_id": "200", "standard_concept": "S"},
    ]


def test__update_entries_with_standard_concepts():
    # Arrange
    entries = [
        {"concept_id": "nonstandard1", "data": "data1"},
        {"concept_id": "nonstandard2", "data": "data2"},
        {"concept_id": "nonstandard3", "data": "data3"},
    ]
    standard_concepts_map = {
        "nonstandard1": ["standard1a", "standard1b"],
        "nonstandard2": ["standard2a"],
        "nonstandard3": ["standard3a", "standard3b", "standard3c"],
    }

    # Act
    _update_entries_with_standard_concepts(entries, standard_concepts_map)

    # Assert
    assert entries == [
        {"concept_id": ["standard1a", "standard1b"], "data": "data1"},
        {"concept_id": ["standard2a"], "data": "data2"},
        {"concept_id": ["standard3a", "standard3b", "standard3c"], "data": "data3"},
    ]


def test__update_entries_with_standard_concepts_warning():
    # Arrange
    entries = [
        {"concept_id": "nonstandard1", "data": "data1"},
        {"concept_id": "", "data": "data2"},
        {"concept_id": "nonstandard3", "data": "data3"},
    ]
    standard_concepts_map = {
        "nonstandard1": ["standard1a", "standard1b"],
        "nonstandard2": ["standard2a"],
        "nonstandard3": ["standard3a", "standard3b", "standard3c"],
    }

    # Act & Assert
    with pytest.raises(RuntimeWarning):
        _update_entries_with_standard_concepts(entries, standard_concepts_map)
