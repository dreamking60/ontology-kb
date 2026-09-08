"""Spec coverage: specs/concept-search/spec.md."""
from __future__ import annotations

from banking_kb.kb import KnowledgeBase
from banking_kb.search import search


def _deposit_result(kb: KnowledgeBase) -> dict:
    return next(r for r in search(kb, "存款") if r["label_zh"] == "存款")


def test_match_on_chinese_label(kb):
    results = search(kb, "存款")
    assert results and results[0]["label_zh"] == "存款"


def test_match_on_chinese_synonym(kb):
    results = search(kb, "定存")
    assert results and results[0]["label_zh"] == "定期存款"


def test_match_on_english_label(kb):
    results = search(kb, "deposit")
    assert results and results[0]["label_zh"] == "存款"


def test_no_matching_concept_returns_empty(kb):
    results = search(kb, "完全不存在的术语zzz")
    assert results == []


def test_result_shows_hierarchy_context(kb):
    deposit = _deposit_result(kb)
    assert deposit["superclass"] is not None
    assert deposit["superclass"]["label"] == "产品"
    subclass_labels = [s["label"] for s in deposit["subclasses"]]
    assert "活期存款" in subclass_labels and "定期存款" in subclass_labels


def test_result_payload_carries_full_detail(kb):
    deposit = _deposit_result(kb)
    for key in (
        "id",
        "labels",
        "synonyms",
        "definition",
        "superclass",
        "subclasses",
        "attributes",
    ):
        assert key in deposit, f"missing payload field: {key}"
    assert deposit["labels"]["zh"] == "存款"
    assert deposit["labels"]["en"] == "Deposit"
    assert deposit["definition"]
