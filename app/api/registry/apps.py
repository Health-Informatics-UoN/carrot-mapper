from django.apps import AppConfig
from django.db.backends.signals import connection_created


def set_trigram_threshold(sender, connection, **kwargs):
    """
    Set pg_trgm's word-similarity cut-off for the ``%>`` operator used by
    registry fuzzy search (registry/search.py), so the GIN trigram indexes
    can be used with a threshold looser than the 0.6 default.
    """
    if connection.vendor != "postgresql":
        return
    from django.conf import settings

    threshold = getattr(settings, "REGISTRY_TRIGRAM_THRESHOLD", 0.3)
    with connection.cursor() as cursor:
        # Custom (dotted) settings are accepted before the extension is
        # loaded, so this is safe on a fresh database too.
        cursor.execute(
            "SELECT set_config('pg_trgm.word_similarity_threshold', %s, false)",
            [str(threshold)],
        )


class RegistryConfig(AppConfig):
    name = "registry"
    label = "registry"
    verbose_name = "Carrot Mappings Registry"

    def ready(self):
        connection_created.connect(
            set_trigram_threshold, dispatch_uid="registry_trigram_threshold"
        )
