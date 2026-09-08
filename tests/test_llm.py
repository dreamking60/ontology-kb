"""Provider client tests for src/banking_kb/llm.py (design.md D2)."""
from __future__ import annotations

import httpx
import pytest
from httpx import MockTransport

from banking_kb import llm

CFG = llm.LLMConfig(base_url="https://llm.example/v1", api_key="secret", model="demo-model")


def test_unconfigured_returns_none(monkeypatch):
    for var in (llm.ENV_BASE_URL, llm.ENV_API_KEY, llm.ENV_MODEL):
        monkeypatch.delenv(var, raising=False)
    assert llm.complete([{"role": "user", "content": "hi"}]) is None


def test_configured_success_returns_content():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://llm.example/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "answer"}}]}
        )

    with httpx.Client(transport=MockTransport(handler)) as http:
        result = llm.complete(
            [{"role": "user", "content": "hi"}], config=CFG, http=http
        )
    assert result == "answer"


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_error_returns_none(status):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="err")

    with httpx.Client(transport=MockTransport(handler)) as http:
        assert llm.complete([{"role": "user", "content": "hi"}], config=CFG, http=http) is None


def test_malformed_response_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    with httpx.Client(transport=MockTransport(handler)) as http:
        assert llm.complete([{"role": "user", "content": "hi"}], config=CFG, http=http) is None
