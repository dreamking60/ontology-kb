"""API contract tests for POST /api/chat (specs/rag-question-answering)."""
from __future__ import annotations

from fastapi.testclient import TestClient

import banking_kb.llm as llm_module
from banking_kb.api import app

client = TestClient(app)


def test_empty_question_is_rejected(monkeypatch):
    called: list[bool] = []

    def fake(*args, **kwargs):  # pragma: no cover - must not be reached
        called.append(True)

    monkeypatch.setattr(llm_module, "read_llm_config", fake)
    resp = client.post("/api/chat", json={"question": "   "})
    assert resp.status_code == 422
    assert called == []


def test_chat_fallback_without_llm_key(monkeypatch):
    for var in (llm_module.ENV_BASE_URL, llm_module.ENV_API_KEY, llm_module.ENV_MODEL):
        monkeypatch.delenv(var, raising=False)
    resp = client.post("/api/chat", json={"question": "什么是大额存单？"})
    assert resp.status_code == 200
    body = resp.json()
    for key in ("answer", "mode", "citations", "context", "retrieval_summary"):
        assert key in body
    assert body["mode"] == "fallback"
    assert body["answer"]
    assert "大额存单" in [c["label"] for c in body["citations"]]


def test_chat_synonym_question_via_api(monkeypatch):
    for var in (llm_module.ENV_BASE_URL, llm_module.ENV_API_KEY, llm_module.ENV_MODEL):
        monkeypatch.delenv(var, raising=False)
    body = client.post("/api/chat", json={"question": "定存有什么特点？"}).json()
    assert body["mode"] == "fallback"
    assert "定期存款" in [c["label"] for c in body["citations"]]


def test_chat_llm_mode(monkeypatch):
    captured: list[list[dict]] = []

    class FakeCfg:
        base_url = "https://llm.example/v1"
        api_key = "k"
        model = "m"

    monkeypatch.setattr(llm_module, "read_llm_config", lambda: FakeCfg())

    def fake_complete(messages, config=None, http=None):
        captured.append(messages)
        return "大额存单是面向个人与企业发行的高起点存款凭证。"

    monkeypatch.setattr(llm_module, "complete", fake_complete)
    body = client.post("/api/chat", json={"question": "什么是大额存单？"}).json()
    assert body["mode"] == "llm"
    assert "大额存单" in body["answer"]
    assert captured and any("知识库资料" in m["content"] for m in captured[0])
