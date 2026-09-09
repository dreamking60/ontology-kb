## 1. Runtime LLM configuration store (llm.py)

- [ ] 1.1 Add a process-level runtime store consulted before env vars in `read_llm_config()` (runtime wins over env), with `set_runtime_config(base_url, api_key, model)` and `clear_runtime_config()`; verify unit tests for runtime-wins, clear-restores-env, and invalid (blank) triples rejected
- [ ] 1.2 Add `llm.stream_complete(messages, config, http)` returning a chunk iterator over OpenAI-compatible streaming (parse `data:` lines and `[DONE]`) or `None` when unconfigured; verify with a mocked httpx stream (fake content chunks), a non-stream JSON fallback path, and an HTTP error → `None`

## 2. Streaming generators

- [ ] 2.1 Add `rag.stream_answer(...)` generator yielding SSE event dicts (`meta` mode, `delta` text, `citations`, `done`) reusing retrieval/passages/fallback helpers; verify: no-LLM → single fallback event set; LLM mode streams deltas then citations; provider failure mid-stream → graceful fallback finish
- [ ] 2.2 Add `agent.stream_agent(...)` generator mirroring the bounded loop and yielding `step` events per executed tool plus final `delta`/`citations`/`done`; verify with scripted fake tool-calling turns (steps visible, budget exhaustion still emits done)

## 3. API surface (api.py)

- [ ] 3.1 Add `GET/POST/DELETE /api/config` (masked reads, runtime store); verify contract tests: POST then GET shows masked key, DELETE clears, blank values → 422, key never appears in responses
- [ ] 3.2 Add `POST /api/chat/stream` and `POST /api/agent/chat/stream` returning `text/event-stream`; verify no-key request yields a complete event set (mode fallback) and empty question → 422; verify streaming happy path with injected fake stream provider
- [ ] 3.3 Mount `ui/static` at `/` (after API routes) so `GET /` serves the SPA; verify `/api/health` and docs still resolve and `GET /` returns the index HTML

## 4. Frontend SPA

- [ ] 4.1 Build `ui/static/index.html` with hash-routed views (chat/explore/reason/settings), sidebar nav + LLM status card, chat composer, and message template hooks; verify served HTML loads in a browser context and routes render without console errors
- [ ] 4.2 Build `ui/static/style.css` — DeepSeek-Harness-inspired chat look (sidebar, bubbles, markdown styles, code blocks, mode chips, citation chips, tool-trace timeline, empty-state suggestions, responsive); verify visual pass in light + dark
- [ ] 4.3 Build `ui/static/app.js` — chat flow using the streaming endpoints (progressive rendering, mode badge, citations chips, collapsible tool trace, suggestion chips), explore view (search + tree + detail via existing endpoints), reasoning view, settings view (config GET/POST/DELETE, masked status, no-key explanation); verify manual end-to-end flow with no key (fallback) and with a fake configured provider
- [ ] 4.4 Remove `ui/app.py` (Streamlit) and drop `streamlit`/`requests` from requirements; update `Makefile` (`ui` target opens `http://127.0.0.1:8000`, keep `api`) and README/demo-script entry points; verify `make api` alone serves the UI and old Streamlit references are gone

## 5. Tests and integration

- [ ] 5.1 Add/complete tests for config endpoints, stream endpoints, and generators (fake provider streams); verify `make test` green with all phase-1..4 tests unchanged
- [ ] 5.2 Run `make load`, `make check-alignment`, HermiT consistency gate, and `openspec validate --specs --strict`; verify all delta scenarios and unchanged capability specs are met
- [ ] 5.3 Manual smoke of the served SPA endpoints (`GET /`, config round-trip masked, chat stream with no key) and update `docs/demo-script.md` with the new UI flow
