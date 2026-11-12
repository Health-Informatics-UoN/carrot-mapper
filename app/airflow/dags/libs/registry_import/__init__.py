"""
Import SSSOM files into the Carrot Mappings Registry (the registry_import DAG).

- parse.py:    split an SSSOM/TSV file into its metadata block and rows.
- validate.py: check every row against the SSSOM spec and the registry's
               vocabularies, and normalise it into an ImportPlan.
- load.py:     write an ImportPlan to the registry tables in one transaction.
- queries.py:  the SQL used by load.py and core.py.
- core.py:     the Airflow task callables.

parse/validate/load have no Airflow imports, so they can be unit tested alone.
"""
