"""Tool registry tests (specs/agentic-question-answering, design D2/D3)."""
from __future__ import annotations

import pytest

from banking_kb import tools
from banking_kb.kb import KnowledgeBase

SPARQL_PREFIX = "PREFIX bc: <https://ontology.example/banking-core#> "


def _exec(kb: KnowledgeBase, name: str, **arguments) -> tuple[str, list[dict]]:
    registry = tools.build_tools(kb)
    return tools.execute_tool(registry, name, arguments)


def test_search_tool(kb):
    text, citations = _exec(kb, "search_concepts", term="大额存单")
    assert "大额存单" in text
    assert any(c["label"] == "大额存单" for c in citations)


def test_concept_detail_tool(kb):
    text, citations = _exec(kb, "concept_detail", identifier="CertificateOfDeposit")
    assert "大额存单" in text and "定期存款" in text
    assert citations[0]["label"] == "大额存单"


def test_browse_tree_tool(kb):
    text, _ = _exec(kb, "browse_tree")
    assert "产品" in text and "主体" in text
    deposit_text, _ = _exec(kb, "browse_tree", root="存款")
    assert "大额存单" in deposit_text and "活期存款" in deposit_text


def test_reasoning_demo_tool(kb):
    text, citations = _exec(kb, "reasoning_demo")
    assert "推理演示完成" in text
    assert "长期定期存款" in text  # demo rule fact is described
    assert citations  # subject concepts referenced


def test_sparql_select_tool(kb):
    query = (
        f"{SPARQL_PREFIX}SELECT ?s WHERE {{ ?s bc:depositInsuranceCovered true }}"
    )
    text, citations = _exec(kb, "sparql_query", query=query)
    assert "示例活期存款" in text
    assert any(c["label"] == "示例活期存款" for c in citations)


def test_sparql_ask_tool(kb):
    query = (
        f"{SPARQL_PREFIX}ASK {{ bc:Deposit rdfs:subClassOf bc:Product }}"
    )
    text, _ = _exec(kb, "sparql_query", query=query)
    assert "True" in text


@pytest.mark.parametrize(
    "query",
    [
        "INSERT DATA { <urn:a> <urn:p> <urn:b> }",
        "DELETE WHERE { ?s ?p ?o }",
        "LOAD <file:///x>",
        "CLEAR ALL",
        "DROP GRAPH <urn:g>",
    ],
)
def test_sparql_rejects_mutations(kb, query):
    text, citations = _exec(kb, "sparql_query", query=query)
    assert "只读" in text
    assert citations == []


def test_sparql_tool_error_is_safe(kb):
    text, _ = _exec(kb, "sparql_query", query="SELECT ?s WHERE { ?s zzz:NoSuchProp ?o }")
    assert "SPARQL 执行失败" in text  # unknown prefix error surfaces as text


def test_sparql_result_row_cap(kb):
    text, _ = _exec(kb, "sparql_query", query="SELECT ?s WHERE { ?s ?p ?o }")
    assert "已截断" in text  # result set exceeds the 50-row cap


def test_unknown_tool_raises(kb):
    registry = tools.build_tools(kb)
    with pytest.raises(KeyError):
        tools.execute_tool(registry, "not_a_tool", {})
