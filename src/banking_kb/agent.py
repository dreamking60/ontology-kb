"""Bounded, tool-calling question-answering agent over the concept KB
(specs/agentic-question-answering, design.md D1/D4/D5).

The agent lets an OpenAI-compatible LLM call read-only KB tools iteratively,
then synthesizes a grounded final answer. Degradation ladder:

1. tools request succeeds          -> mode ``agent``
2. endpoint rejects ``tools``      -> phase-2 single-turn RAG synthesis (mode ``llm``)
3. no LLM configured / call fails  -> deterministic retrieval summary (mode ``fallback``)
"""
from __future__ import annotations

import json
from typing import Optional

from . import llm, rag
from . import tools as kb_tools
from .kb import KnowledgeBase

MAX_AGENT_TURNS = 8

_SYSTEM_PROMPT = (
    "你是银行概念知识库问答智能体。你可以按需调用以下只读工具来收集信息："
    "search_concepts（语义检索概念）、concept_detail（概念详情）、"
    "browse_tree（层级浏览）、reasoning_demo（本体推理演示）、"
    "sparql_query（只读 SPARQL）。规则："
    "1) 只使用工具返回的内容作答，不得编造知识库之外的事实；"
    "2) 需要多个信息时先分别调用工具，再综合回答；"
    "3) 若工具显示知识库没有相关内容，明确说明知识库未收录，不要臆测；"
    "4) 使用与问题相同的语言作答（默认简体中文）；"
    "5) 当信息已足够时，直接给出最终回答，不要继续调用工具。"
)


def _history_messages(history: Optional[list[dict]]) -> list[dict]:
    if not history:
        return []
    return [
        {"role": m.get("role", "user"), "content": str(m.get("content", ""))}
        for m in history[-6:]
        if m.get("role") in ("user", "assistant")
    ]


def _merge_citations(citations: list[dict], seen: set[str], items: list[dict]) -> None:
    for item in items:
        if item.get("id") and item["id"] not in seen:
            seen.add(item["id"])
            citations.append(item)


def run_agent_question(
    kb: KnowledgeBase,
    question: str,
    history: Optional[list[dict]] = None,
    config: Optional[llm.LLMConfig] = None,
    http=None,
    max_turns: Optional[int] = None,
) -> dict:
    """Answer *question* through the agent loop; returns the /api/agent/chat contract."""
    budget = max_turns or MAX_AGENT_TURNS
    registry = kb_tools.build_tools(kb)
    schemas = kb_tools.tool_schemas(registry)
    cfg = config if config is not None else llm.read_llm_config()

    citations: list[dict] = []
    seen: set[str] = set()
    trace: list[dict] = []

    if cfg is None:
        resp = rag.answer_question(kb, question, history=history)
        return {
            "answer": resp["answer"],
            "mode": "fallback",
            "citations": resp["citations"],
            "trace": [],
            "retrieval_summary": {**resp["retrieval_summary"], "tool_calls": 0,
                                  "termination": "no_llm"},
        }

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages += _history_messages(history)
    messages.append({"role": "user", "content": question})

    for _ in range(budget):
        turn = llm.complete_with_tools(messages, schemas, config=cfg, http=http)
        if turn is None:
            # tools unsupported (or endpoint failure) -> single-turn RAG synthesis
            resp = rag.answer_question(kb, question, history=history, config=cfg, http=http)
            return {
                "answer": resp["answer"],
                "mode": resp["mode"],
                "citations": resp["citations"],
                "trace": [],
                "retrieval_summary": {**resp["retrieval_summary"], "tool_calls": 0,
                                      "termination": "tools_unavailable"},
            }
        if not turn.has_tool_calls:
            content = (turn.content or "").strip()
            if not content:
                content = "（模型未返回可显示的回答。）"
            return {
                "answer": content,
                "mode": "agent",
                "citations": citations,
                "trace": trace,
                "retrieval_summary": {"tool_calls": len(trace), "budget": budget,
                                      "termination": "final"},
            }
        assistant_message: dict = {"role": "assistant", "content": turn.content}
        assistant_message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in turn.tool_calls
        ]
        messages.append(assistant_message)
        for call in turn.tool_calls:
            try:
                parsed = json.loads(call.arguments or "{}")
                arguments = parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                arguments = {}
            try:
                text, tool_citations = kb_tools.execute_tool(registry, call.name, arguments)
            except KeyError as exc:
                text, tool_citations = f"[工具错误] {exc}", []
            _merge_citations(citations, seen, tool_citations)
            trace.append(
                {
                    "step": len(trace) + 1,
                    "tool": call.name,
                    "arguments": (call.arguments or "")[:300],
                    "summary": text[:500],
                }
            )
            messages.append({"role": "tool", "tool_call_id": call.id, "content": text})

    steps = "；".join(f"第{t['step']}步：{t['tool']}" for t in trace) or "（未执行任何工具）"
    return {
        "answer": f"在规定的 {budget} 步工具调用上限内未能完成回答。{steps}。"
                  "请拆分问题或补充更多信息后重试。",
        "mode": "agent",
        "citations": citations,
        "trace": trace,
        "retrieval_summary": {"tool_calls": len(trace), "budget": budget,
                              "termination": "budget_exhausted"},
    }
