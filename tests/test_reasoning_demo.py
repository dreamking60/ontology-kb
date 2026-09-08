"""Spec coverage: specs/reasoning-demo/spec.md."""
from __future__ import annotations

from banking_kb import reasoning
from banking_kb.kb import KnowledgeBase

ALL_TAGS = {reasoning.PROVENANCE_ASSERTED, reasoning.PROVENANCE_INFERRED, reasoning.PROVENANCE_RULE}


def _demo(kb: KnowledgeBase) -> dict:
    return reasoning.run_reasoning_demo(kb)


def test_inferred_supertype_is_reported(kb):
    result = _demo(kb)
    inferred = {(f["subject_label"], f["object_label"]) for f in result["inferred_type_facts"]}
    # 示例十年期定期存款 asserted only as 定期存款; 存款 must be inferred.
    assert ("示例十年期定期存款", "存款") in inferred
    # Chain through two levels still works for certificates of deposit.
    assert ("示例大额存单", "定期存款") in inferred
    assert ("示例大额存单", "存款") in inferred


def test_only_consistent_derivations_are_shown(kb):
    result = _demo(kb)
    assert result["consistency"]["status"] == "no_inconsistency_detected"


def test_rule_derived_facts_reported_with_rule_text(kb):
    result = _demo(kb)
    long_term = [
        f for f in result["rule_derived_facts"] if f["subject_label"] == "示例十年期定期存款"
    ]
    assert long_term, "demo rule did not fire on the 120-month deposit"
    fact = long_term[0]
    assert fact["object_label"] == "长期定期存款（演示分类）"
    assert fact["rule"]["id"] == "long-term-deposit-rule"
    assert fact["rule"]["text"]
    # Short-term deposit (12 months) must NOT be rule-derived.
    assert all(f["subject_label"] != "示例一年期定期存款" for f in result["rule_derived_facts"])


def test_provenance_labels_on_all_facts(kb):
    result = _demo(kb)
    all_facts = (
        result["asserted_type_facts"] + result["inferred_type_facts"] + result["rule_derived_facts"]
    )
    assert all_facts
    for fact in all_facts:
        assert fact["provenance"] in ALL_TAGS, fact


def test_store_unchanged_after_reasoning(kb):
    before = kb.triple_count()
    result = _demo(kb)
    after = kb.triple_count()
    assert before == after == result["store_unchanged"]["triples_before"]
    assert result["store_unchanged"]["unchanged"] is True
