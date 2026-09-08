"""Semantic search over the knowledge base (specs/concept-search).

Matching is label/synonym based with hierarchy expansion: every result carries
its direct superclass and direct subclasses so the user sees context.
"""
from __future__ import annotations

from rdflib import URIRef

from .kb import KnowledgeBase, normalize

MAX_RESULTS = 20


def _score(uri: URIRef, kb: KnowledgeBase, q: str) -> int:
    """Return the best match score for *q* against *uri*'s labels/synonyms."""
    labels = kb.labels(uri)
    zh, en = normalize(labels["zh"]), normalize(labels["en"])
    scores: list[int] = []
    if zh and zh == q:
        scores.append(100)  # exact Chinese label
    if en and en == q:
        scores.append(88)  # exact English label
    for syn in kb.synonyms(uri):
        nsyn = normalize(syn)
        if nsyn == q:
            scores.append(92)  # exact synonym
    if zh and q and zh.startswith(q):
        scores.append(84)  # Chinese-label prefix
    if en and q and en.startswith(q):
        scores.append(76)  # English-label prefix
    for syn in kb.synonyms(uri):
        nsyn = normalize(syn)
        if q and nsyn.startswith(q):
            scores.append(80)  # synonym prefix (e.g. 按揭 for 按揭贷款)
    if zh and q and q in zh:
        scores.append(70)  # Chinese-label substring
    if en and q and q in en:
        scores.append(62)  # English-label substring
    for syn in kb.synonyms(uri):
        nsyn = normalize(syn)
        if q and q in nsyn:
            scores.append(66)  # synonym substring
    return max(scores) if scores else 0


def search(kb: KnowledgeBase, query: str) -> list[dict]:
    """Return ranked concept results for *query* (empty query -> empty list)."""
    q = normalize(query)
    if not q:
        return []
    scored: list[tuple[int, dict]] = []
    for uri in kb.candidate_concepts():
        score = _score(uri, kb, q)
        if score <= 0:
            continue
        detail = kb.concept_detail(uri)
        if detail is None:
            continue
        detail["score"] = score
        scored.append((score, detail))
    scored.sort(key=lambda pair: (-pair[0], pair[1].get("label_zh") or ""))
    return [detail for _, detail in scored[:MAX_RESULTS]]
