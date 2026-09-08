## Context

Phase 2 extends the archived phase-1 MVP (`2026-09-09-banking-concept-kb-mvp`) — an ontology-driven banking concept KB with an rdflib graph, semantic search (`search.py`), and provenance-tagged reasoning. Main specs live in `openspec/specs/`. The new capability is natural-language Q&A grounded in that KB. User decisions: RAG shape (retrieval → optional LLM synthesis with citations), OpenAI-compatible LLM backend driven by environment variables with a no-key fallback, and integration into the existing FastAPI + Streamlit app in this repository.

Constraints: no new runtime dependencies (HTTP via existing `httpx`); no embedding stack for the MVP retriever; no keys or internal data in the repo; answers must stay grounded and honest (not-found instead of hallucination); behavior is specified in `specs/rag-question-answering/spec.md`.

## Goals / Non-Goals

**Goals:**

- Deterministic, dependency-free retrieval over the existing graph (labels, synonyms, definitions, attributes, hierarchy).
- Provider-agnostic LLM synthesis (OpenAI chat-completions schema over any compatible base URL).
- Graceful degradation: no key / endpoint error ⇒ structured `fallback` answer, never a 500.
- Grounded answers with machine-readable citations (concept id + label) and explicit not-found responses.
- Single new surface on the existing app: `POST /api/chat` + a Chat tab in Streamlit.

**Non-Goals:**

- No new corpus, news/company data, or outside-knowledge lookup (that is future content work, not this change).
- No NL2SPARQL or tool-calling/query routing (recorded as a future option).
- No streaming, no authentication, no usage metering in this change.
- No persistent conversation store (history is passed client-side, ephemeral).

## Decisions

### D1: Retriever = anchor match + context expansion (no embeddings)

Retrieval is two-stage over the existing rdflib graph:

1. **Anchor concepts** — reuse `search()` label/synonym matching for the entities the question names (e.g. 大额存单, 定存 → 定期存款).
2. **Expansion + ranking** — for the anchors, and when no anchor matches, score every candidate concept by overlap between the question and its "concept text" (labels + synonyms + definition + attribute labels/values + super/subclass labels). Overlap is token/character-n-gram containment so Chinese questions without spaces still match. Top-ranked concepts (cap 6) become context.

- **Why**: deterministic, instantly testable, zero new dependencies; Chinese needs no tokenizer; fits the small corpus (33 concepts).
- **Alternatives considered**: dense embeddings (sentence-transformers + vector store) — better paraphrase recall but adds model downloads, memory, and vector-store deps; deferred to an Open Question with a `Retriever` interface seam so it can be swapped in later. BM25 tokenization — poor fit for unsegmented Chinese without a tokenizer.

### D2: LLM client = minimal OpenAI-compatible HTTP client

`src/banking_kb/llm.py` reads `BANKING_KB_LLM_BASE_URL`, `BANKING_KB_LLM_API_KEY`, `BANKING_KB_LLM_MODEL` (read at request time, so tests can flip them). It posts to `{BASE_URL}/chat/completions` with `httpx`, JSON body `{model, messages, temperature}`. Returns the assistant text, or `None` when unconfigured or when the call fails (timeout, HTTP error) — the caller then degrades to `fallback`.

- **Why**: the OpenAI chat-completions schema is the de-facto standard (DeepSeek/OpenAI/Tongyi/Ollama all expose it); one small client instead of pulling the `openai` SDK.
- **Alternatives considered**: full `openai` SDK (extra dep, same wire format); direct vendor SDKs (lock-in).

### D3: Grounding discipline and citations

Every chat answer is assembled from **passages** — one per retrieved concept, each carrying its id, labels, definition, key attributes, and one-line hierarchy context. When an LLM is used, the system prompt instructs it to answer only from the passages and to prefer the question's language; **citations are not parsed from free text** — the response cites exactly the concepts whose passages were included (deterministic provenance), keeping the contract reliable.

- **Why**: robust citation provenance without brittle bracket-parsing; spec scenario "citations reference the concepts the answer actually used" holds by construction.
- **Trade-off**: the citation list is at passage granularity (which concepts grounded the prompt), not per-sentence claim attribution — acceptable for the demo, noted in the docs.

### D4: Fallback answer builder and not-found handling

When no LLM is configured or the call fails: `mode = "fallback"`. If concepts matched, the answer is a deterministic summary — one bullet per matched concept: label, definition, key attributes, hierarchy line — citing exactly those concepts. If nothing matched: `mode = "fallback"`, answer is the fixed not-found message, citations empty, and the LLM is never called.

- **Why**: mirrors the spec's "degrade, don't fail" and "refuse, don't invent" requirements; keeps the demo fully usable with zero keys.
- **Alternatives considered**: hard error when no key — rejected (spec requires graceful degradation).

### D5: Surface shape

- `POST /api/chat` body `{question, history?}` (pydantic: `question` stripped non-empty ⇒ 422 on empty/whitespace), response `{answer, mode, citations, context, retrieval_summary}`. History (last ≤ 6 turns) is forwarded to the LLM for continuity; retrieval and fallback stay per latest question.
- UI: new Chat tab in `ui/app.py` with `st.chat_message` rendering, mode badge, and an expander listing source concepts that link to their detail.

## Risks / Trade-offs

- [Hallucination despite grounding] → constrained system prompt, deterministic citation list, and explicit not-found path; acceptance tests pin the out-of-corpus case.
- [Paraphrase recall limited without embeddings] → synonym coverage in the ontology plus n-gram overlap; a `Retriever` seam keeps dense retrieval as a drop-in later.
- [Key leakage / compliance] → env-only config, `.env` git-ignored, only `.env.example` committed, README warns about outbound calls.
- [Provider flakiness/latency] → request-timeout (30s) and error ⇒ `fallback`, so the demo never hangs or 500s.
- [N-gram overlap false positives on short Chinese queries] → minimum-overlap threshold and anchor-match priority; tests cover negative cases.
- [UI/API drift from spec] → the Chat-tab and endpoint contract are covered by the same tests as the capability spec scenarios.

## Migration Plan

No migration: this change adds a surface to the running phase-1 app. Rollout: (1) implement `rag.py` + `llm.py` with unit tests, (2) wire `/api/chat` + tests, (3) Chat tab, (4) `.env.example`/docs, (5) run `make test` and the demo script in both modes (no key, then with a key). Rollback: revert the commit; phase-1 endpoints/UI are untouched by this change.

## Open Questions

- Dense-embedding retriever upgrade later (interface seam only; no behavior change now).
- Streaming responses and persistent chat sessions (future, would extend the contract — new change).
- If a specific internal model gateway is mandated later, only `llm.py`'s endpoint details change.
