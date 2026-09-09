## Why

Phase 1 delivered an ontology-driven concept knowledge base with semantic search, browsing, and provenance-tagged reasoning. Banking staff still have to know what to ask and read raw concept cards. Phase 2 adds a **natural-language question-answering layer (RAG)**: staff can simply ask "大额存单和定期存款有什么区别？" and receive a grounded answer with citations to the underlying concepts — while staying honest when the knowledge base has no answer. See archived change `2026-09-09-banking-concept-kb-mvp` and the synced main specs under `openspec/specs/` for the phase-1 contract this builds on.

## What Changes

- Extend the existing FastAPI app with a chat endpoint (`POST /api/chat`) that answers natural-language questions about the concept knowledge base.
- Add a **retrieval layer** over the existing rdflib graph: anchor concepts by label/synonym matching, then expand context with each concept's definition, attributes, and hierarchy/relationships — no new embedding stack required.
- Add an **optional LLM layer** that is OpenAI-compatible and configured purely by environment variables (`BANKING_KB_LLM_BASE_URL` / `BANKING_KB_LLM_API_KEY` / `BANKING_KB_LLM_MODEL`), so DeepSeek, OpenAI, Tongyi and similar endpoints all work.
- **Graceful no-key degradation**: when no LLM is configured, `/api/chat` still answers with a deterministic retrieval summary (mode `fallback`) instead of failing.
- Answers are **grounded in the KB**: every answer cites the source concepts it used; questions with no matching corpus content get an explicit "not found in the knowledge base" response rather than a made-up answer.
- Extend the Streamlit UI with a **Chat tab** that renders answers, mode badge (LLM vs fallback), and clickable source concepts.
- Add `.env.example` documenting the LLM configuration; no internal data or keys are committed.

## Capabilities

### New Capabilities

- `rag-question-answering`: Natural-language Q&A grounded in the concept knowledge base — retrieval over labels/synonyms/definitions/attributes, optional LLM synthesis via an OpenAI-compatible endpoint, deterministic fallback without an LLM key, answer citations to source concepts, and explicit not-found handling for out-of-corpus questions.

### Modified Capabilities

_(none — phase 2 adds a new surface and does not change the phase-1 behavior contracts in `openspec/specs/`)_

## Impact

- **Code**: new module `src/banking_kb/llm.py` (provider client), `src/banking_kb/rag.py` (retrieval + answer assembly); `api.py` gains `POST /api/chat`; `ui/app.py` gains a Chat tab. Existing `kb.py`, `search.py`, and `reasoning.py` are reused, not rewritten.
- **Dependencies**: none new at runtime (HTTP via existing `httpx`); optional keys via environment only.
- **Config**: `.env.example` + README section documenting `BANKING_KB_LLM_*`; no keys in the repository.
- **API contract**: `POST /api/chat` request `{question, history?}` → response `{answer, mode, citations, context, retrieval_summary}`.
- **Behavior boundary**: the assistant answers only from knowledge-base content (concepts, attributes, relationships, hierarchy); it is not a general financial chatbot and does not call out to company/news data.
