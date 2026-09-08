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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import reasoning
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
