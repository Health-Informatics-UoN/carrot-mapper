"""
Fuzzy search for the registry, backed by Postgres ``pg_trgm``.

Matches are tiered and ranked in this order:

    0. exact CURIE / IRI / set_uri match (case-insensitive)
    1. prefix match (``istartswith``) on the label / title or identifier
    2. trigram word-similarity match (typos, partial words)

The trigram tier uses the ``%>`` operator so the GIN ``gin_trgm_ops``
indexes are used. Its cut-off is the session setting
``pg_trgm.word_similarity_threshold``, set on every new connection from
``settings.REGISTRY_TRIGRAM_THRESHOLD`` (see ``RegistryConfig.ready``).
"""

from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import Case, F, FloatField, IntegerField, Q, QuerySet, Value, When
from django.db.models.functions import Greatest

from registry.models import MappingSet, Term

RANK_EXACT = 0
RANK_PREFIX = 1
RANK_FUZZY = 2


def _clean(q: str | None) -> str:
    return (q or "").strip()


def search_terms(qs: QuerySet[Term], q: str | None) -> QuerySet[Term]:
    """
    Filter ``qs`` to terms matching ``q`` and annotate ``match_rank`` and
    ``similarity``. Does not order; call ``order_by_relevance`` for that.
    """
    q = _clean(q)
    if not q:
        return qs

    exact = Q(canonical_iri__iexact=q)
    prefix = Q(label__istartswith=q) | Q(canonical_iri__istartswith=q)
    fuzzy = Q(label__trigram_word_similar=q) | Q(canonical_iri__trigram_word_similar=q)

    return qs.filter(exact | prefix | fuzzy).annotate(
        match_rank=Case(
            When(exact, then=Value(RANK_EXACT)),
            When(prefix, then=Value(RANK_PREFIX)),
            default=Value(RANK_FUZZY),
            output_field=IntegerField(),
        ),
        similarity=Greatest(
            TrigramWordSimilarity(q, "label"),
            TrigramWordSimilarity(q, "canonical_iri"),
            output_field=FloatField(),
        ),
    )


def search_mapping_sets(
    qs: QuerySet[MappingSet], q: str | None
) -> QuerySet[MappingSet]:
    """
    Filter ``qs`` to sets whose set_uri, title or description match ``q``,
    annotating ``match_rank`` and ``similarity``.
    """
    q = _clean(q)
    if not q:
        return qs

    exact = Q(series__set_uri__iexact=q)
    prefix = Q(title__istartswith=q)
    fuzzy = Q(title__trigram_word_similar=q) | Q(description__trigram_word_similar=q)

    return qs.filter(exact | prefix | fuzzy).annotate(
        match_rank=Case(
            When(exact, then=Value(RANK_EXACT)),
            When(prefix, then=Value(RANK_PREFIX)),
            default=Value(RANK_FUZZY),
            output_field=IntegerField(),
        ),
        similarity=Greatest(
            TrigramWordSimilarity(q, "title"),
            TrigramWordSimilarity(q, "description"),
            output_field=FloatField(),
        ),
    )


def order_by_relevance(qs: QuerySet, *tiebreak: str) -> QuerySet:
    """Order a ``search_*`` result: best tier first, then most similar."""
    return qs.order_by("match_rank", F("similarity").desc(nulls_last=True), *tiebreak)
