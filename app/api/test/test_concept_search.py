from data.models import Concept, ConceptSynonym, Vocabulary
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


def make_concept(**kwargs):
    defaults = {
        "domain_id": "Drug",
        "vocabulary_id": "RxNorm",
        "concept_class_id": "Ingredient",
        "standard_concept": "S",
        "valid_start_date": "2020-01-01",
        "valid_end_date": "2099-12-31",
    }
    defaults.update(kwargs)
    return Concept.objects.create(**defaults)


class TestConceptSearchView(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="bilbo", password="theshire")
        self.client = APIClient()
        self.url = "/api/v2/omop/conceptsearch/"

        Vocabulary.objects.create(
            vocabulary_id="RxNorm",
            vocabulary_name="RxNorm",
            vocabulary_reference="OMOP generated",
            vocabulary_concept_id=44819117,
        )
        Vocabulary.objects.create(
            vocabulary_id="SNOMED",
            vocabulary_name="SNOMED CT",
            vocabulary_reference="OMOP generated",
            vocabulary_concept_id=44819097,
        )

    def test_requires_authentication(self):
        response = self.client.get(self.url, {"query": "aspirin"})
        self.assertEqual(response.status_code, 401)

    def test_full_phrase_match_ranks_above_partial_word_match(self):
        exact = make_concept(concept_id=1, concept_code="C1", concept_name="Aspirin")
        partial = make_concept(
            concept_id=2,
            concept_code="C2",
            concept_name="Aspirin 81 MG Oral Tablet",
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(self.url, {"query": "Aspirin"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        concept_ids = [r["concept_id"] for r in data["results"]]
        self.assertIn(exact.concept_id, concept_ids)
        self.assertIn(partial.concept_id, concept_ids)
        self.assertLess(
            concept_ids.index(exact.concept_id), concept_ids.index(partial.concept_id)
        )

    def test_finds_concept_via_synonym(self):
        concept = make_concept(
            concept_id=10, concept_code="C10", concept_name="Acetylsalicylic acid"
        )
        ConceptSynonym.objects.create(
            concept_id=concept.concept_id,
            concept_synonym_name="Aspirin",
            language_concept_id=4180186,
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(self.url, {"query": "Aspirin"})

        self.assertEqual(response.status_code, 200)
        concept_ids = [r["concept_id"] for r in response.json()["results"]]
        self.assertIn(concept.concept_id, concept_ids)

    def test_numeric_query_matches_concept_id(self):
        concept = make_concept(
            concept_id=1127433, concept_code="C99", concept_name="Something unrelated"
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(self.url, {"query": "1127433"})

        self.assertEqual(response.status_code, 200)
        concept_ids = [r["concept_id"] for r in response.json()["results"]]
        self.assertIn(concept.concept_id, concept_ids)

    def test_filters_by_facet(self):
        rxnorm = make_concept(
            concept_id=20,
            concept_code="C20",
            concept_name="Ibuprofen",
            vocabulary_id="RxNorm",
        )
        snomed = make_concept(
            concept_id=21,
            concept_code="C21",
            concept_name="Ibuprofen",
            vocabulary_id="SNOMED",
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.url, {"query": "Ibuprofen", "vocabulary_id": "SNOMED"}
        )

        self.assertEqual(response.status_code, 200)
        concept_ids = {r["concept_id"] for r in response.json()["results"]}
        self.assertEqual(concept_ids, {snomed.concept_id})
        self.assertNotIn(rxnorm.concept_id, concept_ids)

    def test_filters_by_comma_separated_facet_values(self):
        rxnorm = make_concept(
            concept_id=22,
            concept_code="C22",
            concept_name="Naproxen",
            vocabulary_id="RxNorm",
        )
        snomed = make_concept(
            concept_id=23,
            concept_code="C23",
            concept_name="Naproxen",
            vocabulary_id="SNOMED",
        )
        make_concept(
            concept_id=24,
            concept_code="C24",
            concept_name="Naproxen",
            vocabulary_id="ICD10",
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.url, {"query": "Naproxen", "vocabulary_id": "RxNorm,SNOMED"}
        )

        self.assertEqual(response.status_code, 200)
        concept_ids = {r["concept_id"] for r in response.json()["results"]}
        self.assertEqual(concept_ids, {rxnorm.concept_id, snomed.concept_id})

    def test_facet_counts_reflect_matching_candidates(self):
        make_concept(
            concept_id=30,
            concept_code="C30",
            concept_name="Paracetamol",
            vocabulary_id="RxNorm",
        )
        make_concept(
            concept_id=31,
            concept_code="C31",
            concept_name="Paracetamol",
            vocabulary_id="SNOMED",
        )

        self.client.force_authenticate(self.user)
        response = self.client.get(self.url, {"query": "Paracetamol"})

        self.assertEqual(response.status_code, 200)
        facets = response.json()["facets"]
        self.assertEqual(facets["vocabulary_id"].get("RxNorm"), 1)
        self.assertEqual(facets["vocabulary_id"].get("SNOMED"), 1)

    def test_pagination(self):
        for i in range(3):
            make_concept(
                concept_id=100 + i,
                concept_code=f"C10{i}",
                concept_name="Metformin",
            )

        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.url, {"query": "Metformin", "page_size": 2, "p": 1}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 2)

        response_page_2 = self.client.get(
            self.url, {"query": "Metformin", "page_size": 2, "p": 2}
        )
        self.assertEqual(len(response_page_2.json()["results"]), 1)
