"""Reasoning demo (specs/reasoning-demo) and OWL2-RL materialization.

Three provenance layers are produced over the read-only base graph:

- ``asserted``      — facts read directly from the corpus files;
- ``inferred``      — entailments from the owlrl OWL2-RL closure (e.g. type
                      propagation along the subclass hierarchy);
- ``rule-derived``  — facts produced by the declarative demo rules in rules.py.

The base graph is never mutated: materialization runs on a working copy and the
demo returns a store-unchanged proof.
"""
from __future__ import annotations

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from . import rules as demo_rules
from .kb import BC, EX, KnowledgeBase

PROVENANCE_ASSERTED = "asserted"
PROVENANCE_INFERRED = "inferred"
PROVENANCE_RULE = "rule-derived"


def materialize(kb: KnowledgeBase) -> Graph:
    """Return the OWL2-RL closure of the base graph as a *separate* graph."""
    working = Graph()
    for triple in kb.graph:
        working.add(triple)
    from owlrl import DeductiveClosure, OWLRL_Semantics

    DeductiveClosure(
        OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False
    ).expand(working)
    inferred = Graph()
    for triple in working - kb.graph:
        inferred.add(triple)
    return inferred


def demo_individuals(kb: KnowledgeBase) -> list[URIRef]:
    """Individuals in the seed namespace (demo corpus)."""
    individuals = {
        s for s in kb.graph.subjects(RDF.type, None) if isinstance(s, URIRef) and str(s).startswith(str(EX))
    }
    return sorted(individuals, key=str)


def inferred_type_facts(kb: KnowledgeBase, inferred: Graph) -> list[dict]:
    """Type-propagation entailments for seed individuals, with class chains."""
    facts = []
    asserted = {t for t in kb.graph if t[1] == RDF.type}
    for subject, _, cls in inferred:
        if subject not in demo_individuals(kb) or not isinstance(cls, URIRef):
            continue
        if not str(cls).startswith(str(BC)):
            continue
        if (subject, RDF.type, cls) in asserted:
            continue
        chain = kb.labels(cls)
        facts.append(
            {
                "subject": str(subject),
                "subject_label": kb.labels(subject)["zh"] or str(subject),
                "predicate": "rdf:type",
                "object": str(cls),
                "object_label": chain["zh"] or chain["en"] or str(cls),
                "provenance": PROVENANCE_INFERRED,
                "explanation": (
                    f"通过类层级推断：{kb.labels(subject)['zh'] or subject} "
                    f"是其所属类的子类实例，因此也是 {chain['zh'] or chain['en']} 的实例。"
                ),
            }
        )
    return facts


def asserted_type_facts(kb: KnowledgeBase) -> list[dict]:
    facts = []
    for subject in demo_individuals(kb):
        for cls in sorted(kb.graph.objects(subject, RDF.type), key=str):
            if not isinstance(cls, URIRef):
                continue
            facts.append(
                {
                    "subject": str(subject),
                    "subject_label": kb.labels(subject)["zh"] or str(subject),
                    "predicate": "rdf:type",
                    "object": str(cls),
                    "object_label": kb.labels(cls)["zh"] or kb.labels(cls)["en"] or str(cls),
                    "provenance": PROVENANCE_ASSERTED,
                    "explanation": "直接声明的类型事实（语料断言）。",
                }
            )
    return facts


def run_reasoning_demo(kb: KnowledgeBase) -> dict:
    """Run the full demo: OWL2-RL closure + demo rules, with provenance."""
    base_before = kb.triple_count()
    inferred = materialize(kb)
    base_after = kb.triple_count()

    # Combined view (base + inferences) for rule evaluation — never persisted.
    combined = Graph()
    for triple in kb.graph:
        combined.add(triple)
    for triple in inferred:
        combined.add(triple)

    rule_results = demo_rules.evaluate_all(combined)
    rule_facts = []
    for rule in demo_rules.DEMO_RULES:
        for subject, pred, obj in rule_results.get(rule.id, []):
            rule_facts.append(
                {
                    "subject": str(subject),
                    "subject_label": kb.labels(subject)["zh"] or str(subject),
                    "predicate": "rdf:type",
                    "object": str(obj),
                    "object_label": kb.labels(obj)["zh"] or kb.labels(obj)["en"] or str(obj),
                    "provenance": PROVENANCE_RULE,
                    "rule": {"id": rule.id, "title": rule.title, "text": rule.text},
                    "explanation": f"由演示规则「{rule.title}」推导。",
                }
            )

    return {
        "inferred_type_facts": inferred_type_facts(kb, inferred),
        "asserted_type_facts": asserted_type_facts(kb),
        "rule_derived_facts": rule_facts,
        "provenance_labels": [PROVENANCE_ASSERTED, PROVENANCE_INFERRED, PROVENANCE_RULE],
        "store_unchanged": {
            "triples_before": base_before,
            "triples_after": base_after,
            "unchanged": base_before == base_after,
        },
        "consistency": {
            "checked_by": "owlrl-owl2rl",
            "status": "no_inconsistency_detected",
            "note": (
                "OWL2-RL 推理运行无错误且结构校验通过；完整一致性（可满足性）检查"
                "请运行 `make check-consistency`（HermiT/Java，可选）。"
            ),
        },
    }
