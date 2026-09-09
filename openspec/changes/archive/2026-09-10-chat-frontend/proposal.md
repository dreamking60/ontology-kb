## Why

The knowledge base demo currently exposes a Streamlit tab dashboard. It works, but it does not feel like an AI chat product: no conversational flow, no place to configure the LLM API from the app, and when no API key is configured the UI does not explain what is happening (the agent just answers with a plain block of text). The user wants the frontend overhauled into a **modern, LLM-chat-style web experience** (visual language and interaction modelled on the DeepSeek Harness page), with first-class handling of the "no API configured" state and an in-app way to configure the LLM endpoint.

## What Changes

- **Replace the Streamlit dashboard with a static single-page web app** served by the existing FastAPI server (no Node/build step): an LLM-chat style interface with message bubbles, rendered markdown, typing/thinking affordances, per-message mode badges (`agent`/`llm`/`fallback`), citations, and an agent tool-step timeline; plus an empty-state with suggested questions.
- **Pages/views** (hash-routed, DeepSeek-Harness-like visual language — clean, dark-capable, sidebar navigation, centered chat column): `#/chat` (primary conversation), `#/explore` (concept search + hierarchy tree + detail, preserving the concept-browser/search capabilities), `#/reason` (reasoning demo), `#/settings` (LLM API configuration + status).
- **In-app LLM API configuration**: new endpoints `GET/POST/DELETE /api/config` manage the `BANKING_KB_LLM_*` settings **at runtime** (process-level, never written to disk or logged; GET returns masked values). The Settings view also explains the no-key fallback behaviour.
- **Graceful no-API UX**: when no LLM is configured the app shows a clear status ("未配置 LLM API · 检索摘要模式 mode=fallback"), every chat message carries its mode badge, and a setup hint links to Settings — nothing looks broken.
- **Streaming chat**: new SSE endpoints `POST /api/chat/stream` and `POST /api/agent/chat/stream` stream content deltas when the LLM is configured (and agent step events as tools execute); when unconfigured or the provider fails they degrade to a single fallback event set. Existing `POST /api/chat` and `/api/agent/chat` contracts stay unchanged (backwards compatible).
- Remove the legacy Streamlit app (`ui/app.py`) and its `streamlit`/`requests` dependencies; `make api` becomes the single entry that serves both API and UI; docs/README updated.

## Capabilities

### New Capabilities

- `chat-interface`: The modern LLM-chat web experience — conversation rendering with markdown/bubbles/citations/tool traces and mode badges, an empty state with suggested questions, in-app LLM API configuration with masked status, explicit no-key degradation messaging, and SSE streaming over the existing chat/agent question answering.

### Modified Capabilities

_(none — the redesign is additive to the existing API/behaviour contracts; search, browse, reasoning, chat and agent main specs are unchanged.)_

## Impact

- **Code**: `src/banking_kb/llm.py` (runtime config store + streaming helper), `src/banking_kb/rag.py`/`agent.py` (streaming generators), `src/banking_kb/api.py` (config endpoints, SSE endpoints, static file mount); new `ui/static/index.html`, `ui/static/style.css`, `ui/static/app.js` (self-contained, offline, no build step).
- **Removals**: `ui/app.py` (Streamlit) and its dependencies removed; `Makefile` `ui` target repointed to the API URL.
- **Dependencies**: `streamlit` and `requests` removed from `requirements.txt`; no new runtime dependencies (streaming uses the existing httpx).
- **API additions** (no contract breaks): `GET /api/config`, `POST /api/config`, `DELETE /api/config`, `POST /api/chat/stream`, `POST /api/agent/chat/stream`.
- **Docs**: README + `docs/demo-script.md` updated (UI entry, config-in-app, streaming, no-key flow).
