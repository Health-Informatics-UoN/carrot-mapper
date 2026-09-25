from django.core.management.base import BaseCommand
from django.db import connection

# CREATE INDEX CONCURRENTLY can't run inside a transaction, and the `omop`
# schema tables aren't Django-migration-managed (they're bulk-loaded by the
# separate omop-lite service), so this is a manual, idempotent command
# rather than a migration -- run once after omop-lite has loaded the vocab
# data.
_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS pg_trgm;",
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_concept_name_trgm "
    'ON "omop"."concept" USING GIN (concept_name gin_trgm_ops);',
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_concept_code_trgm "
    'ON "omop"."concept" USING GIN (concept_code gin_trgm_ops);',
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_concept_synonym_name_trgm "
    'ON "omop"."concept_synonym" USING GIN (concept_synonym_name gin_trgm_ops);',
]


class Command(BaseCommand):
    help = (
        "Enable pg_trgm and create the GIN trigram indexes concept search "
        "relies on for performance. Safe to re-run; run once after omop-lite "
        "has loaded the vocabulary data."
    )

    def handle(self, *args, **kwargs):
        # CONCURRENTLY requires autocommit -- can't be wrapped in a transaction.
        with connection.cursor() as cursor:
            connection.set_autocommit(True)
            for statement in _STATEMENTS:
                self.stdout.write(f"Running: {statement}")
                cursor.execute(statement)

        self.stdout.write(
            self.style.SUCCESS("Concept search trigram indexes are ready.")
        )
