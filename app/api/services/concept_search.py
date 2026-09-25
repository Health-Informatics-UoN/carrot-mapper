"""
Free-text search over the OMOP CDM vocabulary (Concept/ConceptSynonym):
query parsing, ranking, and pagination.

Recall (candidate matching, typo/fuzzy tolerant via Postgres pg_trgm) is
services/postgres_concept_search.py's job; this module re-ranks whatever it
recalls into explicit tiers. Ported from the pallas proof-of-concept
(health-informatics-uon/pallas), which found that reproducing this ranking
isn't something an off-the-shelf search engine does by construction (e.g.
Postgres tokenizes away punctuation on indexing, so it has no native notion
of "the literal substring '[hip]', brackets included" that the quoted-exact
tier needs) -- so ranking is computed explicitly in Python here, over
whatever the backend recalled:

  1. Full phrase match (a field equals the query, case-insensitive)
  2. Quoted exact substring match (only for "..." queries)
  3. Multi-word match, weighted by simple IDF computed over the candidates
  4. Prefix match (trailing `*` wildcard, e.g. "aspir*")
  5. Fuzzy/typo-tolerant catch-all -- whatever pg_trgm recalled that didn't
     qualify for tiers 1-4

Field priority within a tier: concept_code/concept_id tied highest (concept_id
is numeric and matched separately, not as a searchable text field), then
concept_name, then concept_synonyms, then vocabulary_id/domain_id/
concept_class_id (tied lowest).
"""

import re
from dataclasses import dataclass

from services import postgres_concept_search

_CANDIDATE_LIMIT = 500

FIELD_PRIORITY = {
    "concept_code": 0,
    "concept_name": 1,
    "concept_synonyms": 2,
    "vocabulary_id": 3,
    "domain_id": 3,
    "concept_class_id": 3,
}

# Always split the query on these separators.
_ALWAYS_SEPARATORS = re.compile(r"[/\\|?!,;.]")
# Stripped only from token edges (e.g. bracket-wrapped terms like "[hip]"),
# kept when embedded within a token (e.g. the hyphen in "COVID-19").
_STANDALONE_CHARS = "+-():^[]{}~*?|&"


@dataclass
class ParsedQuery:
    is_quoted: bool
    phrase: str  # literal text, verbatim if quoted; cleaned if not
    words: list[str]
    is_numeric: bool


def parse_query(raw_query: str) -> ParsedQuery:
    raw_query = raw_query.strip()

    if len(raw_query) >= 2 and raw_query.startswith('"') and raw_query.endswith('"'):
        phrase = raw_query[1:-1].strip()
        words = [w for w in phrase.split() if w]
        return ParsedQuery(is_quoted=True, phrase=phrase, words=words, is_numeric=False)

    cleaned = _ALWAYS_SEPARATORS.sub(" ", raw_query)
    words = []
    for token in cleaned.split():
        word = token.strip(_STANDALONE_CHARS)
        if word:
            words.append(word)
    phrase = " ".join(words)
    return ParsedQuery(
        is_quoted=False, phrase=phrase, words=words, is_numeric=phrase.isdigit()
    )


def _field_text(document: dict, field_name: str) -> str:
    value = document.get(field_name)
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


def _best_field(document: dict, predicate) -> str | None:
    """The highest-priority searchable field for which `predicate(text)` holds."""
    best = None
    for field_name in sorted(FIELD_PRIORITY, key=lambda name: FIELD_PRIORITY[name]):
        if predicate(_field_text(document, field_name)):
            if best is None or FIELD_PRIORITY[field_name] < FIELD_PRIORITY[best]:
                best = field_name
    return best


def _quoted_match_field(document: dict, phrase: str) -> str | None:
    needle = phrase.lower()
    return _best_field(document, lambda text: needle in text.lower())


def _full_phrase_match_field(document: dict, phrase: str) -> str | None:
    needle = phrase.lower()
    return _best_field(document, lambda text: text.strip().lower() == needle)


def _word_stats(document: dict, words: list[str]) -> tuple[int, str | None, int]:
    """(matched word count, best matching field, total word count of that field)."""
    best_field = None
    best_matched = -1
    best_total = 0
    for field_name in FIELD_PRIORITY:
        text = _field_text(document, field_name).lower()
        field_words = text.split()
        matched = sum(1 for w in words if w.lower() in field_words)
        if matched == 0:
            continue
        if (
            best_field is None
            or matched > best_matched
            or (
                matched == best_matched
                and FIELD_PRIORITY[field_name] < FIELD_PRIORITY[best_field]
            )
        ):
            best_field, best_matched, best_total = field_name, matched, len(field_words)
    return (best_matched if best_field else 0, best_field, best_total)


def _prefix_match_field(document: dict, prefixes: list[str]) -> str | None:
    prefixes_lower = [p.lower() for p in prefixes]

    def predicate(text: str) -> bool:
        field_words = text.lower().split()
        return all(any(w.startswith(p) for w in field_words) for p in prefixes_lower)

    return _best_field(document, predicate)


def _idf_weights(
    words: list[str], corpus_word_sets: list[set[str]]
) -> dict[str, float]:
    n_docs = max(len(corpus_word_sets), 1)
    weights = {}
    for word in set(w.lower() for w in words):
        containing = sum(1 for doc_words in corpus_word_sets if word in doc_words)
        weights[word] = (n_docs / (1 + containing)) if containing else n_docs
    return weights


def rank_candidates(documents: list[dict], parsed: ParsedQuery) -> list[dict]:
    """Sort `documents` (already typo-tolerant recall -- tier 5) into tier
    order. Quoted queries are a hard filter (must appear verbatim); unquoted
    queries keep every recalled document, since a hit that matches none of
    tiers 1-4 is, by construction, only there because of typo-tolerant
    matching -- tier 5."""
    if parsed.is_quoted:
        scored = []
        for doc in documents:
            field_name = _quoted_match_field(doc, parsed.phrase)
            if field_name is not None:
                scored.append((0, FIELD_PRIORITY[field_name], 0, 0, doc))
        scored.sort(key=lambda row: row[:4])
        return [doc for *_key, doc in scored]

    corpus_word_sets = [
        {word for f in FIELD_PRIORITY for word in _field_text(doc, f).lower().split()}
        for doc in documents
    ]
    idf = _idf_weights(parsed.words, corpus_word_sets)

    prefix_terms = [w[:-1] for w in parsed.words if w.endswith("*") and len(w) > 1]
    plain_words = [w for w in parsed.words if not w.endswith("*")]

    scored = []
    for doc in documents:
        phrase_field = (
            _full_phrase_match_field(doc, parsed.phrase) if parsed.phrase else None
        )
        if phrase_field is not None:
            scored.append((1, FIELD_PRIORITY[phrase_field], 0, 0, 0, doc))
            continue

        matched_count, word_field, field_total = (
            _word_stats(doc, plain_words) if plain_words else (0, None, 0)
        )
        if matched_count > 0:
            assert word_field is not None
            field_words = _field_text(doc, word_field).lower().split()
            idf_sum = sum(
                idf.get(w.lower(), 0) for w in plain_words if w.lower() in field_words
            )
            # Primary: more matched words wins (tier 3). Secondary: rarer
            # matched words win on ties (IDF). Tertiary: fewer total words in
            # the matching field wins, so a match diluted by extra unrelated
            # words doesn't outrank a denser match of the same words.
            scored.append(
                (
                    3,
                    FIELD_PRIORITY[word_field],
                    -matched_count,
                    -idf_sum,
                    field_total,
                    doc,
                )
            )
            continue

        if prefix_terms:
            prefix_field = _prefix_match_field(doc, prefix_terms)
            if prefix_field is not None:
                scored.append((4, FIELD_PRIORITY[prefix_field], 0, 0, 0, doc))
                continue

        # Recalled by pg_trgm (typo-tolerant) but none of tiers 1/3/4 apply: tier 5.
        scored.append((5, 99, 0, 0, 0, doc))

    scored.sort(key=lambda row: row[:5])
    return [doc for *_key, doc in scored]


def _document_to_result(document: dict) -> dict:
    return {
        "concept_id": document["concept_id"],
        "concept_code": document["concept_code"],
        "concept_name": document["concept_name"],
        "domain_id": document["domain_id"],
        "vocabulary_id": document["vocabulary_id"],
        "concept_class_id": document["concept_class_id"],
        "standard_concept": document.get("standard_concept"),
    }


def search_concepts(
    query: str, filters: dict[str, list[str]], page: int = 0, size: int = 20
) -> dict:
    """Search Concept/ConceptSynonym, ranked and paginated.

    `page` is 0-indexed. `filters` maps facet param name (vocabulary_id,
    domain_id, concept_class_id, standard_concept) to selected values.
    """
    parsed = parse_query(query) if query else ParsedQuery(False, "", [], False)

    candidate_ids = (
        postgres_concept_search.match_candidate_ids(parsed.phrase, parsed.words)
        if parsed.words
        else None
    )
    concept_ids, facets = postgres_concept_search.recall_and_facets(
        candidate_ids, parsed.phrase, filters, _CANDIDATE_LIMIT
    )
    hits = postgres_concept_search.hydrate_documents(concept_ids)

    if parsed.is_numeric:
        by_id = postgres_concept_search.get_by_concept_id(int(parsed.phrase), filters)
        if by_id and not any(h["concept_id"] == by_id["concept_id"] for h in hits):
            hits.append(by_id)

    if query:
        hits = rank_candidates(hits, parsed)
    else:
        hits = sorted(hits, key=lambda h: h.get("concept_name") or "")

    total = len(hits)
    page_hits = hits[page * size : page * size + size]

    return {
        "results": [_document_to_result(h) for h in page_hits],
        "facets": facets,
        "total": total,
    }
