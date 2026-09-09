## Why

Phase 2 (`rag-concept-qa`, archived) answers a single question with one retrieve-then-generate pass. Questions that genuinely need several knowledge operations — "列出所有受存款保险保障的存款产品，并对比示例大额存单与示例一年期定期存款的期限" — cannot be answered reliably by a single retrieval: they need chained retrieval, structured querying, and optionally reasoning, decided *as the question is being answered*. Embedding a **tool-calling agent** lets the LLM choose which knowledge-base operations to run, observe their results, and iterate until it can synthesize a grounded final answer.

## What Changes

- Add an **agent loop** that lets an OpenAI-compatible LLM call knowledge-base tools iteratively (up to a bounded number of turns) and then produce a final, grounded answer.
- Add a **read-only tool registry** over the existing KB:
  - `search_concepts(term)` — semantic concept search (reuses phase-1/2 retrieval),
  - `concept_detail(identifier)` — full detail for a class or individual,
  - `browse_tree(root)` — class-hierarchy subtrees,
  - `reasoning_demo()` — provenance-tagged inference facts,
  - `sparql_query(query)` — **read-only** SELECT/ASK queries against the in-memory rdflib graph (row/char/time caps; mutation keywords rejected).
- Extend the OpenAI-compatible client to support the chat `tools` protocol (function calling); when the configured model rejects the `tools` parameter, the agent **degrades to the phase-2 single-turn RAG synthesis** instead of failing.
- New endpoint `POST /api/agent/chat` `{question, history?}` → `{answer, mode, citations, trace, retrieval_summary}`; empty question → 422 without calling the LLM. `trace` lists every executed tool step so the reasoning is inspectable.
- UI: the 智能问答 tab gains an **Agent 模式** toggle that calls the new endpoint and shows the step trace under the answer.
- No new runtime dependencies; same `BANKING_KB_LLM_*` environment configuration as phase 2; no keys or internal data committed.

## Capabilities

### New Capabilities

- `agentic-question-answering`: Multi-step, tool-calling question answering over the concept knowledge base — a bounded LLM agent loop over read-only KB tools (search, detail, browse, reasoning, read-only SPARQL) that synthesizes a grounded final answer with an inspectable tool trace, degrades to phase-2 RAG synthesis when the model lacks tool-calling, and to a deterministic retrieval summary when no LLM is configured.

### Modified Capabilities

_(none — phase 3 adds a new capability and does not change the behavior contracts in `openspec/specs/`)_

## Impact

- **Code**: `src/banking_kb/tools.py` (tool registry + read-only SPARQL gate), `src/banking_kb/agent.py` (loop + assembly); `llm.py` gains a tool-calling path; `api.py` gains `POST /api/agent/chat`; `ui/app.py` gains the Agent-mode toggle. Phase-1/2 modules (`kb`, `search`, `rag`, `reasoning`, `llm`) are reused, not rewritten.
- **API contract**: see What Changes; response adds `trace` and new `mode` values (`agent` | `llm` | `fallback`).
- **Environment**: unchanged (`BANKING_KB_LLM_*`); docs updated.
- **Safety boundary**: tools are strictly read-only over the in-memory graph; the SPARQL tool rejects mutation statements; the agent has no web/OS/file tools; iteration is bounded; answers stay grounded in KB content.
