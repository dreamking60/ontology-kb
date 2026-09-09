## Context

Phase 3 builds on the archived phase-2 change (`2026-09-09-rag-concept-qa`): a FastAPI + Streamlit app over an rdflib concept KB, with semantic search, provenance-tagged reasoning, and a single-turn RAG chat (`/api/chat`, specs/rag-question-answering). The new capability is a **bounded, tool-calling LLM agent** over read-only KB tools. User decisions: archive phase 2 first (done), and shape = tool-calling Q&A agent (not a heavier planning/self-reflection agent, not an external agent framework). Behavior is specified in `specs/agentic-question-answering/spec.md`.

Constraints: no new runtime dependencies; same `BANKING_KB_LLM_*` env config; read-only tools only; graceful degradation at every layer (no tools support → phase-2 synthesis → deterministic fallback); inspectable step trace; everything testable with a fake tool-calling LLM.

## Goals / Non-Goals

**Goals:**

- An LLM agent that decides tool usage per question, over a **read-only** registry: `search_concepts`, `concept_detail`, `browse_tree`, `reasoning_demo`, `sparql_query`.
- OpenAI-compatible function calling (`tools` / `tool_calls` protocol) reusing the existing env-configured client.
- Bounded loop (max iterations), robust to tool errors, with an explicit exhausted-budget answer.
- New `POST /api/agent/chat` contract with an inspectable `trace`; Agent-mode toggle in the existing chat UI.
- Deterministic tests using an injected fake LLM that scripts tool calls.

**Non-Goals:**

- No web/OS/file/external tools — the agent operates only on this KB.
- No planning/self-reflection frameworks, no agent memory beyond `history`, no persistent sessions.
- No dataset writes: SPARQL tool is SELECT/ASK-only with hard caps; nothing persists (in-memory graph is authoritative anyway).
- No streaming in this change.

## Decisions

### D1: Agent loop = tools protocol + bounded turns

Loop (max `MAX_AGENT_TURNS`, default 8): call the LLM with messages + tool schemas; if the response carries `tool_calls`, execute each against the read-only registry, append `role: "tool"` results, and repeat; if it carries final content without tool calls, stop. On budget exhaustion, synthesize a final message stating more steps are needed. Tool errors are returned as ordinary tool-result text so the loop never crashes.

- **Why**: the smallest faithful "agent" that is still deterministic to test and safe to demo; matches the chosen shape.
- **Alternatives considered**: LangGraph/CrewAI-style frameworks (extra deps + orchestration complexity — rejected); ReAct-style free-text tool syntax (brittle vs native `tool_calls`).

### D2: Tool registry is a thin read-only layer over existing modules

`tools.py` exposes `{name: (schema, callable)}`. Callables reuse `search`/`kb.concept_detail`/`kb.tree`/`reasoning.run_reasoning_demo`/`rag.retrieve` and return short human-readable text plus any concept IRIs they touched (used for citations). No new query logic lives in the agent.

- **Why**: keeps agent and knowledge logic decoupled; tests exercise the same code paths as the phase-1/2 APIs.
- **Alternatives considered**: an agent wrapping the HTTP API (extra serialization round trips and an HTTP dependency inside the server — rejected).

### D3: SPARQL tool is gated read-only

`sparql_query` accepts only statements whose first keyword is `SELECT` or `ASK` (case-insensitive, whitespace-tolerant), rejects mutation keywords (`INSERT`, `DELETE`, `LOAD`, `CLEAR`, `DROP`, `MOVE`, `COPY`, `CREATE`), caps result rows (50), query length (2000 chars), and execution time (5s). It runs against the in-memory graph only; the graph is never written regardless.

- **Why**: lets the agent answer set-style questions ("which products have X") with exact semantics while making mutation impossible by construction.
- **Alternatives considered**: no SPARQL tool (agent limited to keyword retrieval — rejected: set questions need exact queries); a full write-capable query surface (rejected: read-only is a hard boundary).

### D4: LLM client gains a tools path with two-step degradation

`llm.py` adds `complete_with_tools(messages, tools)` returning a structured result `(content, tool_calls)` or `None`. Callers degrade in this order:

1. tools request succeeds → `mode: "agent"`;
2. endpoint rejects `tools` (HTTP 400 etc.) → retry once as a plain phase-2 RAG synthesis → `mode: "llm"`;
3. unconfigured or call failure → deterministic retrieval summary → `mode: "fallback"`.

- **Why**: banks may route to models/gateways without function calling; every rung is a working answer, never an error.
- **Alternatives considered**: hard-failing when tools unsupported (rejected by the spec).

### D5: Response contract and trace

`POST /api/agent/chat` returns `{answer, mode, citations, trace, retrieval_summary}`. `trace` entries: `{step, tool, arguments, summary}` (arguments truncated to ~300 chars each; trace capped at the turn budget). Citations accumulate from tool results that reference concepts (deduplicated). The UI Agent-mode toggle renders the answer, mode badge, citations, and an expandable step trace.

- **Why**: the trace makes the agent's reasoning inspectable — the point of embedding an agent in a demo for bank staff.
- **Alternatives considered**: hiding the loop (opaque answers — rejected for a demo whose value is transparency).

## Risks / Trade-offs

- [Model/gateway lacks tool-calling] → D4 degradation to phase-2 RAG; documented.
- [Loop cost/latency/runaway] → turn budget (8), tool-result truncation, per-tool timeouts, exhausted-budget answer.
- [SPARQL injection/abuse] → SELECT/ASK-only gate + mutation keyword rejection + length/row/time caps; graph is never persisted.
- [Hallucinated final claims] → grounding system prompt + citations derived from actually-executed tool results + visible trace.
- [Fake-tool test determinism] → tests inject a scripted fake LLM rather than mocking network JSON shapes.
- [Prompt-injection via corpus content] → corpus is public/generic; system prompt keeps tool choice inside the registry.

## Migration Plan

Additive to the running app: implement `tools.py` + `agent.py` with unit tests, extend `llm.py`, add the endpoint + tests, add the UI toggle, update docs, then `make test` and demo in all three modes (fallback / llm / agent with a key). Rollback: revert the commit; phase-1/2 endpoints and `/api/chat` are untouched.

## Open Questions

- Default iteration budget (8) — tunable via module constant or env later without contract change.
- Whether a future phase exposes the trace/agent plan through a separate "research mode" endpoint (would extend the contract — new change).
- Result-row and token caps for tool outputs (start at 50 rows / ~300 chars per trace entry; adjust after real-model trials).
