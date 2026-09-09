"""API contract tests for POST /api/agent/chat (specs/agentic-question-answering)."""
from __future__ import annotations

from fastapi.testclient import TestClient

import banking_kb.llm as llm_module
from banking_kb import llm
from banking_kb.api import app

client = TestClient(app)
CONTRACT_KEYS = {"answer", "mode", "citations", "trace", "retrieval_summary"}


def test_empty_question_is_rejected(monkeypatch):
    called: list[bool] = []

    def fake(*a, **k):  # pragma: no cover - must not run
        called.append(True)

    monkeypatch.setattr(llm_module, "complete_with_tools", fake)
    resp = client.post("/api/agent/chat", json={"question": "   "})
    assert resp.status_code == 422
    assert called == []


def test_no_llm_key_fallback_contract(monkeypatch):
    for var in (llm_module.ENV_BASE_URL, llm_module.ENV_API_KEY, llm_module.ENV_MODEL):
        monkeypatch.delenv(var, raising=False)
    resp = client.post("/api/agent/chat", json={"question": "什么是信用贷款？"})
    assert resp.status_code == 200
    body = resp.json()
    assert CONTRACT_KEYS <= set(body)
    assert body["mode"] == "fallback"
    assert body["trace"] == []
    assert body["citations"]


def test_agent_mode_with_tools(monkeypatch):
    monkeypatch.setenv(llm_module.ENV_BASE_URL, "https://llm.example/v1")
    monkeypatch.setenv(llm_module.ENV_API_KEY, "k")
    monkeypatch.setenv(llm_module.ENV_MODEL, "m")
    sequence = [
        llm.ChatTurn(
            content=None,
            tool_calls=[llm.ToolCall("c1", "concept_detail", '{"identifier": "CreditLoan"}')],
        ),
        llm.ChatTurn(content="信用贷款是基于信用而非抵押物的个人贷款。", tool_calls=[]),
    ]

    def fake(messages, tools, config=None, http=None):
        return sequence.pop(0)

    monkeypatch.setattr(llm_module, "complete_with_tools", fake)
    resp = client.post("/api/agent/chat", json={"question": "什么是信用贷款？"})
    assert resp.status_code == 200
    body = resp.json()
    assert CONTRACT_KEYS <= set(body)
    assert body["mode"] == "agent"
    assert body["trace"][0]["tool"] == "concept_detail"
    assert "信用贷款" in body["answer"]


def test_tools_unsupported_llm_mode(monkeypatch):
    monkeypatch.setenv(llm_module.ENV_BASE_URL, "https://llm.example/v1")
    monkeypatch.setenv(llm_module.ENV_API_KEY, "k")
    monkeypatch.setenv(llm_module.ENV_MODEL, "m")
    monkeypatch.setattr(llm_module, "complete_with_tools", lambda *a, **k: None)
    monkeypatch.setattr(llm_module, "complete", lambda *a, **k: "综合回答：信用贷款…")
    resp = client.post("/api/agent/chat", json={"question": "什么是信用贷款？"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "llm"
    assert body["trace"] == []
    assert "信用贷款" in body["answer"]
