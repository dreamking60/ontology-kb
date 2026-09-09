"""Tool-calling LLM path tests (design.md D4)."""
from __future__ import annotations

import httpx
from httpx import MockTransport

from banking_kb import llm

CFG = llm.LLMConfig(base_url="https://llm.example/v1", api_key="k", model="m")
TOOLS = [{"type": "function", "function": {"name": "f", "parameters": {"type": "object"}}}]
MESSAGES = [{"role": "user", "content": "hi"}]


def test_content_only_turn():
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.read().decode("utf-8"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "final"}}]})

    with httpx.Client(transport=MockTransport(handler)) as http:
        turn = llm.complete_with_tools(MESSAGES, TOOLS, config=CFG, http=http)
    assert turn is not None and turn.content == "final" and not turn.has_tool_calls
    assert '"tools"' in captured[0] and '"tool_choice":"auto"' in captured[0]


def test_tool_calls_turn():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "search_concepts",
                                                "arguments": '{"term": "存款"}'},
                                }
                            ],
                        }
                    }
                ]
            },
        )

    with httpx.Client(transport=MockTransport(handler)) as http:
        turn = llm.complete_with_tools(MESSAGES, TOOLS, config=CFG, http=http)
    assert turn is not None and turn.has_tool_calls
    call = turn.tool_calls[0]
    assert call.id == "call_1" and call.name == "search_concepts"


def test_http_error_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="tools unsupported")

    with httpx.Client(transport=MockTransport(handler)) as http:
        assert llm.complete_with_tools(MESSAGES, TOOLS, config=CFG, http=http) is None


def test_malformed_response_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{}]})

    with httpx.Client(transport=MockTransport(handler)) as http:
        assert llm.complete_with_tools(MESSAGES, TOOLS, config=CFG, http=http) is None
