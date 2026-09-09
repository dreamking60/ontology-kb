## Context

Phases 1–4 delivered an ontology KB with FastAPI (`/api/*`) + a Streamlit dashboard (`ui/app.py`), RAG chat (`/api/chat`), an agent (`/api/agent/chat`), and a verified FIBO-enriched corpus. The new capability (`specs/chat-interface/spec.md`) overhauls the frontend into an LLM-chat product (visual reference: DeepSeek Harness page), adds in-app LLM API configuration, and adds streaming. Environment: Python 3.12 FastAPI app; httpx available; Node is NOT part of the stack; user will not interact during this change.

## Goals / Non-Goals

**Goals:**

- A single FastAPI-served static SPA that looks and behaves like a chat product (bubbles, markdown, mode badges, citations, tool traces, suggestions, settings) and preserves search/browse/reasoning access.
- Runtime, key-safe LLM configuration with masked reads; clear no-key fallback messaging.
- SSE streaming for chat and agent with graceful degradation.
- Legacy Streamlit UI removed; `make api` is the single entry.

**Non-Goals:**

- No Node/npm build pipeline or frontend framework (self-contained static assets only).
- No user accounts, conversation persistence, or multi-user isolation.
- No changes to the existing `/api/chat` and `/api/agent/chat` contracts.
- No server-side persistence of API keys (runtime/process memory only).

## Decisions

### D1: Static SPA served by FastAPI instead of Streamlit

Assets under `ui/static/` (`index.html`, `style.css`, `app.js`) are mounted at `/` (mount registered after all `/api` routes); hash routing (`#/chat`, `#/explore`, `#/reason`, `#/settings`) keeps navigation server-less. The SPA talks only to the existing + new `/api/*` endpoints. Streamlit app and deps are removed.

- **Why**: one process, one URL (`http://127.0.0.1:8000`), zero build tooling, full control of the visual language; Streamlit cannot achieve the requested product look without fighting its chrome.
- **Alternatives**: keeping Streamlit and theming it (limited, still "dashboard-y"); a Vite/React app (heavier toolchain contradicting the no-Node constraint).

### D2: Visual language modelled on the DeepSeek Harness page

Light-first, optional dark, clean chat layout: slim left sidebar (nav + LLM/status card + config shortcut), centered conversation column with bubbles, system-friendly typography, subtle borders/radii, monospace code styling, and an input composer pinned at the bottom with send affordance and suggestion chips in the empty state. CSS variables keep theming cheap. The look is an *inspiration*, not a copy: same product genre (AI chat), original markup/styles.

### D3: Runtime configuration store with masked reads

`llm.py` gains a process-level runtime store (`_RUNTIME = {base_url, api_key, model}`) consulted before env vars; `read_llm_config()` merges runtime → env. New endpoints: `GET /api/config` → `{configured, base_url, model, key_present}` (never the key), `POST /api/config` (validates non-blank triples; also accepts a `clear` semantics via DELETE), `DELETE /api/config`. The Settings view explains env-var persistence (`export BANKING_KB_LLM_*`) for restart persistence.

- **Why**: gives the "agent 没有配置 api 的地方" complaint a real answer without key-on-disk risk or credential plumbing.
- **Alternatives**: writing `.env` (persists keys to disk — rejected); forcing restarts with env vars only (poor UX).

### D4: SSE streaming with graceful degradation

New `POST /api/chat/stream` and `POST /api/agent/chat/stream` return `text/event-stream`. Events: `meta` (mode/status), `delta` (text chunk), `step` (agent tool step), `citations`, `done`. Backend generators: `rag.stream_answer` (reuses retrieval + passages; when configured, calls the new `llm.stream_complete` OpenAI-compatible streaming helper and yields deltas; on any provider failure after start, finishes gracefully with the assembled fallback), and `agent.stream_agent` (mirrors the bounded loop, yielding `step` events as tools execute and final deltas). When unconfigured, both emit a single `meta`+`done` set carrying the deterministic answer. Existing one-shot endpoints stay for compatibility and tests.

- **Why**: "looks like a real LLM chat" is mostly streaming + progressive UI; SSE over POST (ReadableStream via fetch) works without EventSource's GET limitation.
- **Alternatives**: client polling (laggy); WebSockets (extra infra); non-streaming chat (does not meet the product feel).

### D5: Keep legacy behaviour untouched

No changes to `search`/`reasoning`/`rag.answer_question`/`agent.run_agent_question` semantics; streaming code paths are new functions sharing retrieval/rules helpers. Concept search/browse/reasoning features are re-exposed in the SPA (`#/explore`, `#/reason`) using the existing endpoints, so the phase-1..4 capability scenarios remain green unchanged.

## Risks / Trade-offs

- [Streaming provider quirks] → SSE parser tolerant of `data:` framing and `[DONE]`; provider failure degrades to a complete fallback event set (never a hanging stream).
- [Key exposure] → key never returned by config endpoints, never logged; runtime memory only; docs recommend env-var persistence outside the app.
- [Self-contained markdown rendering] → small homegrown renderer (headings/lists/bold/code/links); adequate for KB answers; documented limitation vs full CommonMark.
- [Static-asset regression risk on old browsers] → target evergreen browsers; fetch-stream + modern CSS only.
- [Removing Streamlit breaks muscle memory] → README/demo-script and `make ui` (opens the new URL) updated; old Streamlit endpoints never existed server-side.

## Migration Plan

Served-app swap: add static mount + new endpoints; frontend code lands with `make api`; no data migration. Rollback: revert commit (Streamlit removal is a separate, revertible commit).

## Open Questions

- Dark vs light default theme (default light with CSS variable hooks; user toggles — recorded assumption).
- Whether a future change adds conversation history persistence server-side (would extend the API contract — new change).
