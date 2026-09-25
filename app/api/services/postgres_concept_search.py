"""
Postgres pg_trgm-backed recall for concept search: trigram similarity plus
substring matching against Concept.concept_name/concept_code and
ConceptSynonym.concept_synonym_name.

Ported from the pallas proof-of-concept (health-informatics-uon/pallas),
adapted to query carrot's existing `data.models.Concept`/`ConceptSynonym`
directly rather than a separate model set, and relies on the
`setup_search_indexes` management command having created the GIN trigram
indexes this needs for performance at scale.

Recall happens in two steps rather than one annotated/filtered query: first
find the matching concept_ids, then hydrate full documents (synonyms
included via a second query keyed by concept_id) for just those ids.
`ConceptSynonym.concept_id` is a plain integer column, not a Django
ForeignKey, so there's no ORM relation to aggregate synonyms through in a
single query anyway.

Matching concept_name/concept_code and matching via a concept_synonym are
also deliberately queried separately (`_match_candidate_ids`) rather than
combined into one `concept_name % ... OR concept_id IN (subquery on
concept_synonym)` condition: against the real ~10M-row omop.concept table,
EXPLAIN showed Postgres refusing to use either GIN trigram index for that
combined condition, falling back to a full parallel sequential scan (47s+
per query). Two separate, independently GIN-index-assisted lookups, merged
in Python, avoids that plan entirely.

Substring matching also registers and uses a native ILIKE lookup
(`__trgm_icontains`) instead of Django's built-in `icontains`: on
PostgreSQL, `icontains` compiles to `UPPER(field) LIKE UPPER(pattern)`,
which pg_trgm's GIN index does not recognise as an indexable LIKE
expression (only the native `ILIKE`/`~~*` operator is) -- confirmed via
EXPLAIN, where `icontains` silently fell back to a full sequential scan
(5s+) while `ILIKE` used the index as expected.

Known limitation: a short query word with common trigrams (e.g. a 6-letter
typo like "asprin") can still take several seconds even with the index,
because GIN's own candidate generation for `%` is trigram-count-based, not
pruned by `pg_trgm.similarity_threshold` until the recheck step -- so a
short/common word's posting-list intersection can be large regardless of
threshold. Bounded by DB_STATEMENT_TIMEOUT (20s default) rather than
unbounded, and doesn't affect normal-length word queries (1-4s against the
real ~10M-row vocab). Worth revisiting (e.g. a minimum-length gate before
falling back to pure trigram similarity) if it proves disruptive in
practice.
"""

import re
from collections import Counter

from data.models import Concept, ConceptSynonym
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import CharField, Q, QuerySet
from django.db.models.functions import Greatest
from django.db.models.lookups import Lookup

FACET_PARAMS = ("vocabulary_id", "domain_id", "concept_class_id", "standard_concept")

# Generous upper bound on how many raw (pre-facet-filter) text matches to
# pull back per source (name/code, synonym) before intersecting with facet
# filters and ranking. Large enough that a common search term still recalls
# a representative candidate pool, small enough that the resulting
# `concept_id__in=...` list stays cheap.
_MATCH_CANDIDATE_CAP = 2000


@CharField.register_lookup
class _TrigramIContains(Lookup):
    """Native `field ILIKE %value%`, pg_trgm-GIN-indexable unlike
    Django's built-in `icontains` (see module docstring)."""

    lookup_name = "trgm_icontains"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f"{lhs} ILIKE {rhs}", lhs_params + rhs_params


_LIKE_SPECIAL_CHARS = re.compile(r"([\\%_])")


def _as_like_pattern(word: str) -> str:
    """Escape LIKE metacharacters in `word`, then wrap it for a substring
    match -- replicates what Django's `icontains` does to its value."""
    escaped = _LIKE_SPECIAL_CHARS.sub(r"\\\1", word)
    return f"%{escaped}%"


def _apply_filters(queryset: QuerySet, filters: dict[str, list[str]]) -> QuerySet:
    for param in FACET_PARAMS:
        values = filters.get(param)
        if values:
            queryset = queryset.filter(**{f"{param}__in": values})
    return queryset


def _word_or_trigram_q(field: str, words: list[str], full_text: str) -> Q:
    """Cast a wide-enough recall net for concept_search.py's tiers to
    classify precisely: substring match on each individual word (tiers 1/3/4
    need candidates containing query words at all) OR'd with trigram
    similarity against the whole phrase (tier 5 -- typos)."""
    q = Q(**{f"{field}__trigram_similar": full_text})
    for word in words:
        q |= Q(**{f"{field}__trgm_icontains": _as_like_pattern(word)})
    return q


def match_candidate_ids(query_text: str, words: list[str]) -> set[int]:
    """Concept ids matching `query_text` by name, code, or synonym
    (typo-tolerant via pg_trgm), unfiltered by facets -- each source queried
    independently so both GIN indexes stay usable (see module docstring).

    Expensive (two GIN-assisted scans), so callers compute this once per
    request and reuse the result for both recall and facet counting rather
    than each recomputing it."""
    name_or_code = _word_or_trigram_q(
        "concept_name", words, query_text
    ) | _word_or_trigram_q("concept_code", words, query_text)
    direct_ids = set(
        Concept.objects.filter(name_or_code).values_list("concept_id", flat=True)[
            :_MATCH_CANDIDATE_CAP
        ]
    )
    synonym_ids = set(
        ConceptSynonym.objects.filter(
            _word_or_trigram_q("concept_synonym_name", words, query_text)
        ).values_list("concept_id", flat=True)[:_MATCH_CANDIDATE_CAP]
    )
    return direct_ids | synonym_ids


def recall_and_facets(
    candidate_ids: set[int] | None,
    query_text: str,
    filters: dict[str, list[str]],
    limit: int,
) -> tuple[list[int], dict[str, dict[str, int]]]:
    """Ranked concept_ids (capped at `limit`) plus facet counts across the
    *whole* (uncapped) candidate set, in one query rather than one for
    recall plus one GROUP BY per facet -- each of those would otherwise
    re-filter the same potentially-thousands-strong
    `concept_id__in=candidate_ids` list from scratch. `candidate_ids` is
    `match_candidate_ids(...)`'s result, or None for a query-less browse
    (facet filters only, ordered by name; facets counted across all
    concepts matching the current filters)."""
    queryset = _apply_filters(Concept.objects.all(), filters)

    if candidate_ids is None:
        order_by = "concept_name"
    else:
        if not candidate_ids:
            return [], {param: {} for param in FACET_PARAMS}
        queryset = queryset.filter(concept_id__in=candidate_ids).annotate(
            _similarity=Greatest(
                TrigramSimilarity("concept_name", query_text),
                TrigramSimilarity("concept_code", query_text),
            )
        )
        order_by = "-_similarity"

    rows = list(queryset.order_by(order_by).values("concept_id", *FACET_PARAMS))
    ranked_ids = [row["concept_id"] for row in rows[:limit]]

    facet_counters = {param: Counter() for param in FACET_PARAMS}
    for row in rows:
        for param in FACET_PARAMS:
            value = row[param]
            if value:
                facet_counters[param][value] += 1
    facets = {param: dict(counter) for param, counter in facet_counters.items()}

    return ranked_ids, facets


def get_by_concept_id(concept_id: int, filters: dict[str, list[str]]) -> dict | None:
    queryset = _apply_filters(Concept.objects.filter(concept_id=concept_id), filters)
    concept_ids = list(queryset.values_list("concept_id", flat=True))
    documents = hydrate_documents(concept_ids)
    return documents[0] if documents else None


def hydrate_documents(concept_ids: list[int]) -> list[dict]:
    if not concept_ids:
        return []

    rows = Concept.objects.filter(concept_id__in=concept_ids).values(
        "concept_id",
        "concept_code",
        "concept_name",
        "domain_id",
        "vocabulary_id",
        "concept_class_id",
        "standard_concept",
        "invalid_reason",
    )
    by_id = {row["concept_id"]: row for row in rows}

    synonyms_by_id: dict[int, list[str]] = {}
    synonym_rows = ConceptSynonym.objects.filter(concept_id__in=concept_ids).values(
        "concept_id", "concept_synonym_name"
    )
    for row in synonym_rows:
        synonyms_by_id.setdefault(row["concept_id"], []).append(
            row["concept_synonym_name"]
        )

    documents = []
    for concept_id in concept_ids:
        row = by_id.get(concept_id)
        if row is None:
            continue
        documents.append(
            {
                "concept_id": row["concept_id"],
                "concept_code": row["concept_code"],
                "concept_name": row["concept_name"],
                "concept_synonyms": synonyms_by_id.get(concept_id, []),
                "domain_id": row["domain_id"],
                "vocabulary_id": row["vocabulary_id"],
                "concept_class_id": row["concept_class_id"],
                "standard_concept": row["standard_concept"],
                "invalid_reason": row["invalid_reason"],
            }
        )
    return documents
