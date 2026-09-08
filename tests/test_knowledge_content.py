"""Spec coverage: specs/knowledge-content/spec.md."""
from __future__ import annotations

from rdflib import URIRef
from rdflib.namespace import RDFS, SKOS

from banking_kb import reasoning
from banking_kb.kb import BC, KnowledgeBase
from banking_kb.search import search

# The five coverage categories from specs/knowledge-content/spec.md.
CATEGORY_ROOTS = {
    "deposit": BC.Deposit,
    "loan": BC.Loan,
    "wealth_management": BC.WealthManagementProduct,
    "account": BC.Account,
    "party": BC.Party,
}

# Builtin vocabularies allowed as un-declared reference targets.
_BUILTIN_NAMESPACES = (
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/2004/02/skos/core#",
    "http://www.w3.org/2001/XMLSchema#",
)


def _classes(kb: KnowledgeBase):
    return [c for c in kb.candidate_concepts() if kb.is_class(c)]


def _curated_entries(kb: KnowledgeBase):
    """Classes and individuals that carry both labels and a definition."""
    out = []
    for c in kb.candidate_concepts():
        labels = kb.labels(c)
        if labels["zh"] and labels["en"] and kb.definition(c):
            out.append(c)
    return out


def test_ontology_loads_without_errors(kb):
    assert kb.triple_count() > 0


def test_reasoner_reports_no_inconsistency(kb):
    result = reasoning.run_reasoning_demo(kb)
    assert result["consistency"]["status"] == "no_inconsistency_detected"
    assert "fail" not in result["consistency"]["status"]


def test_referential_integrity(kb):
    g = kb.graph
    declared = set(g.subjects())
    for pred in (RDFS.subClassOf, RDFS.domain, RDFS.range):
        for s, o in g.subject_objects(pred):
            assert isinstance(s, URIRef)
            if isinstance(o, URIRef) and not str(o).startswith(_BUILTIN_NAMESPACES):
                assert o in declared, f"{pred} target {o} is undeclared"


def test_no_class_missing_bilingual_label(kb):
    missing = []
    for cls in _classes(kb):
        labels = kb.labels(cls)
        if not labels["zh"] or not labels["en"]:
            missing.append(str(cls))
    assert missing == [], f"classes missing zh/en labels: {missing}"


def test_synonyms_are_queryable(kb):
    results = search(kb, "定存")
    assert any(r["label_zh"] == "定期存款" for r in results)


def test_aligned_classes_are_annotated(kb):
    aligned = list(kb.graph.objects(BC.Deposit, BC.alignedToFibo))
    assert aligned, "bc:Deposit carries no FIBO alignment annotation"
    assert all(isinstance(a, URIRef) for a in aligned)


def test_alignment_is_documented(repo_root):
    doc = (repo_root / "docs" / "fibo-alignment.md").read_text(encoding="utf-8")
    assert "Deposit" in doc and "Loan" in doc
    assert "spec.edmcouncil.org/fibo/ontology" in doc


def test_minimum_corpus_size(kb):
    entries = _curated_entries(kb)
    assert len(entries) >= 15, f"only {len(entries)} curated entries"


def test_coverage_categories_present(kb):
    classes = set(_classes(kb))
    for category, root in CATEGORY_ROOTS.items():
        subtree = {c for c in kb.descendants(root) if c in classes}
        assert subtree, f"category {category} has no curated class"
        assert any(kb.definition(c) for c in subtree), (
            f"category {category} has no curated class with a definition"
        )


def test_no_internal_data_markers(kb):
    markers = ("招商", "cmb", "内网", "机密", "confidential", "非公开", "内部数据")
    for note in kb.graph.objects(None, SKOS.editorialNote):
        text = str(note).lower()
        assert not any(m in text for m in markers), f"marker in editorialNote: {text}"
    for label in kb.graph.objects(None, RDFS.label):
        assert "招商银行" not in str(label)
