"""FastAPI application exposing the MVP query surfaces (design.md D4).

Endpoints
---------
GET  /api/health            — dataset status
GET  /api/concepts?q=...    — semantic search with hierarchy expansion
GET  /api/tree              — class-hierarchy browse tree
GET  /api/concepts/{id}     — concept detail (class or individual)
POST /api/reasoning/demo    — provenance-tagged reasoning demo
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from . import agent, llm, rag, reasoning
from .kb import KnowledgeBase
from .search import search

kb = KnowledgeBase()

app = FastAPI(
    title="Banking Concept Knowledge Base (MVP)",
    description="Ontology-driven banking business/product concept KB demo "
    "(banking-concept-kb-mvp).",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReasoningRequest(BaseModel):
    """Placeholder body for POST /api/reasoning/demo (no parameters today)."""


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] | None = None

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be empty")
        return value


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "triples": kb.triple_count()}


@app.get("/api/concepts")
def concepts(q: str = "") -> dict:
    results = search(kb, q)
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/concepts/{identifier}")
def concept_detail(identifier: str) -> dict:
    uri = kb.resolve(identifier)
    if uri is None:
        raise HTTPException(status_code=404, detail=f"Concept not found: {identifier}")
    detail = kb.concept_detail(uri)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Concept not found: {identifier}")
    return detail


@app.get("/api/tree")
def tree() -> dict:
    return {"roots": kb.tree()}


@app.post("/api/reasoning/demo")
def reasoning_demo(_: ReasoningRequest | None = None) -> dict:
    return reasoning.run_reasoning_demo(kb)


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    """RAG question answering over the knowledge base (specs/rag-question-answering)."""
    history = (
        [{"role": m.role, "content": m.content} for m in request.history]
        if request.history
        else None
    )
    return rag.answer_question(kb, request.question, history=history)


@app.post("/api/agent/chat")
def agent_chat(request: ChatRequest) -> dict:
    """Tool-calling agent question answering (specs/agentic-question-answering)."""
    history = (
        [{"role": m.role, "content": m.content} for m in request.history]
        if request.history
        else None
    )
    return agent.run_agent_question(kb, request.question, history=history)


# --------------------------------------------------------------------------- #
# Runtime LLM configuration (settings UI) and SSE streaming (chat-interface)
# --------------------------------------------------------------------------- #

class ConfigPayload(BaseModel):
    base_url: str
    api_key: str
    model: str


@app.get("/api/config")
def get_config() -> dict:
    return llm.config_status()


@app.post("/api/config")
def post_config(payload: ConfigPayload) -> dict:
    try:
        llm.set_runtime_config(payload.base_url, payload.api_key, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return llm.config_status()


@app.delete("/api/config")
def delete_config() -> dict:
    llm.clear_runtime_config()
    return llm.config_status()


def _sse(events: Iterator[dict]) -> Iterator[str]:
    for event in events:
        payload = json.dumps(event, ensure_ascii=False)
        yield f"event: {event.get('type', 'message')}\ndata: {payload}\n\n"


def _chat_history(request: ChatRequest) -> list[dict] | None:
    return (
        [{"role": m.role, "content": m.content} for m in request.history]
        if request.history
        else None
    )


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """SSE streaming RAG chat (specs/chat-interface)."""
    history = _chat_history(request)
    events = rag.stream_answer(kb, request.question, history=history)
    return StreamingResponse(
        _sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/agent/chat/stream")
def agent_chat_stream(request: ChatRequest) -> StreamingResponse:
    """SSE streaming agent chat (specs/chat-interface)."""
    history = _chat_history(request)
    events = agent.stream_agent(kb, request.question, history=history)
    return StreamingResponse(
        _sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------- #
# Static SPA (served at /) — registered last so /api/* routes win.
# --------------------------------------------------------------------------- #

_UI_DIR = Path(__file__).resolve().parents[2] / "ui" / "static"
if _UI_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")
