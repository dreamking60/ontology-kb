"""LLM provider for the RAG question-answering capability (rag-concept-qa).

Configuration comes purely from environment variables, read at request time:

- ``BANKING_KB_LLM_BASE_URL``  e.g. https://api.deepseek.com/v1  (OpenAI-compatible)
- ``BANKING_KB_LLM_API_KEY``
- ``BANKING_KB_LLM_MODEL``     e.g. deepseek-chat

When any variable is missing, or the endpoint call fails (network/timeout/HTTP
error), :func:`complete` returns ``None`` so the caller degrades to the
deterministic fallback answer — the demo never hard-fails on LLM availability.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx

ENV_BASE_URL = "BANKING_KB_LLM_BASE_URL"
ENV_API_KEY = "BANKING_KB_LLM_API_KEY"
ENV_MODEL = "BANKING_KB_LLM_MODEL"
REQUEST_TIMEOUT_SECONDS = 30.0


class LLMConfig:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model


def read_llm_config() -> Optional[LLMConfig]:
    """Return the configured LLM endpoint, or ``None`` if not fully configured."""
    base_url = os.getenv(ENV_BASE_URL, "").strip().rstrip("/")
    api_key = os.getenv(ENV_API_KEY, "").strip()
    model = os.getenv(ENV_MODEL, "").strip()
    if not (base_url and api_key and model):
        return None
    return LLMConfig(base_url=base_url, api_key=api_key, model=model)


def complete(
    messages: list[dict],
    config: Optional[LLMConfig] = None,
    http: Optional[httpx.Client] = None,
) -> Optional[str]:
    """Call the OpenAI-compatible chat endpoint and return the assistant text.

    Returns ``None`` when unconfigured or on any request/parse failure.
    """
    cfg = config if config is not None else read_llm_config()
    if cfg is None:
        return None
    url = f"{cfg.base_url}/chat/completions"
    payload = {"model": cfg.model, "messages": messages, "temperature": 0.2}
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    try:
        if http is None:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                data = _post_json(client, url, payload, headers)
        else:
            data = _post_json(http, url, payload, headers)
    except Exception:
        # Unconfigured, unreachable, unauthorized, or malformed -> degrade.
        return None
    if data is None:
        return None
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


class ToolCall:
    """One function call requested by the model."""

    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.id = call_id
        self.name = name
        self.arguments = arguments


class ChatTurn:
    """A model response that either carries final content or requests tools."""

    def __init__(self, content: Optional[str], tool_calls: list[ToolCall]) -> None:
        self.content = content
        self.tool_calls = tool_calls

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


def complete_with_tools(
    messages: list[dict],
    tools: list[dict],
    config: Optional[LLMConfig] = None,
    http: Optional[httpx.Client] = None,
) -> Optional[ChatTurn]:
    """Call the chat endpoint with the function-calling ``tools`` parameter.

    Returns a :class:`ChatTurn`, or ``None`` on unconfigured/request failure.
    """
    cfg = config if config is not None else read_llm_config()
    if cfg is None:
        return None
    url = f"{cfg.base_url}/chat/completions"
    payload = {
        "model": cfg.model,
        "messages": messages,
        "temperature": 0.2,
        "tools": tools,
        "tool_choice": "auto",
    }
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }
    try:
        if http is None:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                data = _post_json(client, url, payload, headers)
        else:
            data = _post_json(http, url, payload, headers)
    except Exception:
        return None
    if data is None:
        return None
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        return None
    content = message.get("content")
    tool_calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        tool_calls.append(
            ToolCall(
                call_id=call.get("id") or f"call_{len(tool_calls)}",
                name=str(function.get("name", "")),
                arguments=str(function.get("arguments", "") or "{}"),
            )
        )
    return ChatTurn(content=content, tool_calls=tool_calls)


def _post_json(client: httpx.Client, url: str, payload: dict, headers: dict) -> Optional[dict]:
    response = client.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()
