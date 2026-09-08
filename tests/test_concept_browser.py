"""Spec coverage: specs/concept-browser/spec.md."""
from __future__ import annotations

from banking_kb.kb import BC, KnowledgeBase


def _find_node(nodes: list[dict], label_zh: str) -> dict | None:
    for node in nodes:
        if node["label_zh"] == label_zh:
            return node
        found = _find_node(node["children"], label_zh)
        if found:
            return found
    return None


def test_browse_from_top_level_categories(kb):
    roots = kb.tree()
    assert [r["label_zh"] for r in roots] == ["产品", "账户", "主体"]


def test_tree_reaches_leaf_product_types(kb):
    deposit = _find_node(kb.tree(), "存款")
    assert deposit is not None
    cod = _find_node([deposit], "大额存单")
    assert cod is not None
    # hierarchy path: 产品 → 存款 → 定期存款 → 大额存单
    time_deposit = _find_node([deposit], "定期存款")
    assert any(c["label_zh"] == "大额存单" for c in time_deposit["children"])


def test_concept_detail_view(kb):
    detail = kb.concept_detail(BC.CertificateOfDeposit)
    assert detail is not None
    assert detail["labels"]["zh"] == "大额存单"
    assert detail["labels"]["en"] == "Certificate of Deposit"
    assert "CD" in detail["synonyms"]
    assert detail["definition"]
    assert detail["superclass"]["label"] == "定期存款"
    assert detail["kind"] == "class"


def test_related_concepts_and_attributes_visible(kb):
    detail = kb.concept_detail(kb.resolve("DemoHousingLoan"))
    assert detail is not None
    prop_labels = {a["property_label"] for a in detail["attributes"]}
    assert "期限（月）" in prop_labels and "风险等级" in prop_labels
    offered = [r for r in detail["relationships"] if r["property_label"] == "提供机构"]
    assert offered and offered[0]["value_label"] == "示例商业银行"
