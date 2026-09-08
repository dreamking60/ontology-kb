"""Declarative demo rules evaluated over the knowledge base (specs/reasoning-demo).

Each rule is a small declarative record: id/title/human-readable text plus an
``evaluate`` callable that inspects a graph and returns derived triples. Every
returned triple is tagged with its rule by the caller.
"""
from __future__ import annotations

from typing import Callable, NamedTuple

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .kb import BC

Triple = tuple[URIRef, URIRef, URIRef]


class DemoRule(NamedTuple):
    id: str
    title: str
    text: str
    evaluate: Callable[[Graph], list[Triple]]


def _long_term_rule(graph: Graph) -> list[Triple]:
    """Deposits with termMonths >= 60 are classified as long-term time deposits."""
    q = """
    PREFIX bc:  <https://ontology.example/banking-core#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?s WHERE {
      ?s rdf:type/rdfs:subClassOf* bc:TimeDeposit .
      ?s bc:termMonths ?term .
      FILTER(?term >= 60)
    }
    """
    rows = []
    for row in graph.query(q):
        subject = row[0]
        if isinstance(subject, URIRef) and (subject, RDF.type, BC.LongTermTimeDeposit) not in graph:
            rows.append((subject, RDF.type, BC.LongTermTimeDeposit))
    return rows


LONG_TERM_RULE = DemoRule(
    id="long-term-deposit-rule",
    title="长期定期存款判定",
    text=(
        "IF ?s 是 bc:TimeDeposit（或其子类）的实例 AND ?s 的 bc:termMonths >= 60 "
        "THEN 将 ?s 归类为 bc:LongTermTimeDeposit（长期定期存款，演示分类）。"
    ),
    evaluate=_long_term_rule,
)

# The ordered demo rule set (extend here for future demo rules).
DEMO_RULES: list[DemoRule] = [LONG_TERM_RULE]


def evaluate_all(graph: Graph) -> dict[str, list[Triple]]:
    """Evaluate every demo rule over *graph*; returns rule_id -> derived triples."""
    results: dict[str, list[Triple]] = {}
    for rule in DEMO_RULES:
        results[rule.id] = rule.evaluate(graph)
    return results
