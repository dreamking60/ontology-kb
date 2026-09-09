"""Read-only tool registry for the agentic QA assistant (specs/agentic-question-answering,
design.md D2/D3).

Every tool operates strictly read-only over the in-memory knowledge base and
returns ``(text_summary, citations)`` where citations is a list of
``{"id", "label"}`` concept references used by the tool output. The SPARQL tool
is additionally gated: only ``SELECT``/``ASK`` statements are accepted.
"""
from __future__ import annotations

import re
from typing import Callable

from rdflib import URIRef
from rdflib.namespace import RDF

from . import rag, reasoning
from .kb import BC, EX, KnowledgeBase

MAX_SPARQL_ROWS = 50
MAX_SPARQL_LENGTH = 2000
_ALLOWED_SPARQL = ("SELECT", "ASK")
_BLOCKED_SPARQL_KEYWORDS = (
    "INSERT", "DELETE", "LOAD", "CLEAR", "DROP", "MOVE", "COPY", "CREATE", "WITH",
)
_SUMMARY_LIMIT = 600  # chars per tool summary


def _label(kb: KnowledgeBase, uri: URIRef) -> str:
    labels = kb.labels(uri)
    return labels["zh"] or labels["en"] or str(uri).split("#")[-1]


def _citation(kb: KnowledgeBase, uri: URIRef) -> dict:
    return {"id": str(uri), "label": _label(kb, uri)}


def _clip(text: str, limit: int = _SUMMARY_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…(已截断)"


# --------------------------------------------------------------------------- #
# Tool implementations
# --------------------------------------------------------------------------- #


def tool_search_concepts(kb: KnowledgeBase, arguments: dict) -> tuple[str, list[dict]]:
    term = str(arguments.get("term") or arguments.get("query") or "").strip()
    if not term:
        raise ValueError("search_concepts 需要参数 term。")
    concepts = rag.retrieve(kb, term)
    citations = [_citation(kb, URIRef(c["id"])) for c in concepts]
    if not concepts:
        return f"未找到与「{term}」相关的概念。", []
    lines = [f"找到 {len(concepts)} 个相关概念："]
    for c in concepts[:6]:
        name = c["label_zh"] or c["label_en"]
        line = f"- {name}" + (f" ({c['label_en']})" if c.get("label_en") else "")
        if c["definition"]:
            line += f"：{c['definition'][:90]}"
        lines.append(line)
    return _clip("\n".join(lines)), citations


def tool_concept_detail(kb: KnowledgeBase, arguments: dict) -> tuple[str, list[dict]]:
    identifier = str(arguments.get("identifier") or arguments.get("id") or "").strip()
    uri = kb.resolve(identifier) if identifier else None
    if uri is None:
        raise ValueError(f"未找到概念：{identifier or '<空>'}。可用 search_concepts 先查找。")
    detail = kb.concept_detail(uri)
    if detail is None:
        raise ValueError(f"未找到概念：{identifier}。")
    lines = [f"{detail['label_zh'] or detail['label_en']} ({detail['kind']})"]
    if detail.get("label_en"):
        lines.append(f"英文：{detail['label_en']}")
    if detail["definition"]:
        lines.append(f"定义：{detail['definition']}")
    if detail.get("synonyms"):
        lines.append("同义词：" + "、".join(detail["synonyms"]))
    if detail.get("superclass"):
        lines.append(f"上级类：{detail['superclass']['label']}")
    if detail.get("subclasses"):
        lines.append("子类：" + "、".join(s["label"] for s in detail["subclasses"][:6]))
    if detail.get("types"):
        lines.append("类型：" + "、".join(t["label"] for t in detail["types"]))
    if detail.get("attributes"):
        attrs = "、".join(f"{a['property_label']}={a['value']}" for a in detail["attributes"])
        lines.append(f"关键属性：{attrs}")
    if detail.get("relationships"):
        rels = "、".join(f"{r['property_label']}→{r['value_label']}" for r in detail["relationships"])
        lines.append(f"关系：{rels}")
    return _clip("\n".join(lines)), [_citation(kb, uri)]


def _find_node(nodes: list[dict], label: str) -> dict | None:
    for node in nodes:
        if label and (node["label_zh"] == label or node["label_en"].lower() == label.lower()):
            return node
        found = _find_node(node["children"], label)
        if found:
            return found
    return None


def tool_browse_tree(kb: KnowledgeBase, arguments: dict) -> tuple[str, list[dict]]:
    root = str(arguments.get("root") or "").strip()
    tree = kb.tree()
    citations = []
    if root:
        node = _find_node(tree, root)
        if node is None:
            raise ValueError(f"层级中没有「{root}」。可选根：产品/账户/主体。")
        tree = [node]
    lines: list[str] = []
    max_nodes = 60
    rendered = 0

    def walk(nodes: list[dict], depth: int) -> None:
        nonlocal rendered
        for node in nodes:
            if rendered >= max_nodes:
                return
            rendered += 1
            indent = "  " * depth
            lines.append(f"{indent}- {node['label_zh']} ({node['label_en']})")
            if depth == 0 and not root:
                # Top-level overview: show direct children only, not the full tree.
                for child in node["children"][:8]:
                    if rendered >= max_nodes:
                        return
                    rendered += 1
                    lines.append(f"  {indent}  - {child['label_zh']} ({child['label_en']})")
                continue
            walk(node["children"], depth + 1)

    walk(tree, 0)
    return _clip("\n".join(lines) if lines else "（无内容）"), citations


def tool_reasoning_demo(kb: KnowledgeBase, arguments: dict) -> tuple[str, list[dict]]:
    result = reasoning.run_reasoning_demo(kb)
    citations: list[dict] = []
    seen: set[str] = set()
    for facts in (result["inferred_type_facts"], result["rule_derived_facts"]):
        for fact in facts:
            if fact["subject"] not in seen:
                seen.add(fact["subject"])
                citations.append({"id": fact["subject"], "label": fact["subject_label"]})
    inferred = result["inferred_type_facts"]
    rules = result["rule_derived_facts"]
    lines = [
        f"推理演示完成：一致性={result['consistency']['status']}；"
        f"数据未被修改={result['store_unchanged']['unchanged']}。",
        f"推理得到的类型 {len(inferred)} 条，例如：",
    ]
    for fact in inferred[:6]:
        lines.append(f"- {fact['subject_label']} → {fact['object_label']}（{fact['provenance']}）")
    if rules:
        lines.append(f"演示规则推导 {len(rules)} 条：")
        for fact in rules[:4]:
            lines.append(f"- {fact['subject_label']} → {fact['object_label']}（规则：{fact['rule']['title']}）")
    else:
        lines.append("演示规则未命中个体。")
    return _clip("\n".join(lines)), citations


def _query_form(query: str) -> str | None:
    """First keyword (upper) after any leading PREFIX/BASE declarations."""
    body = re.sub(
        r"(?is)^(?:\s*(?:PREFIX\s+\w+:\s*<[^>]*>|BASE\s*<[^>]*>))+", "", query.strip()
    )
    first = re.match(r"[A-Za-z]+", body.lstrip())
    return first.group(0).upper() if first else None


def _validate_sparql(query: str) -> None:
    stripped = query.strip()
    if not stripped:
        raise ValueError("SPARQL 查询为空。")
    if len(stripped) > MAX_SPARQL_LENGTH:
        raise ValueError(f"SPARQL 查询超过 {MAX_SPARQL_LENGTH} 字符限制。")
    if stripped.count(";") > 0:
        raise ValueError("只允许单条 SPARQL 查询（不允许分号分隔的多个语句）。")
    if _query_form(stripped) not in _ALLOWED_SPARQL:
        raise ValueError("只读工具仅支持 SELECT / ASK 查询。")
    upper = stripped.upper()
    for keyword in _BLOCKED_SPARQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper):
            raise ValueError(f"只读工具拒绝变更语句：{keyword}。数据集不会被修改。")


def tool_sparql_query(kb: KnowledgeBase, arguments: dict) -> tuple[str, list[dict]]:
    query = str(arguments.get("query") or "").strip()
    _validate_sparql(query)
    try:
        result = kb.graph.query(query)
    except Exception as exc:  # noqa: BLE001 - surfaced to the LLM as tool text
        raise ValueError(f"SPARQL 执行失败：{exc}") from exc
    if _query_form(query) == "ASK":
        try:
            return f"ASK 结果：{bool(result.askAnswer)}", []
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"SPARQL 执行失败：{exc}") from exc
    citations: list[dict] = []
    seen: set[str] = set()
    lines: list[str] = []
    row_count = 0
    for row in result:
        if row_count >= MAX_SPARQL_ROWS:
            lines.append(f"…（已截断，仅显示前 {MAX_SPARQL_ROWS} 行）")
            break
        row_count += 1
        cells = []
        for value in row:
            if isinstance(value, URIRef):
                cells.append(_label(kb, value) or str(value))
                if str(value).startswith((str(BC), str(EX))) and str(value) not in seen:
                    seen.add(str(value))
                    citations.append(_citation(kb, value))
            else:
                cells.append(str(value))
        lines.append(" | ".join(cells))
    if not lines:
        return "查询无结果。", []
    return _clip("\n".join(lines)), citations


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

ToolFn = Callable[[KnowledgeBase, dict], tuple[str, list[dict]]]


def _make_tool(kb: KnowledgeBase, fn: ToolFn, name: str, description: str, parameters: dict) -> dict:
    """OpenAI-compatible function descriptor + bound callable."""
    return {
        "schema": {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        },
        "call": lambda arguments: fn(kb, arguments),
    }


def build_tools(kb: KnowledgeBase) -> list[dict]:
    return [
        _make_tool(
            kb,
            tool_search_concepts,
            "search_concepts",
            "按关键词/问题在本体知识库中做语义搜索（支持中文/英文标签与同义词），返回相关概念及其定义。",
            {
                "type": "object",
                "properties": {"term": {"type": "string", "description": "要检索的概念词或问题，例如 存款 / 定存 / 大额存单"},
                               },
                "required": ["term"],
            },
        ),
        _make_tool(
            kb,
            tool_concept_detail,
            "concept_detail",
            "查看某个概念（类或示例个体）的完整详情：定义、属性、层级与关系。identifier 可用 Deposit、bc:Loan、DemoHousingLoan 等形式。",
            {
                "type": "object",
                "properties": {"identifier": {"type": "string", "description": "概念标识，如 CertificateOfDeposit 或 DemoHousingLoan"}},
                "required": ["identifier"],
            },
        ),
        _make_tool(
            kb,
            tool_browse_tree,
            "browse_tree",
            "浏览概念类层级树（根：产品 / 账户 / 主体，可指定某类下钻）。",
            {
                "type": "object",
                "properties": {"root": {"type": "string", "description": "可选：层级节点名，例如 存款 或 Product"}},
            },
        ),
        _make_tool(
            kb,
            tool_reasoning_demo,
            "reasoning_demo",
            "运行本体推理演示（OWL2-RL 类层级推断 + 演示规则），返回带溯源(inferred/rule-derived)的事实，不会修改数据。",
            {"type": "object", "properties": {}},
        ),
        _make_tool(
            kb,
            tool_sparql_query,
            "sparql_query",
            "对知识库执行只读 SPARQL（仅 SELECT/ASK），前缀可用 bc(本体)、ex(示例个体)、rdfs、rdf、skos；返回结果表格文本。",
            {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "只读 SELECT/ASK 查询，如：PREFIX bc:<https://ontology.example/banking-core#> SELECT ?s WHERE { ?s bc:depositInsuranceCovered true }"}},
                "required": ["query"],
            },
        ),
    ]


def tool_schemas(tools: list[dict]) -> list[dict]:
    return [t["schema"] for t in tools]


def execute_tool(tools: list[dict], name: str, arguments: dict) -> tuple[str, list[dict]]:
    """Execute a registry tool by name; raises KeyError when unknown."""
    for tool in tools:
        if tool["schema"]["function"]["name"] == name:
            try:
                return tool["call"](arguments or {})
            except (ValueError, TypeError) as exc:
                return f"[工具错误] {exc}", []
    raise KeyError(f"未知工具：{name}。可用工具：" + ", ".join(
        t["schema"]["function"]["name"] for t in tools
    ))
