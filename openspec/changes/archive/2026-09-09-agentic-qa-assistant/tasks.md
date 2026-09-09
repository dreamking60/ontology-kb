## 1. Read-only tool registry (tools.py)

- [x] 1.1 Implement `src/banking_kb/tools.py` with a registry of `{name: (schema, callable)}` for `search_concepts`, `concept_detail`, `browse_tree`, `reasoning_demo`, and `sparql_query`, each reusing existing modules and returning short human-readable text plus touched concept IRIs; verify a driver test can invoke every tool and gets a non-empty summary
- [x] 1.2 Implement the read-only SPARQL gate: allow only `SELECT`/`ASK` (case-insensitive first keyword), reject mutation keywords, cap rows (50), query length (2000), and runtime (5s); verify tests cover a valid SELECT, an ASK, and rejections of INSERT/DELETE/LOAD/CLEAR with no graph change
- [x] 1.3 Truncate tool summaries to bounded text (per design D3/D5); verify long result sets (e.g. `SELECT ?s WHERE {?s ?p ?o}` capped at 50 rows) do not exceed the cap

## 2. Tool-calling LLM path (llm.py)

- [x] 2.1 Extend `llm.py` with `complete_with_tools(messages, tools)` returning a structured `(content, tool_calls)` result or `None`; verify mocked-transport tests cover a content-only response, a tool_calls response, an HTTP error → `None`
- [x] 2.2 Support the two-step degradation call (retry without tools when the endpoint rejects the `tools` parameter); verify a 400-on-tools transport falls back to a plain completion result

## 3. Agent loop (agent.py)

- [x] 3.1 Implement the bounded agent loop with max-turns budget, tool execution against the registry, `role: "tool"` result injection, and termination on final content; verify with a scripted fake LLM that a two-tool question executes both tools and returns a final answer with citations and a trace of ≥ 2 steps
- [x] 3.2 Implement exhausted-budget handling: when a fake LLM requests tools every turn, the loop stops at the budget and the answer states the step limit was reached; verify no infinite loop and the trace length equals the budget
- [x] 3.3 Implement tool-error tolerance (error text returned to the LLM as a normal tool result) and citation accumulation (dedup concept IRIs from executed tool results); verify tests for an invalid SPARQL tool call and for deduplicated citations

## 4. Endpoint

- [x] 4.1 Add `POST /api/agent/chat` to `api.py` (pydantic body `{question, history?}`, stripped non-empty → 422); verify empty/whitespace question returns 422 without calling the LLM
- [x] 4.2 Add contract tests: no-key → `mode` `fallback` with contract fields; injected fake tool-calling LLM → `mode` `agent` with `answer`, `citations`, and a non-empty `trace`; injected no-tools LLM → `mode` `llm`; verify `make test` stays green

## 5. UI Agent mode

- [x] 5.1 Add an Agent-mode toggle to the 智能问答 tab that calls `/api/agent/chat` and renders answer, mode badge, citations, and an expandable step trace; verify manual run in fallback mode and with a fake/no key shows correct fields
- [x] 5.2 Keep normal chat (phase 2 `/api/chat`) fully functional when the toggle is off; verify both modes coexist without state interference

## 6. Configuration and docs

- [x] 6.1 Update `.env.example`/README with the agent mode, tool list, degradation ladder (`agent` → `llm` → `fallback`), and read-only guarantees; verify no new required variables were introduced
- [x] 6.2 Extend `docs/demo-script.md` with `/api/agent/chat` examples (multi-step question, empty-question 422, no-key fallback); verify steps render and are executable

## 7. Integration and acceptance

- [x] 7.1 Run the full pytest suite (phases 1–2 still green + new tools/agent/endpoint tests) and `openspec validate --changes agentic-qa-assistant --strict`; verify both pass
- [x] 7.2 Run the demo end to end: fallback mode (no key), and agent mode with a tool-calling model when a key is available, checking the multi-step question scenario and that the dataset is unchanged after agent runs; verify behavior matches `specs/agentic-question-answering/spec.md` before requesting archive
