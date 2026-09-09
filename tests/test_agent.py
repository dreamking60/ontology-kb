"""Agent loop tests (specs/agentic-question-answering, design D1/D5)."""
from __future__ import annotations

import banking_kb.llm as llm_module
from banking_kb import agent, llm
from banking_kb.kb import KnowledgeBase

CFG = llm.LLMConfig(base_url="https://llm.example/v1", api_key="k", model="m")


def _scripted(sequence: list[llm.ChatTurn]):
    def fake(messages, tools, config=None, http=None):
        return sequence.pop(0)

    return fake


def test_multi_tool_question_executes_tools_then_answers(kb, monkeypatch):
    sequence = [
        llm.ChatTurn(
            content=None,
            tool_calls=[
                llm.ToolCall("c1", "search_concepts", '{"term": "存款"}'),
                llm.ToolCall("c2", "concept_detail", '{"identifier": "DemandDeposit"}'),
            ],
        ),
        llm.ChatTurn(content="定期存款与活期存款的区别如下…", tool_calls=[]),
    ]
    monkeypatch.setattr(llm_module, "complete_with_tools", _scripted(sequence))
    resp = agent.run_agent_question(
        kb, "定期存款和活期存款有什么区别？", config=CFG, max_turns=4
    )
    assert resp["mode"] == "agent"
    assert "区别" in resp["answer"]
    tools_used = [t["tool"] for t in resp["trace"]]
    assert tools_used == ["search_concepts", "concept_detail"]
    assert resp["trace"][0]["step"] == 1
    assert resp["citations"]  # concepts seen in tool output


def test_budget_exhaustion_reports_step_limit(kb, monkeypatch):
    def always_tools(messages, tools, config=None, http=None):
        return llm.ChatTurn(
            content=None,
            tool_calls=[llm.ToolCall("c", "search_concepts", '{"term": "存款"}')],
        )

    monkeypatch.setattr(llm_module, "complete_with_tools", always_tools)
    resp = agent.run_agent_question(kb, "请一直搜索", config=CFG, max_turns=3)
    assert resp["mode"] == "agent"
    assert len(resp["trace"]) == 3
    assert "上限" in resp["answer"]
    assert resp["retrieval_summary"]["termination"] == "budget_exhausted"


def test_tool_error_is_returned_and_loop_continues(kb, monkeypatch):
    sequence = [
        llm.ChatTurn(
            content=None,
            tool_calls=[
                llm.ToolCall("c1", "sparql_query", '{"query": "INSERT DATA { <a> <b> <c> }"}')
            ],
        ),
        llm.ChatTurn(content="SPARQL 只能执行只读查询。", tool_calls=[]),
    ]
    monkeypatch.setattr(llm_module, "complete_with_tools", _scripted(sequence))
    resp = agent.run_agent_question(kb, "试着写入数据", config=CFG, max_turns=3)
    assert resp["mode"] == "agent"
    assert "只读" in resp["trace"][0]["summary"]
    assert "只读" in resp["answer"]


def test_tools_unsupported_degrades_to_rag_synthesis(kb, monkeypatch):
    monkeypatch.setattr(llm_module, "complete_with_tools", lambda *a, **k: None)
    monkeypatch.setattr(
        llm_module, "complete", lambda *a, **k: "这是综合后的自然语言回答。"
    )
    resp = agent.run_agent_question(kb, "什么是大额存单？", config=CFG)
    assert resp["mode"] == "llm"
    assert "综合" in resp["answer"]
    assert resp["trace"] == []
    assert resp["retrieval_summary"]["termination"] == "tools_unavailable"


def test_no_llm_config_degrades_to_fallback(kb, monkeypatch):
    for var in (llm_module.ENV_BASE_URL, llm_module.ENV_API_KEY, llm_module.ENV_MODEL):
        monkeypatch.delenv(var, raising=False)
    resp = agent.run_agent_question(kb, "什么是信用贷款？")
    assert resp["mode"] == "fallback"
    assert resp["trace"] == []
    assert resp["citations"]
    assert "信用贷款" in resp["answer"]
