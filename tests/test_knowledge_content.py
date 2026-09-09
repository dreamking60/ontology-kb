"""Spec coverage: specs/knowledge-content/spec.md."""
from __future__ import annotations

from rdflib import URIRef
from rdflib.namespace import RDFS, SKOS

from banking_kb import reasoning
from banking_kb.kb import BC, KnowledgeBase
from banking_kb.search import search

# The coverage categories from specs/knowledge-content/spec.md, extended by
# the ontology-enrichment delta (rate & pricing, banking events added).
CATEGORY_ROOTS = {
    "deposit": BC.Deposit,
    "loan": BC.Loan,
    "wealth_management": BC.WealthManagementProduct,
    "account": BC.Account,
    "party": BC.Party,
    "rate": BC.Rate,
    "banking_event": BC.BankingEvent,
}

EXPANDED_MIN_CLASSES = 50
EXPANDED_MIN_INDIVIDUALS = 30

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


# --------------------------------------------------------------------------- #
# ontology-enrichment delta: expanded corpus and verified FIBO alignment
# --------------------------------------------------------------------------- #

def test_expanded_corpus_counts(kb):
    classes = [c for c in kb.candidate_concepts() if kb.is_class(c)]
    individuals = [c for c in kb.candidate_concepts() if not kb.is_class(c)]
    assert len(classes) >= EXPANDED_MIN_CLASSES, f"only {len(classes)} classes"
    assert len(individuals) >= EXPANDED_MIN_INDIVIDUALS, f"only {len(individuals)} individuals"


def test_expanded_categories_present(kb):
    classes = set(_classes(kb))
    for category, root in CATEGORY_ROOTS.items():
        subtree = {c for c in kb.descendants(root) if c in classes}
        assert subtree, f"category {category} has no curated class"
        assert any(kb.definition(c) for c in subtree), (
            f"category {category} has no curated class with a definition"
        )


def test_all_alignment_iris_resolve_in_pinned_manifest(kb, repo_root):
    import json

    manifest = json.loads(
        (repo_root / "docs" / "reference" / "fibo-verified.json").read_text(encoding="utf-8")
    )
    known = {iri for module in manifest.values() for iri in module.values()}
    aligned = {str(o) for o in kb.graph.objects(BC.Deposit, BC.alignedToFibo)}
    for node in kb.candidate_concepts():
        aligned |= {str(o) for o in kb.graph.objects(node, BC.alignedToFibo)}
    assert aligned, "no alignment annotations found"
    unresolved = [iri for iri in sorted(aligned) if iri not in known]
    assert unresolved == [], f"unresolved alignment IRIs: {unresolved}"


def test_no_legacy_best_effort_alignment_iris(kb):
    legacy = "FND/ProductsAndServices/FinancialProductsAndServices/Deposit"
    for node in kb.candidate_concepts():
        for obj in kb.graph.objects(node, BC.alignedToFibo):
            assert legacy not in str(obj), f"stale best-effort IRI on {node}"


def test_alignment_doc_lists_modules_and_date(repo_root):
    doc = (repo_root / "docs" / "fibo-alignment.md").read_text(encoding="utf-8")
    assert "ClientsAndAccounts" in doc and "Mortgages" in doc
    assert "119fa8c091aa4beece7d22aefa6fe138021a4355" in doc
    assert "never imports" in doc or "never imported" in doc


def test_sources_dossier_lists_fibo(repo_root):
    dossier = (repo_root / "docs" / "reference" / "ontology-sources.md").read_text(
        encoding="utf-8"
    )
    assert "github.com/edmcouncil/fibo" in dossier
    assert "self-authored" in dossier
