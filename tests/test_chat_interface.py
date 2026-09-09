"""Spec coverage: specs/chat-interface/spec.md — config, streaming, SPA hosting.

Also guards key safety: runtime config never returns key material.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import banking_kb.llm as llm_module
from banking_kb import llm
from banking_kb.api import app

client = TestClient(app)
SECRET = "sk-super-secret-key-value"


@pytest.fixture(autouse=True)
def _isolate_runtime_config():
    llm.clear_runtime_config()
    yield
    llm.clear_runtime_config()


def _parse_events(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        evt_type = "message"
        data_parts: list[str] = []
        for ln in lines:
            if ln.startswith("event:"):
                evt_type = ln[6:].strip()
            elif ln.startswith("data:"):
                data_parts.append(ln[5:].strip())
        if not data_parts:
            continue
        payload = json.loads("\n".join(data_parts))
        payload.setdefault("type", evt_type)
        events.append(payload)
    return events


def _no_llm_env(monkeypatch) -> None:
    for var in (llm_module.ENV_BASE_URL, llm_module.ENV_API_KEY, llm_module.ENV_MODEL):
        monkeypatch.delenv(var, raising=False)


# ----------------------------------------------------------------- config ---

def test_config_default_unconfigured(monkeypatch):
    _no_llm_env(monkeypatch)
    body = client.get("/api/config").json()
    assert body["configured"] is False
    assert body["key_present"] is False


def test_config_post_get_delete(monkeypatch):
    _no_llm_env(monkeypatch)
    resp = client.post(
        "/api/config",
        json={"base_url": "https://llm.example/v1", "api_key": SECRET, "model": "m"},
    )
    assert resp.status_code == 200
    assert resp.json()["configured"] is True
    # GET must be masked — the raw key never appears anywhere in the response.
    got = client.get("/api/config")
    assert got.status_code == 200
    assert got.json()["key_present"] is True
    assert got.json()["base_url"] == "https://llm.example/v1"
    assert got.json()["model"] == "m"
    assert SECRET not in got.text
    cleared = client.delete("/api/config")
    assert cleared.status_code == 200
    assert cleared.json()["configured"] is False


def test_config_blank_values_rejected(monkeypatch):
    _no_llm_env(monkeypatch)
    resp = client.post(
        "/api/config", json={"base_url": "", "api_key": "", "model": ""}
    )
    assert resp.status_code == 422
    assert client.get("/api/config").json()["configured"] is False


def test_runtime_config_wins_over_env(monkeypatch):
    monkeypatch.setenv(llm_module.ENV_BASE_URL, "https://env.example/v1")
    monkeypatch.setenv(llm_module.ENV_API_KEY, "env-key")
    monkeypatch.setenv(llm_module.ENV_MODEL, "env-model")
    llm.set_runtime_config("https://runtime.example/v1", "runtime-key", "runtime-model")
    cfg = llm.read_llm_config()
    assert cfg is not None and cfg.base_url == "https://runtime.example/v1"
    llm.clear_runtime_config()
    cfg2 = llm.read_llm_config()
    assert cfg2 is not None and cfg2.base_url == "https://env.example/v1"


# ----------------------------------------------------------------- streams --

def test_chat_stream_fallback_without_llm(monkeypatch):
    _no_llm_env(monkeypatch)
    resp = client.post("/api/chat/stream", json={"question": "什么是大额存单？"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _parse_events(resp.text)
    assert events[-1]["type"] == "done"
    assert events[-1]["mode"] == "fallback"
    text = "".join(e.get("text", "") for e in events if e["type"] == "delta")
    assert "大额存单" in text
    assert any(e["type"] == "meta" for e in events)


def test_chat_stream_deltas_with_llm(monkeypatch):
    monkeypatch.setenv(llm_module.ENV_BASE_URL, "https://llm.example/v1")
    monkeypatch.setenv(llm_module.ENV_API_KEY, "k")
    monkeypatch.setenv(llm_module.ENV_MODEL, "m")

    def fake_stream(messages, config=None, http=None):
        yield "大额存单是"
        yield "面向个人与企业的"
        yield "高起点存款凭证。"

    monkeypatch.setattr(llm_module, "stream_complete", fake_stream)
    resp = client.post("/api/chat/stream", json={"question": "什么是大额存单？"})
    assert resp.status_code == 200
    events = _parse_events(resp.text)
    deltas = "".join(e.get("text", "") for e in events if e["type"] == "delta")
    assert deltas == "大额存单是面向个人与企业的高起点存款凭证。"
    done = events[-1]
    assert done["mode"] == "llm"
    assert any(e["type"] == "citations" for e in events)


def test_chat_stream_degrades_when_llm_stream_fails(monkeypatch):
    monkeypatch.setenv(llm_module.ENV_BASE_URL, "https://llm.example/v1")
    monkeypatch.setenv(llm_module.ENV_API_KEY, "k")
    monkeypatch.setenv(llm_module.ENV_MODEL, "m")

    def broken(messages, config=None, http=None):
        raise RuntimeError("provider down")
        yield  # pragma: no cover

    monkeypatch.setattr(llm_module, "stream_complete", broken)
    resp = client.post("/api/chat/stream", json={"question": "什么是信用贷款？"})
    events = _parse_events(resp.text)
    assert events[-1]["mode"] == "fallback"
    assert "降级" in "".join(e.get("text", "") for e in events if e["type"] == "delta")


def test_agent_stream_steps_and_final(monkeypatch):
    monkeypatch.setenv(llm_module.ENV_BASE_URL, "https://llm.example/v1")
    monkeypatch.setenv(llm_module.ENV_API_KEY, "k")
    monkeypatch.setenv(llm_module.ENV_MODEL, "m")
    sequence = [
        llm.ChatTurn(
            content=None,
            tool_calls=[
                llm.ToolCall("c1", "concept_detail", '{"identifier": "CreditLoan"}')
            ],
        ),
        llm.ChatTurn(content="信用贷款是基于信用而非抵押物的个人贷款。", tool_calls=[]),
    ]

    def fake(messages, tools, config=None, http=None):
        return sequence.pop(0)

    monkeypatch.setattr(llm_module, "complete_with_tools", fake)
    resp = client.post(
        "/api/agent/chat/stream", json={"question": "什么是信用贷款？"}
    )
    assert resp.status_code == 200
    events = _parse_events(resp.text)
    steps = [e for e in events if e["type"] == "step"]
    assert steps and steps[0]["tool"] == "concept_detail"
    done = events[-1]
    assert done["mode"] == "agent"
    assert any(e["type"] == "delta" for e in events)


def test_agent_stream_fallback_without_llm(monkeypatch):
    _no_llm_env(monkeypatch)
    resp = client.post("/api/agent/chat/stream", json={"question": "哪些产品受存款保险保障？"})
    events = _parse_events(resp.text)
    assert events[-1]["mode"] == "fallback"
    assert all(e["type"] != "step" for e in events)


@pytest.mark.parametrize("endpoint", ["/api/chat/stream", "/api/agent/chat/stream"])
def test_stream_empty_question_rejected(monkeypatch, endpoint):
    monkeypatch.setattr(llm_module, "stream_complete", lambda *a, **k: iter([]))
    resp = client.post(endpoint, json={"question": "   "})
    assert resp.status_code == 422


# ---------------------------------------------------------------- SPA files --

def test_index_html_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "银行概念知识库 · AI 助手" in resp.text
    assert resp.headers["content-type"].startswith("text/html")


def test_static_assets_served():
    for path, fragment in (("/style.css", "--sidebar-w"), ("/app.js", "runAnswer")):
        resp = client.get(path)
        assert resp.status_code == 200
        assert fragment in resp.text


def test_api_docs_still_available():
    assert client.get("/docs").status_code == 200
    assert client.get("/api/health").status_code == 200
