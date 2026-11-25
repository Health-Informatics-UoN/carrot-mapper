import hashlib
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from mapping.models import ScanReport
from registry.models import (
    ImportJob,
    ImportJobStatus,
    License,
    MappingSet,
    Origin,
    Prefix,
    Status,
)
from registry.validation import MAX_SAMPLE_ROWS, RESERVED_PREFIXES
from rest_framework.test import APIClient

BASE = "/api/v2/registry/imports/"
LICENSE_IRI = "https://spdx.org/licenses/CC-BY-4.0.html"
HEADER = "subject_id\tpredicate_id\tobject_id\tmapping_justification\tconfidence"


def sssom(
    set_uri="https://example.org/sets/a",
    version='"1.0.0"',
    license_iri=LICENSE_IRI,
    curie_map=None,
    rows=None,
    header=HEADER,
):
    curie_map = curie_map or {
        "EX": "https://example.org/ex/",
        "OMOP": RESERVED_PREFIXES["OMOP"],
    }
    lines = ["#curie_map:"]
    lines += [f"#  {name}: {namespace}" for name, namespace in curie_map.items()]
    if set_uri:
        lines.append(f"#mapping_set_id: {set_uri}")
    if version:
        lines.append(f"#mapping_set_version: {version}")
    if license_iri:
        lines.append(f"#license: {license_iri}")
    lines.append("#mapping_set_title: A set")
    lines.append(header)
    if rows is None:
        rows = ["EX:1\tskos:exactMatch\tOMOP:2\tsemapv:ManualMappingCuration\t0.5"]
    return ("\n".join(lines + rows) + "\n").encode()


class UploadTestBase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(username="uploader")
        self.other = User.objects.create(username="other")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.license, _ = License.objects.get_or_create(
            id="CC-BY-4.0",
            defaults={
                "license_iri": LICENSE_IRI,
                "spdx_id": "CC-BY-4.0",
                "label": "Creative Commons Attribution 4.0",
                "see_also": ["https://creativecommons.org/licenses/by/4.0/legalcode"],
            },
        )

        storage = patch("registry.services.StorageService")
        worker = patch("registry.services.worker_service")
        self.storage = storage.start().return_value
        self.worker = worker.start()
        self.worker.trigger_registry_import.return_value = "manual__1"
        self.addCleanup(storage.stop)
        self.addCleanup(worker.stop)

    def make_set(self, publisher=None, version="1.0.0", **kwargs):
        return MappingSet.objects.create(
            set_uri="https://example.org/sets/a",
            set_version=version,
            title="Existing",
            origin_id=Origin.SSSOM_UPLOAD,
            status_id=Status.PUBLISHED,
            publisher=publisher,
            **kwargs,
        )

    def send(self, url, content, name="set.sssom.tsv", headers=None, **fields):
        file = SimpleUploadedFile(name, content, content_type="text/plain")
        return self.client.post(
            url, {"file": file, **fields}, format="multipart", headers=headers
        )

    def validate(self, content, **kwargs):
        return self.send(f"{BASE}validate/", content, **kwargs)

    def upload(self, content=None, **kwargs):
        return self.send(BASE, sssom() if content is None else content, **kwargs)

    @staticmethod
    def codes(response, level="error"):
        return {i["code"] for i in response.data["issues"] if i["level"] == level}


class TestValidate(UploadTestBase):
    def assert_rejected(self, content, code, **kwargs):
        r = self.validate(content, **kwargs)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["valid"])
        self.assertIn(code, self.codes(r))
        return r

    def test_valid_file_stores_and_starts_nothing(self):
        r = self.validate(sssom())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["valid"], r.data["issues"])
        self.assertEqual(r.data["set_uri"], "https://example.org/sets/a")
        self.assertEqual(r.data["set_version"], "1.0.0")
        self.assertEqual(r.data["title"], "A set")
        self.assertEqual(r.data["license"], "CC-BY-4.0")
        self.assertEqual(r.data["rows_checked"], 1)
        self.assertFalse(ImportJob.objects.exists())
        self.storage.upload_file.assert_not_called()
        self.worker.trigger_registry_import.assert_not_called()

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.validate(sssom()).status_code, 401)
        self.assertEqual(self.upload().status_code, 401)

    def test_file_is_required(self):
        r = self.client.post(f"{BASE}validate/", {}, format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertIn("file", r.data)

    def test_file_envelope(self):
        self.assert_rejected(sssom(), "invalid_file_type", name="set.csv")
        self.assert_rejected(b"\xff\xfe", "invalid_encoding")
        self.assert_rejected(b"", "missing_metadata")
        with override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=10):
            self.assert_rejected(sssom(), "file_too_large")

    def test_tsv_extension_and_byte_order_mark_are_accepted(self):
        r = self.validate(b"\xef\xbb\xbf" + sssom(), name="set.TSV")
        self.assertTrue(r.data["valid"], r.data["issues"])
        self.assertIn("byte_order_mark", self.codes(r, "warning"))

    def test_metadata_problems(self):
        self.assert_rejected(b"#a: [\nsubject_id\n", "invalid_metadata")
        self.assert_rejected(b"#- a\nsubject_id\n", "invalid_metadata")
        self.assert_rejected(sssom(set_uri=None), "missing_metadata_slot")
        self.assert_rejected(sssom(version=None), "missing_metadata_slot")
        self.assert_rejected(sssom(license_iri=None), "missing_metadata_slot")
        self.assert_rejected(sssom(set_uri="https://x/" + "a" * 500), "value_too_long")

    def test_yaml_aliases_are_refused(self):
        content = b"#a: &x [1]\n#b: *x\n" + sssom()
        self.assert_rejected(content, "invalid_metadata")

    def test_oversized_metadata_is_refused_before_parsing(self):
        content = b"#c: x\n" * 200_000 + sssom()
        self.assert_rejected(content, "metadata_too_large")

    def test_unquoted_number_version_is_read_as_text_and_refused(self):
        r = self.assert_rejected(sssom(version="1.0"), "invalid_set_version")
        self.assertEqual(r.data["set_version"], "1.0")
        self.assertIn("coerced_value", self.codes(r, "warning"))

    def test_set_version_format(self):
        for version in ('"1.0.0"', "1.0.0", '"2026-11-04"', "2026-11-04"):
            with self.subTest(version=version):
                r = self.validate(sssom(version=version))
                self.assertTrue(r.data["valid"], r.data["issues"])
        for version in ('"v1"', '"1.0"', '"01.0.0"', '"2026-13-01"', '"1.0.0-rc1"'):
            with self.subTest(version=version):
                self.assert_rejected(sssom(version=version), "invalid_set_version")

    def test_new_version_must_be_higher_and_the_same_scheme(self):
        self.make_set(publisher=self.user, version="1.2.0")
        for version, code in (
            ('"1.1.0"', "set_version_not_newer"),
            ('"2026-11-04"', "set_version_scheme_mismatch"),
        ):
            with self.subTest(version=version):
                self.assert_rejected(sssom(version=version), code)
        self.assertTrue(self.validate(sssom(version='"1.10.0"')).data["valid"])

    def test_namespace_rules(self):
        for curie_map, code in (
            ({"EX": "banana"}, "invalid_namespace"),
            ({"EX": "ftp://example.org/"}, "invalid_namespace"),
            ({"EX": "http://[broken"}, "invalid_namespace"),
            ({"EX": "https://x/" + "a" * 1000}, "value_too_long"),
            ({"skos": "https://example.org/"}, "builtin_prefix_redefined"),
            ({"carrot": "https://example.org/"}, "prefix_conflict"),
            ({"not valid": "https://example.org/"}, "invalid_curie_map"),
        ):
            with self.subTest(code=code, curie_map=curie_map):
                self.assert_rejected(sssom(curie_map=curie_map), code)

    def test_registered_prefix_cannot_be_rebound_by_a_used_curie(self):
        Prefix.objects.create(prefix="EX", namespace="https://elsewhere.org/")
        self.assert_rejected(sssom(), "prefix_conflict")

    def test_registered_namespace_may_use_another_name(self):
        Prefix.objects.create(prefix="canon", namespace="https://example.org/ex/")
        self.assertTrue(self.validate(sssom()).data["valid"])

    def test_header_problems(self):
        self.assert_rejected(
            sssom(header="subject_id\tpredicate_id\tobject_id", rows=[]),
            "missing_column",
        )
        self.assert_rejected(
            sssom(header=HEADER + "\tconfidence", rows=[]), "duplicate_column"
        )
        self.assert_rejected(sssom(rows=[]), "no_mappings")

    def test_unknown_column_is_a_warning(self):
        row = "EX:1\tskos:exactMatch\tOMOP:2\tsemapv:ManualMappingCuration\t0.5\tx"
        r = self.validate(sssom(header=HEADER + "\tmy_column", rows=[row]))
        self.assertTrue(r.data["valid"], r.data["issues"])
        self.assertIn("unknown_column", self.codes(r, "warning"))

    def test_row_problems_report_their_line(self):
        good = ["EX:1", "skos:exactMatch", "OMOP:2", "semapv:ManualMappingCuration"]
        for index, value, confidence, code in (
            (0, "", "0.5", "missing_value"),
            (0, "no-prefix", "0.5", "invalid_curie"),
            (0, "NOPE:1", "0.5", "undeclared_prefix"),
            (1, "skos:madeUp", "0.5", "unknown_predicate"),
            (3, "semapv:MadeUp", "0.5", "unknown_justification"),
            (0, "EX:1", "high", "invalid_number"),
            (0, "EX:1", "1.5", "schema_violation"),
        ):
            with self.subTest(code=code):
                values = list(good)
                values[index] = value
                row = "\t".join(values + [confidence])
                r = self.assert_rejected(sssom(rows=[row]), code)
                issue = next(i for i in r.data["issues"] if i["code"] == code)
                self.assertEqual(issue["line"], 9)

    def test_wrong_length_and_duplicate_rows(self):
        self.assert_rejected(sssom(rows=["EX:1\tskos:exactMatch"]), "row_length")
        row = "EX:1\tskos:exactMatch\tOMOP:2\tsemapv:ManualMappingCuration\t0.5"
        self.assert_rejected(sssom(rows=[row, row]), "duplicate_mapping")

    def test_only_the_first_rows_are_checked(self):
        row = "EX:{}\tskos:exactMatch\tOMOP:2\tsemapv:ManualMappingCuration\t0.5"
        rows = [row.format(i) for i in range(MAX_SAMPLE_ROWS)] + ["broken"]
        r = self.validate(sssom(rows=rows))
        self.assertTrue(r.data["valid"], r.data["issues"][:3])
        self.assertEqual(r.data["rows_checked"], MAX_SAMPLE_ROWS)

    def test_issue_list_is_capped(self):
        r = self.validate(sssom(rows=["broken"] * 500))
        self.assertLessEqual(len(r.data["issues"]), 201)
        self.assertIn("issues_truncated", self.codes(r, "warning"))

    def test_license_matching(self):
        for iri in (
            LICENSE_IRI,
            "https://spdx.org/licenses/CC-BY-4.0",
            "http://spdx.org/licenses/CC-BY-4.0/",
            "https://creativecommons.org/licenses/by/4.0/legalcode",
        ):
            with self.subTest(iri=iri):
                r = self.validate(sssom(license_iri=iri))
                self.assertEqual(r.data["license"], "CC-BY-4.0")

    def test_unknown_license_is_a_warning(self):
        r = self.validate(sssom(license_iri="https://example.org/my-licence"))
        self.assertTrue(r.data["valid"], r.data["issues"])
        self.assertIsNone(r.data["license"])
        self.assertIn("unknown_license", self.codes(r, "warning"))

    def test_set_identity_conflicts(self):
        self.make_set(publisher=self.other, version="0.9.0")
        r = self.assert_rejected(sssom(), "set_uri_not_owned")
        self.assertEqual(r.status_code, 200)

    def test_existing_version(self):
        self.make_set(publisher=self.user)
        self.assert_rejected(sssom(), "set_version_exists")

    def test_publisher_can_add_a_version(self):
        self.make_set(publisher=self.user, version="0.9.0")
        self.assertTrue(self.validate(sssom()).data["valid"])

    def test_local_scan_report_uri_is_reserved(self):
        report = ScanReport.objects.create(name="Report", dataset="Data")
        uri = f"https://carrot.ac.uk/registry/mapping-sets/{report.uuid}"
        self.assert_rejected(sssom(set_uri=uri), "set_uri_reserved")

    def test_other_instances_scan_report_uri_is_allowed(self):
        uri = f"https://carrot.ac.uk/registry/mapping-sets/{uuid.uuid4()}"
        self.assertTrue(self.validate(sssom(set_uri=uri)).data["valid"])

    def test_reserved_prefixes_match_the_seeded_rows(self):
        seeded = dict(
            Prefix.objects.filter(prefix__in=RESERVED_PREFIXES).values_list(
                "prefix", "namespace"
            )
        )
        self.assertEqual(seeded, RESERVED_PREFIXES)


class TestUpload(UploadTestBase):
    def test_accepted_upload_is_stored_and_started(self):
        content = sssom()
        r = self.upload(content)
        self.assertEqual(r.status_code, 202, r.data)
        job = ImportJob.objects.get()
        self.assertEqual(r.data["import_job_id"], str(job.id))
        self.assertEqual(r.data["status"], ImportJobStatus.PENDING)
        self.assertEqual(r.headers["Location"], f"{BASE}{job.id}/")
        self.assertEqual(job.submitted_by, self.user)
        self.assertEqual(job.origin_id, Origin.SSSOM_UPLOAD)
        self.assertEqual(job.file_key, f"imports/{job.id}/original.sssom.tsv")
        self.assertEqual(job.dag_run_id, "manual__1")
        self.assertEqual(job.params["sha256"], hashlib.sha256(content).hexdigest())

        args, kwargs = self.storage.upload_file.call_args
        self.assertEqual(args[0], job.file_key)
        self.assertEqual(args[1], "registry-sssom")
        self.assertEqual(args[2].getvalue(), content)
        self.assertTrue(kwargs["use_read_method"])
        self.worker.trigger_registry_import.assert_called_once_with(
            {
                "import_job_id": str(job.id),
                "origin": Origin.SSSOM_UPLOAD,
                "user_id": self.user.pk,
                "file_key": job.file_key,
                "overrides": {"status": Status.PUBLISHED, "license": "CC-BY-4.0"},
            }
        )

    def test_draft_can_be_requested(self):
        self.assertEqual(self.upload(status=Status.DRAFT).status_code, 202)
        conf = self.worker.trigger_registry_import.call_args.args[0]
        self.assertEqual(conf["overrides"]["status"], Status.DRAFT)

    def test_withdrawn_status_is_refused(self):
        r = self.upload(status=Status.WITHDRAWN)
        self.assertEqual(r.status_code, 400)
        self.assertIn("status", r.data)

    def test_metadata_overrides_are_refused(self):
        for field in ("set_version", "title", "license", "set_uri"):
            with self.subTest(field=field):
                r = self.upload(**{field: "x"})
                self.assertEqual(r.status_code, 400)
                self.assertIn(field, r.data)
        self.assertFalse(ImportJob.objects.exists())

    def test_unknown_license_is_not_sent_to_the_dag(self):
        r = self.upload(sssom(license_iri="https://example.org/my-licence"))
        self.assertEqual(r.status_code, 202)
        self.assertIn("unknown_license", self.codes(r, "warning"))
        conf = self.worker.trigger_registry_import.call_args.args[0]
        self.assertEqual(conf["overrides"], {"status": Status.PUBLISHED})

    def test_invalid_file_is_rejected_with_its_issues(self):
        r = self.upload(sssom(rows=["broken"]))
        self.assertEqual(r.status_code, 400)
        self.assertIs(r.data["valid"], False)
        self.assertIn("row_length", self.codes(r))
        self.assertFalse(ImportJob.objects.exists())
        self.storage.upload_file.assert_not_called()

    def test_identity_conflicts_are_409(self):
        self.make_set(publisher=self.user)
        r = self.upload()
        self.assertEqual(r.status_code, 409)
        self.assertIn("set_version_exists", self.codes(r))
        self.assertFalse(ImportJob.objects.exists())

    def test_older_version_is_409(self):
        self.make_set(publisher=self.user, version="2.0.0")
        r = self.upload()
        self.assertEqual(r.status_code, 409)
        self.assertIn("set_version_not_newer", self.codes(r))

    def test_invalid_version_is_400(self):
        r = self.upload(sssom(version='"v1"'))
        self.assertEqual(r.status_code, 400)
        self.assertIn("invalid_set_version", self.codes(r))

    def test_another_users_set_is_409(self):
        self.make_set(publisher=self.other, version="0.9.0")
        r = self.upload()
        self.assertEqual(r.status_code, 409)
        self.assertIn("set_uri_not_owned", self.codes(r))

    def test_repeat_of_an_upload_in_progress_returns_the_same_job(self):
        first = self.upload()
        second = self.upload()
        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.data["import_job_id"], first.data["import_job_id"])
        self.assertEqual(ImportJob.objects.count(), 1)
        self.worker.trigger_registry_import.assert_called_once()

    def test_repeat_while_its_set_is_loaded_returns_the_same_job(self):
        first = self.upload()
        job = ImportJob.objects.get(pk=first.data["import_job_id"])
        job.status = ImportJobStatus.RUNNING
        job.save(update_fields=["status"])
        self.make_set(publisher=self.user, import_job=job)
        self.assertEqual(self.upload().data["import_job_id"], str(job.id))
        r = self.validate(sssom())
        self.assertTrue(r.data["valid"], r.data["issues"])
        self.assertIn("import_in_progress", self.codes(r, "warning"))

    def test_different_upload_of_a_version_in_progress_is_409(self):
        self.upload()
        changed = sssom(
            rows=["EX:9\tskos:exactMatch\tOMOP:2\tsemapv:ManualMappingCuration\t1"]
        )
        r = self.upload(changed)
        self.assertEqual(r.status_code, 409)
        self.assertIn("version_in_flight", self.codes(r))
        self.assertIn("version_in_flight", self.codes(self.validate(changed)))

    def test_same_file_with_another_status_is_409(self):
        self.upload()
        self.assertEqual(self.upload(status=Status.DRAFT).status_code, 409)

    def test_other_users_identical_upload_in_progress_is_409(self):
        self.upload()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.upload().status_code, 409)

    def test_upload_can_be_retried_after_a_failed_import(self):
        first = self.upload()
        ImportJob.objects.filter(pk=first.data["import_job_id"]).update(
            status=ImportJobStatus.FAILED
        )
        second = self.upload()
        self.assertEqual(second.status_code, 202)
        self.assertNotEqual(second.data["import_job_id"], first.data["import_job_id"])

    def test_idempotency_key_returns_the_original_job(self):
        headers = {"Idempotency-Key": "abc"}
        first = self.upload(headers=headers)
        ImportJob.objects.filter(pk=first.data["import_job_id"]).update(
            status=ImportJobStatus.SUCCEEDED
        )
        self.make_set(publisher=self.user)
        second = self.upload(headers=headers)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.data["import_job_id"], first.data["import_job_id"])

    def test_idempotency_key_cannot_be_reused_for_another_file(self):
        headers = {"Idempotency-Key": "abc"}
        self.upload(headers=headers)
        r = self.upload(sssom(version='"2.0.0"'), headers=headers)
        self.assertEqual(r.status_code, 409)
        self.assertIn("idempotency_key_reused", self.codes(r))

    def test_idempotency_key_belongs_to_one_user(self):
        headers = {"Idempotency-Key": "abc"}
        self.upload(headers=headers)
        self.client.force_authenticate(self.other)
        r = self.upload(sssom(set_uri="https://example.org/sets/b"), headers=headers)
        self.assertEqual(r.status_code, 202)

    def test_long_idempotency_key_is_refused(self):
        r = self.upload(headers={"Idempotency-Key": "a" * 256})
        self.assertEqual(r.status_code, 400)

    def test_storage_failure_fails_the_job(self):
        self.storage.upload_file.side_effect = ValueError("secret bucket detail")
        r = self.upload()
        self.assertEqual(r.status_code, 503)
        job = ImportJob.objects.get()
        self.assertEqual(job.status, ImportJobStatus.FAILED)
        self.assertNotIn("secret", job.error_message)
        self.assertIsNotNone(job.finished_at)
        self.worker.trigger_registry_import.assert_not_called()

    def test_trigger_failure_fails_the_job_and_allows_a_retry(self):
        self.worker.trigger_registry_import.side_effect = RuntimeError("down")
        self.assertEqual(self.upload().status_code, 503)
        self.assertEqual(ImportJob.objects.get().status, ImportJobStatus.FAILED)
        self.worker.trigger_registry_import.side_effect = None
        self.assertEqual(self.upload().status_code, 202)

    def test_job_can_be_polled_at_its_location(self):
        location = self.upload().headers["Location"]
        r = self.client.get(location)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["origin"], Origin.SSSOM_UPLOAD)
