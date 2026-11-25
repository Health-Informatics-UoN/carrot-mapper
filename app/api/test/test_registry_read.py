import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from registry.models import (
    CARROT_MAPPING_SET_NAMESPACE,
    ImportJob,
    License,
    Mapping,
    MappingSet,
    MappingSetSeries,
    Origin,
    Status,
    Term,
    TermKind,
    TermLevel,
)
from rest_framework.test import APIClient

from test.registry_test_helper import series_id_for

BASE = "/api/v2/registry/"


def make_term(iri, label, kind=TermKind.OBJECT, **kwargs):
    return Term.objects.create(
        canonical_iri=iri,
        label=label,
        kind=kind,
        prefix=iri.split(":", 1)[0],
        **kwargs,
    )


class RegistryReadTestBase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create(username="owner")
        self.other = User.objects.create(username="other")
        self.admin = User.objects.create(username="admin", is_staff=True)
        self.client = APIClient()

        self.license, _ = License.objects.get_or_create(
            id="CC-BY-4.0",
            defaults={
                "license_iri": "https://spdx.org/licenses/CC-BY-4.0",
                "spdx_id": "CC-BY-4.0",
                "label": "Creative Commons Attribution 4.0",
            },
        )

        self.job = ImportJob.objects.create(
            submitted_by=self.owner, origin_id=Origin.SSSOM_UPLOAD
        )
        now = timezone.now()
        self.v1 = self.make_set(
            "Diabetes mappings",
            "1.0.0",
            Status.PUBLISHED,
            published_at=now - timezone.timedelta(days=10),
            creator_ids=["orcid:0000-0001"],
        )
        self.v2 = self.make_set(
            "Diabetes mappings",
            "2.0.0",
            Status.PUBLISHED,
            published_at=now,
        )
        self.withdrawn = self.make_set(
            "Old asthma set", "1.0.0", Status.WITHDRAWN, set_uri="https://x/asthma"
        )
        self.draft = self.make_set(
            "Draft gender set",
            "0.1.0",
            Status.DRAFT,
            set_uri="https://x/draft",
            import_job=self.job,
        )

        # Terms
        self.diabetes = make_term("SNOMED:44054006", "Type 2 diabetes mellitus")
        self.male = make_term("OMOP:8507", "MALE")
        self.subj_field = make_term(
            "carrot:diagnosis",
            "diagnosis",
            kind=TermKind.SUBJECT,
            ext_term_level=TermLevel.FIELD,
            ext_source_field="diagnosis",
        )
        self.subj_value = make_term(
            "carrot:gender/M",
            "gender = M",
            kind=TermKind.SUBJECT,
            ext_term_level=TermLevel.VALUE,
            ext_source_field="gender",
            ext_source_value="M",
        )
        self.draft_only = make_term("OMOP:999", "Secret draft concept")

        self.m1 = self.make_mapping(self.v1, self.subj_field, self.diabetes)
        self.m2 = self.make_mapping(
            self.v2, self.subj_field, self.diabetes, confidence=0.9
        )
        self.m3 = self.make_mapping(self.v2, self.subj_value, self.male, confidence=0.5)
        self.m_withdrawn = self.make_mapping(self.withdrawn, self.subj_value, self.male)
        self.m_draft = self.make_mapping(self.draft, self.subj_value, self.draft_only)

    def make_set(self, title, version, status, set_uri="https://x/diabetes", **kw):
        series, _ = MappingSetSeries.objects.get_or_create(
            set_uri=set_uri, defaults={"id": series_id_for(set_uri)}
        )
        return MappingSet.objects.create(
            series=series,
            set_version=version,
            title=title,
            origin_id=Origin.SSSOM_UPLOAD,
            status_id=status,
            license=self.license,
            object_source="OMOP",
            **kw,
        )

    def make_mapping(self, mapping_set, subject, obj, **kw):
        return Mapping.objects.create(
            mapping_set=mapping_set,
            subject=subject,
            predicate_id="skos:exactMatch",
            object=obj,
            mapping_justification_id="semapv:ManualMappingCuration",
            **kw,
        )

    def get(self, path, user=None, **params):
        self.client.force_authenticate(user)
        return self.client.get(BASE + path, params)

    @staticmethod
    def ids(response):
        return [r["id"] for r in response.data["results"]]


class TestMappingSetList(RegistryReadTestBase):
    def test_anonymous_sees_published_only_by_default(self):
        r = self.get("mapping-sets/")
        self.assertEqual(r.status_code, 200)
        self.assertCountEqual(self.ids(r), [str(self.v1.id), str(self.v2.id)])

    def test_status_filter_opts_in_to_withdrawn(self):
        r = self.get("mapping-sets/", status="WITHDRAWN")
        self.assertEqual(self.ids(r), [str(self.withdrawn.id)])

    def test_drafts_hidden_from_others_even_when_requested(self):
        r = self.get("mapping-sets/", user=self.other, status="DRAFT")
        self.assertEqual(self.ids(r), [])

    def test_drafts_visible_to_submitter_and_admin(self):
        for user in (self.owner, self.admin):
            r = self.get("mapping-sets/", user=user, status="DRAFT")
            self.assertEqual(self.ids(r), [str(self.draft.id)])

    def test_latest_returns_newest_version_per_set_uri(self):
        r = self.get("mapping-sets/", latest="true")
        self.assertEqual(self.ids(r), [str(self.v2.id)])

    def test_latest_is_the_highest_version_not_the_last_published(self):
        v10 = self.make_set(
            "Diabetes mappings",
            "10.0.0",
            Status.PUBLISHED,
            published_at=timezone.now() - timezone.timedelta(days=20),
        )
        self.make_set(
            "Diabetes mappings",
            "9.1.0",
            Status.PUBLISHED,
            published_at=timezone.now() + timezone.timedelta(days=1),
        )
        r = self.get("mapping-sets/", latest="true")
        self.assertEqual(self.ids(r), [str(v10.id)])

    def test_latest_orders_iso_date_versions(self):
        dates = {
            version: self.make_set(
                "Dated set",
                version,
                Status.PUBLISHED,
                set_uri="https://x/dated",
                published_at=timezone.now() - timezone.timedelta(days=i),
            )
            for i, version in enumerate(["2026-01-05", "2026-11-04", "2025-12-31"])
        }
        r = self.get("mapping-sets/", latest="true", set_uri="https://x/dated")
        self.assertEqual(self.ids(r), [str(dates["2026-11-04"].id)])

    def test_creator_id_filter(self):
        r = self.get("mapping-sets/", creator_id="orcid:0000-0001")
        self.assertEqual(self.ids(r), [str(self.v1.id)])

    def test_fuzzy_q_tolerates_misspelling(self):
        r = self.get("mapping-sets/", q="diabetis")
        self.assertCountEqual(self.ids(r), [str(self.v1.id), str(self.v2.id)])

    def test_exact_set_uri_ranks_first(self):
        r = self.get(
            "mapping-sets/", q="https://x/asthma", status="PUBLISHED,WITHDRAWN"
        )
        self.assertEqual(self.ids(r)[0], str(self.withdrawn.id))

    def test_mapping_count(self):
        r = self.get("mapping-sets/", ordering="set_version")
        counts = {row["set_version"]: row["mapping_count"] for row in r.data["results"]}
        self.assertEqual(counts, {"1.0.0": 1, "2.0.0": 2})


class TestMappingSetDetail(RegistryReadTestBase):
    def test_detail_has_counts_and_provenance(self):
        r = self.get(f"mapping-sets/{self.v2.series_id}/versions/{self.v2.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["mapping_count"], 2)
        self.assertEqual(r.data["subject_count"], 2)
        self.assertEqual(r.data["object_count"], 2)
        self.assertEqual(r.data["license"], "CC-BY-4.0")

    def test_withdrawn_resolvable_by_id(self):
        r = self.get(
            f"mapping-sets/{self.withdrawn.series_id}/versions/{self.withdrawn.id}/"
        )
        self.assertEqual(r.status_code, 200)

    def test_draft_404_for_others_200_for_owner(self):
        self.assertEqual(
            self.get(
                f"mapping-sets/{self.draft.series_id}/versions/{self.draft.id}/"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.get(
                f"mapping-sets/{self.draft.series_id}/versions/{self.draft.id}/",
                user=self.other,
            ).status_code,
            404,
        )
        r = self.get(
            f"mapping-sets/{self.draft.series_id}/versions/{self.draft.id}/",
            user=self.owner,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["import_job"]["id"], str(self.job.id))

    def test_set_mappings(self):
        r = self.get(
            f"mapping-sets/{self.v2.series_id}/versions/{self.v2.id}/mappings/"
        )
        self.assertCountEqual(self.ids(r), [self.m2.id, self.m3.id])
        r = self.get(
            f"mapping-sets/{self.draft.series_id}/versions/{self.draft.id}/mappings/"
        )
        self.assertEqual(r.status_code, 404)
        r = self.get(
            f"mapping-sets/{self.draft.series_id}/versions/{self.draft.id}/mappings/",
            user=self.owner,
        )
        self.assertEqual(self.ids(r), [self.m_draft.id])


class TestMappingSearch(RegistryReadTestBase):
    def test_only_published_sets(self):
        r = self.get("mappings/", user=self.owner)
        self.assertCountEqual(self.ids(r), [self.m1.id, self.m2.id, self.m3.id])

    def test_fuzzy_q_on_object_label(self):
        r = self.get("mappings/", q="diabtes")
        self.assertCountEqual(self.ids(r), [self.m1.id, self.m2.id])

    def test_exact_curie_filters(self):
        r = self.get("mappings/", object_id="OMOP:8507")
        self.assertEqual(self.ids(r), [self.m3.id])
        r = self.get("mappings/", subject_id="carrot:diagnosis")
        self.assertCountEqual(self.ids(r), [self.m1.id, self.m2.id])

    def test_confidence_and_term_level(self):
        r = self.get("mappings/", confidence_min=0.8)
        self.assertEqual(self.ids(r), [self.m2.id])
        r = self.get("mappings/", term_level="VALUE")
        self.assertEqual(self.ids(r), [self.m3.id])

    def test_mapping_set_filter(self):
        r = self.get("mappings/", mapping_set=str(self.v1.id))
        self.assertEqual(self.ids(r), [self.m1.id])

    def test_nested_terms_in_response(self):
        r = self.get("mappings/", object_id="OMOP:8507")
        row = r.data["results"][0]
        self.assertEqual(row["subject"]["ext_source_value"], "M")
        self.assertEqual(row["mapping_set"]["id"], str(self.v2.id))


class TestTerms(RegistryReadTestBase):
    def test_terms_from_published_sets_only(self):
        r = self.get("terms/", page_size=50)
        ids = self.ids(r)
        self.assertIn(self.diabetes.id, ids)
        self.assertNotIn(self.draft_only.id, ids)
        self.assertEqual(self.get(f"terms/{self.draft_only.id}/").status_code, 404)

    def test_ranking_exact_then_prefix_then_fuzzy(self):
        prefix = make_term("OMOP:1", "Male gender")
        fuzzy = make_term("OMOP:2", "Female")
        for t in (prefix, fuzzy):
            self.make_mapping(self.v2, self.subj_field, t)

        r = self.get("terms/", q="OMOP:8507")
        self.assertEqual(self.ids(r)[0], self.male.id)

        r = self.get("terms/", q="male")
        ids = self.ids(r)
        # MALE and "Male gender" are prefix matches; "Female" is only fuzzy.
        self.assertLess(ids.index(prefix.id), ids.index(fuzzy.id))
        self.assertLess(ids.index(self.male.id), ids.index(fuzzy.id))

    def test_kind_filter(self):
        r = self.get("terms/", kind="SUBJECT")
        self.assertCountEqual(self.ids(r), [self.subj_field.id, self.subj_value.id])

    def test_term_mappings(self):
        r = self.get(f"terms/{self.male.id}/mappings/")
        self.assertEqual(self.ids(r), [self.m3.id])


class TestVocabularies(RegistryReadTestBase):
    def test_predicates_and_justifications_unpaginated(self):
        r = self.get("predicates/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("skos:exactMatch", [p["predicate_id"] for p in r.data])
        r = self.get("justifications/")
        self.assertIn(
            "semapv:ManualMappingCuration", [j["justification_id"] for j in r.data]
        )


GET_FILE = "registry.views.storage_service.get_file"
SSSOM = b"# mapping_set_id: https://x/diabetes\nsubject_id\tpredicate_id\n"


class TestMappingSetSeries(RegistryReadTestBase):
    def test_series_lists_visible_versions_newest_first(self):
        r = self.get(f"mapping-sets/{self.v1.series_id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["set_uri"], "https://x/diabetes")
        self.assertEqual(
            [v["set_version"] for v in r.data["versions"]], ["2.0.0", "1.0.0"]
        )

    def test_series_hides_versions_the_caller_cant_see(self):
        self.make_set("Diabetes mappings", "3.0.0", Status.DRAFT, import_job=self.job)
        r = self.get(f"mapping-sets/{self.v1.series_id}/")
        self.assertEqual(
            [v["set_version"] for v in r.data["versions"]], ["2.0.0", "1.0.0"]
        )
        r = self.get(f"mapping-sets/{self.v1.series_id}/", user=self.owner)
        self.assertEqual(
            [v["set_version"] for v in r.data["versions"]],
            ["3.0.0", "2.0.0", "1.0.0"],
        )

    def test_series_with_only_hidden_versions_is_404(self):
        path = f"mapping-sets/{self.draft.series_id}/"
        self.assertEqual(self.get(path).status_code, 404)
        self.assertEqual(self.get(path, user=self.other).status_code, 404)
        self.assertEqual(self.get(path, user=self.owner).status_code, 200)

    def test_version_under_another_series_is_404(self):
        path = f"mapping-sets/{self.withdrawn.series_id}/versions/{self.v2.id}/"
        self.assertEqual(self.get(path).status_code, 404)
        self.assertEqual(self.get(path + "mappings/").status_code, 404)
        self.assertEqual(self.get(path + "download/").status_code, 404)

    def test_carrot_set_uri_resolves_to_its_series(self):
        sr_uuid = uuid.uuid4()
        ms = self.make_set(
            "Carrot set",
            "1.0.0",
            Status.PUBLISHED,
            set_uri=f"{CARROT_MAPPING_SET_NAMESPACE}{sr_uuid}",
        )
        self.assertEqual(ms.series_id, sr_uuid)
        r = self.get(f"mapping-sets/{sr_uuid}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["id"], str(sr_uuid))

    def test_external_set_uri_gets_a_random_series_id(self):
        self.assertNotEqual(
            series_id_for("http://pretendurl.com"),
            series_id_for("http://pretendurl.com"),
        )
        self.assertNotEqual(
            series_id_for(f"{CARROT_MAPPING_SET_NAMESPACE}not-a-uuid"),
            series_id_for(f"{CARROT_MAPPING_SET_NAMESPACE}not-a-uuid"),
        )

    def test_versions_carry_their_series(self):
        r = self.get("mapping-sets/", set_uri="https://x/diabetes")
        self.assertEqual(
            {row["series"] for row in r.data["results"]}, {str(self.v1.series_id)}
        )
        r = self.get(
            "mapping-sets/", series=str(self.withdrawn.series_id), status="WITHDRAWN"
        )
        self.assertEqual(self.ids(r), [str(self.withdrawn.id)])


class TestMappingSetDownload(RegistryReadTestBase):
    def setUp(self):
        super().setUp()
        for ms in (self.v2, self.withdrawn, self.draft):
            ms.file_key = f"imports/{ms.pk}/original.sssom.tsv"
            ms.save(update_fields=["file_key"])

    @patch(GET_FILE, return_value=SSSOM)
    def test_download_streams_stored_file(self, get_file):
        r = self.get(
            f"mapping-sets/{self.v2.series_id}/versions/{self.v2.id}/download/"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, SSSOM)
        self.assertTrue(r["Content-Type"].startswith("text/tab-separated-values"))
        self.assertEqual(
            r["Content-Disposition"],
            'attachment; filename="diabetes-mappings-2.0.0.sssom.tsv"',
        )
        get_file.assert_called_once_with(self.v2.file_key, "registry-sssom")

    @patch(GET_FILE, return_value=SSSOM)
    def test_withdrawn_downloadable(self, get_file):
        r = self.get(
            f"mapping-sets/{self.withdrawn.series_id}/versions/{self.withdrawn.id}/download/"
        )
        self.assertEqual(r.status_code, 200)

    @patch(GET_FILE, return_value=SSSOM)
    def test_draft_only_for_submitter(self, get_file):
        path = f"mapping-sets/{self.draft.series_id}/versions/{self.draft.id}/download/"
        self.assertEqual(self.get(path).status_code, 404)
        self.assertEqual(self.get(path, user=self.other).status_code, 404)
        self.assertEqual(self.get(path, user=self.owner).status_code, 200)

    @patch(GET_FILE)
    def test_no_file_key_is_404(self, get_file):
        r = self.get(
            f"mapping-sets/{self.v1.series_id}/versions/{self.v1.id}/download/"
        )
        self.assertEqual(r.status_code, 404)
        get_file.assert_not_called()

    @patch(GET_FILE, side_effect=ValueError("boom"))
    def test_storage_error_is_503(self, get_file):
        r = self.get(
            f"mapping-sets/{self.v2.series_id}/versions/{self.v2.id}/download/"
        )
        self.assertEqual(r.status_code, 503)
