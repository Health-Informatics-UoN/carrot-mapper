"""SQL for the registry_import DAG. Table names are Django's defaults for app "registry"."""

# --- ImportJob ---------------------------------------------------------------

get_import_job_query = """
    SELECT id::text, status, origin_id, file_key, submitted_by_id
    FROM registry_importjob
    WHERE id = %(import_job_id)s
"""

mark_import_job_running_query = """
    UPDATE registry_importjob
    SET status = 'RUNNING',
        started_at = COALESCE(started_at, NOW()),
        finished_at = NULL,
        error_message = '',
        dag_run_id = CASE WHEN dag_run_id = '' THEN %(dag_run_id)s ELSE dag_run_id END
    WHERE id = %(import_job_id)s
"""

set_import_job_file_key_query = """
    UPDATE registry_importjob SET file_key = %(file_key)s WHERE id = %(import_job_id)s
"""

set_import_job_issues_query = """
    UPDATE registry_importjob
    SET validation_issues = %(issues)s::jsonb
    WHERE id = %(import_job_id)s
"""

# Only the first failure is recorded (a task's callback, then the DAG's, both
# fire), and a job that already succeeded is never marked failed. RETURNING
# tells the caller whether this call did the update, so it notifies once.
mark_import_job_failed_query = """
    UPDATE registry_importjob
    SET status = 'FAILED',
        error_message = %(error_message)s,
        finished_at = NOW()
    WHERE id = %(import_job_id)s AND status NOT IN ('FAILED', 'SUCCEEDED')
    RETURNING id
"""

mark_import_job_succeeded_query = """
    UPDATE registry_importjob
    SET status = 'SUCCEEDED',
        error_message = '',
        finished_at = NOW()
    WHERE id = %(import_job_id)s
"""

# --- Vocabularies --------------------------------------------------------------

get_predicates_query = "SELECT predicate_id FROM registry_predicate"
get_justifications_query = "SELECT justification_id FROM registry_mappingjustification"
get_licenses_query = """
    SELECT id, license_iri, see_also, is_deprecated FROM registry_license
"""

get_scan_report_name_query = (
    "SELECT dataset FROM mapping_scanreport WHERE id = %(scan_report_id)s"
)

# Another import already holds this set_uri + set_version (sets are immutable;
# corrections are a new set_version).
get_conflicting_set_query = """
    SELECT id::text FROM registry_mappingset
    WHERE set_uri = %(set_uri)s
        AND set_version = %(set_version)s
        AND import_job_id IS DISTINCT FROM %(import_job_id)s
"""

# --- Load (one transaction) ----------------------------------------------------

# Undo an earlier attempt of this job that committed its load, so retries are
# idempotent. Mapping.mapping_set's CASCADE is Django-side only, so mappings are
# deleted first. Terms are shared between sets and are kept.
delete_job_mappings_query = """
    DELETE FROM registry_mapping
    WHERE mapping_set_id IN (
        SELECT id FROM registry_mappingset WHERE import_job_id = %(import_job_id)s
    )
"""
delete_job_mapping_sets_query = """
    DELETE FROM registry_mappingset WHERE import_job_id = %(import_job_id)s
"""

insert_mapping_set_query = """
    INSERT INTO registry_mappingset (
        id, set_uri, set_version, title, description, license_id, origin_id,
        status_id, import_job_id, source_scan_report_id, sssom_version,
        creator_ids, publication_date, subject_source, subject_source_version,
        object_source, object_source_version, curie_map, extra_metadata,
        file_key, created_at, published_at
    ) VALUES (
        %(id)s, %(set_uri)s, %(set_version)s, %(title)s, %(description)s,
        %(license_id)s, %(origin_id)s, 'DRAFT', %(import_job_id)s,
        %(source_scan_report_id)s, %(sssom_version)s, %(creator_ids)s::jsonb,
        %(publication_date)s, %(subject_source)s, %(subject_source_version)s,
        %(object_source)s, %(object_source_version)s, %(curie_map)s::jsonb,
        %(extra_metadata)s::jsonb, %(file_key)s, NOW(), NULL
    )
"""

# Dropped at the end of the load transaction.
create_staging_table_query = """
    CREATE TEMP TABLE registry_import_staging (
        row_no INTEGER NOT NULL,
        subject_iri TEXT NOT NULL,
        subject_label TEXT NOT NULL,
        subject_type TEXT NOT NULL,
        subject_category TEXT NOT NULL,
        subject_prefix TEXT NOT NULL,
        subject_ext_level TEXT NOT NULL,
        subject_ext_field TEXT NOT NULL,
        subject_ext_value TEXT NOT NULL,
        predicate_id TEXT NOT NULL,
        predicate_modifier TEXT NOT NULL,
        object_iri TEXT NOT NULL,
        object_label TEXT NOT NULL,
        object_type TEXT NOT NULL,
        object_category TEXT NOT NULL,
        object_prefix TEXT NOT NULL,
        object_source_version TEXT NOT NULL,
        mapping_justification TEXT NOT NULL,
        mapping_cardinality TEXT NOT NULL,
        confidence DOUBLE PRECISION,
        author_ids JSONB NOT NULL,
        reviewer_ids JSONB NOT NULL,
        mapping_date DATE,
        comment TEXT NOT NULL,
        other TEXT,
        extra_metadata JSONB NOT NULL
    ) ON COMMIT DROP
"""

copy_staging_query = "COPY registry_import_staging ({columns}) FROM STDIN"

# New terms only; an existing term (same canonical_iri and kind) is reused as is.
# DISTINCT ON keeps the first row's label etc. for a term repeated in the file.
# Ordered by IRI so concurrent imports take row locks in the same order.
insert_subject_terms_query = """
    INSERT INTO registry_term (
        canonical_iri, label, type, category, prefix, kind,
        object_source_version, ext_term_level, ext_source_field, ext_source_value
    )
    SELECT DISTINCT ON (subject_iri)
        subject_iri, subject_label, subject_type, subject_category,
        subject_prefix, 'SUBJECT', '', subject_ext_level, subject_ext_field,
        subject_ext_value
    FROM registry_import_staging
    ORDER BY subject_iri, row_no
    ON CONFLICT (canonical_iri, kind) DO NOTHING
"""

insert_object_terms_query = """
    INSERT INTO registry_term (
        canonical_iri, label, type, category, prefix, kind,
        object_source_version, ext_term_level, ext_source_field, ext_source_value
    )
    SELECT DISTINCT ON (object_iri)
        object_iri, object_label, object_type, object_category, object_prefix,
        'OBJECT', object_source_version, '', '', ''
    FROM registry_import_staging
    ORDER BY object_iri, row_no
    ON CONFLICT (canonical_iri, kind) DO NOTHING
"""

insert_mappings_query = """
    INSERT INTO registry_mapping (
        mapping_set_id, subject_id, predicate_id, predicate_modifier, object_id,
        mapping_justification_id, mapping_cardinality, confidence, author_ids,
        reviewer_ids, mapping_date, comment, extra_metadata, other
    )
    SELECT
        %(mapping_set_id)s, subject_term.id, staging.predicate_id,
        staging.predicate_modifier, object_term.id, staging.mapping_justification,
        staging.mapping_cardinality, staging.confidence, staging.author_ids,
        staging.reviewer_ids, staging.mapping_date, staging.comment,
        staging.extra_metadata, staging.other
    FROM registry_import_staging AS staging
    JOIN registry_term AS subject_term
        ON subject_term.canonical_iri = staging.subject_iri
        AND subject_term.kind = 'SUBJECT'
    JOIN registry_term AS object_term
        ON object_term.canonical_iri = staging.object_iri
        AND object_term.kind = 'OBJECT'
    ORDER BY staging.row_no
"""

set_import_job_stats_query = """
    UPDATE registry_importjob SET stats = %(stats)s::jsonb WHERE id = %(import_job_id)s
"""

# --- Finalize -------------------------------------------------------------------

publish_mapping_set_query = """
    UPDATE registry_mappingset
    SET status_id = %(status)s,
        published_at = CASE WHEN %(status)s = 'PUBLISHED' THEN NOW() ELSE NULL END
    WHERE import_job_id = %(import_job_id)s
    RETURNING id::text, title
"""
