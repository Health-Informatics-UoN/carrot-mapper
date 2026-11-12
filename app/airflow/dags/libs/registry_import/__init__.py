"""
Import SSSOM files into the Carrot Mappings Registry (the registry_import DAG).

One file per DAG step, in order:

- validate_params.py: check the run conf; job RUNNING.
- prepare_source.py:  make sure the SSSOM file is in storage (a Mapper direct
                      publish builds it).
- full_validate.py:   validate every row; store the issues on the job.
- load.py:            write the set, terms and mappings in one transaction.
- finalize.py:        publish the set; job SUCCEEDED.
- on_failure.py:      the failure callback; job FAILED.

Helpers:

- helpers.py:                  small helpers and constants all steps share.
- queries.py:                  the SQL.
- full_validate_parse.py:      split an SSSOM/TSV file into metadata and rows.
- full_validate_checks.py:     the checks, and normalising rows for load.
- full_validate_licenses.py:   find the registry_license row a license IRI names.

full_validate_parse/checks/licenses and load.load_plan take no Airflow
connections, so they can be unit tested alone.
"""
