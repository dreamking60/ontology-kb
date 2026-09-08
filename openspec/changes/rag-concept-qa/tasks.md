## 1. Retrieval layer (rag.py)

- [x] 1.1 Implement anchor retrieval in `src/banking_kb/rag.py` that finds concepts via `search()` label/synonym matching for entities named in the question; verify a unit test maps "什么是大额存单？" to the 大额存单 concept and "定存" questions to 定期存款
- [x] 1.2 Implement expansion + ranking: score candidate concepts by question overlap with labels/synonyms/definition/attribute text (character-n-gram containment), cap at 6 concepts, and apply a minimum-overlap threshold; verify ranking tests cover the deposit-comparison question (定期存款 + 活期存款 both retrieved) and a no-match question returns an empty context
- [x] 1.3 Implement passage building: each retrieved concept yields id, labels, definition, key attributes, and a one-line hierarchy context; verify a passage test asserts all fields for a sample concept and that 定存-retrieved 定期存款 passages carry its attributes

## 2. LLM provider (llm.py)

- [x] 2.1 Implement `src/banking_kb/llm.py` reading `BANKING_KB_LLM_BASE_URL`/`_API_KEY`/`_MODEL` at request time and returning `None` when any is missing; verify unit tests for unconfigured → `None` and configured-but-invalid → `None`
- [x] 2.2 Implement the OpenAI-compatible `chat/completions` POST via httpx (JSON messages body, Bearer auth, 30s timeout) returning the assistant text; verify a mocked-transport test returns the expected content and a 401/timeout surfaces as `None` (degradation)

## 3. Answer assembly

- [x] 3.1 Implement the fallback answer builder: deterministic per-concept summary (label, definition, key attributes, hierarchy) with citations exactly matching summarized concepts; verify tests for the known-concept case (mode `fallback`, answer includes the definition text) and the not-found case (fixed message, empty citations)
- [x] 3.2 Implement LLM-synthesis path: system prompt grounded strictly on passages (answer from passages only, prefer the question's language) + user message with passages and question; verify with a fake LLM client that the prompt includes the retrieved passage text and the assembled response returns mode `llm` with deterministic citations
- [x] 3.3 Wire history (last ≤ 6 turns) into the LLM request while keeping retrieval and fallback per latest question; verify a history-carrying unit test passes turns through to the fake client

## 4. API surface

- [x] 4.1 Add `POST /api/chat` to `src/banking_kb/api.py` with pydantic body `{question, history?}` (stripped non-empty); verify empty/whitespace question returns HTTP 422 without calling the LLM
- [x] 4.2 Add API contract tests: no-key environment → 200 with mode `fallback` and contract fields (`answer`, `mode`, `citations`, `context`, `retrieval_summary`); injected fake LLM → 200 mode `llm`; verify `make test` stays green

## 5. UI Chat tab

- [x] 5.1 Add a Chat tab to `ui/app.py` using `st.chat_message`: user question input, assistant answer render, mode badge, and an expander of source concepts; verify manual run shows the chat and the fallback answer when no key is set
- [x] 5.2 Keep a client-side message history and send the last turns with each request; verify repeated questions in the UI show a coherent single-session conversation and no history-related errors

## 6. Configuration and docs

- [x] 6.1 Add committed `.env.example` documenting `BANKING_KB_LLM_BASE_URL`/`_API_KEY`/`_MODEL` with examples (DeepSeek-compatible URL) and a note that `.env` is git-ignored; verify `.env.example` is tracked and `.env` is not
- [x] 6.2 Update `README.md` (chat usage, env vars, grounding/citation and no-key behavior, outbound-call warning) and extend `docs/demo-script.md` with chat examples for both modes; verify markdown renders and demo steps are executable

## 7. Integration and acceptance

- [x] 7.1 Run the full pytest suite (phase-1 specs still green + new rag/llm/api/chat tests) and `openspec validate --changes rag-concept-qa --strict`; verify both pass
- [x] 7.2 Run the demo end to end in no-key mode (fallback answers with citations, not-found for out-of-corpus question) and, if a key is available, in LLM mode; verify behavior matches `specs/rag-question-answering/spec.md` scenarios before requesting archive
