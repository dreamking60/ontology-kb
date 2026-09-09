# Banking Concept Knowledge Base (MVP)

An ontology-driven **banking business/product concept knowledge base** demo —
part of the OpenSpec change `banking-concept-kb-mvp` in this repository.
Banking staff can look up concepts such as 存款 / 定期存款 / 大额存单, browse the
class hierarchy, and watch OWL reasoning derive facts with full provenance.

## What it is

- **`banking-core` ontology** (OWL2, Turtle): product, account and party
  concept hierarchies with bilingual (中文/English) labels, synonyms and
  definitions, authored for Protégé. **Enriched (ontology-enrichment): 60
  curated concept classes and 34 example individuals** across deposits, loans,
  wealth management, accounts, parties/roles, rate & pricing, and banking
  events.
- **FIBO alignment by annotation only**: `ontology/fibo-alignment.ttl` maps
  selected classes to FIBO terms **verified against a pinned FIBO snapshot**
  (see `docs/fibo-alignment.md` + `docs/reference/`); FIBO itself is never
  imported.
- **Semantic search** with hierarchy expansion and synonym matching
  (specs/concept-search), **tree browser** (specs/concept-browser), a
  **reasoning demo** with `asserted` / `inferred` / `rule-derived` provenance
  (specs/reasoning-demo), and **RAG question answering** (specs/rag-question-answering):
  natural-language questions over the concept KB with citations, plus a
  deterministic fallback when no LLM is configured.
- **No LLM required for the base demo** — chat degrades gracefully (`mode=fallback`).

## Quick start

```bash
make setup              # python3 -m venv .venv + pip install -r requirements.txt
make load               # parse ontology/ files, print dataset summary
make test               # run spec-scenario pytest suite
make api                # FastAPI on http://127.0.0.1:8000  (keep running)
make ui                 # Streamlit UI on http://127.0.0.1:8501  (keep running)
```

Optional: `make check-consistency` runs a HermiT satisfiability gate
(needs Java); the fallback is Protégé's HermiT tab.

Try: search 存款, 定存, 按揭, `deposit`; browse 产品 → 存款 → 定期存款 → 大额存单;
run the reasoning demo to see 示例十年期定期存款 classified as
长期定期存款（演示分类）by the demo rule. Then open the **智能问答** tab and ask
"大额存单和定期存款有什么区别？" or "什么是信用贷款？".

## RAG question answering (chat)

`POST /api/chat` answers natural-language questions **grounded in the concept
knowledge base** — the answer cites the source concepts it used, and questions
with no matching content get an explicit "not found" response instead of a
made-up answer.

**Without an LLM key** the endpoint still answers via a deterministic retrieval
summary (`"mode": "fallback"`). To enable synthesized answers, export an
OpenAI-compatible endpoint (see `.env.example`):

```bash
export BANKING_KB_LLM_BASE_URL=https://api.deepseek.com/v1   # or any compatible URL
export BANKING_KB_LLM_API_KEY=sk-...                          # never commit this
export BANKING_KB_LLM_MODEL=deepseek-chat
make api
```

> ⚠️ Configuring a key makes the demo **call an external service** with prompt
> text derived from the knowledge base — review data-exit policy before using a
> cloud endpoint in a bank environment. When the call fails, chat degrades to
> `mode=fallback` instead of erroring.

### Agent mode (tool calling)

`POST /api/agent/chat` answers questions that need **several knowledge
operations** — the LLM decides which read-only tools to call (`search_concepts`,
`concept_detail`, `browse_tree`, `reasoning_demo`, `sparql_query`) and iterates
before answering. Every executed step is returned in the `trace`, and citations
reflect the concepts the tools actually touched.

Degradation ladder: tools work → `mode=agent`; model rejects the `tools`
parameter → phase-2 RAG synthesis `mode=llm`; no LLM key → deterministic
summary `mode=fallback`. Tools are strictly read-only (the SPARQL tool only
accepts `SELECT`/`ASK`), the loop is bounded (8 turns), and the dataset is never
modified. Try it in the UI by enabling the **🤖 Agent 模式** toggle.

## Repository layout

```
ontology/               # ontology files (TBox, ABox/corpus, alignment)
src/banking_kb/         # Python package (load, search, reasoning, rules, api)
ui/app.py               # Streamlit demo UI
tests/                  # pytest — one test file per OpenSpec delta spec
docs/                   # fibo-alignment.md, demo-script.md, internal-import.md
openspec/               # OpenSpec specs & changes (source of truth for behavior)
.agents/skills/         # OpenSpec workflow skills
```

## Data policy — no internal bank data

All shipped content (`ontology/*.ttl`) is **public and generic**; every entry
carries a `skos:editorialNote` provenance marker. Internal bank data is
**never** committed: place it in the git-ignored `internal/` directory and load
it explicitly with `make load-internal`. See `docs/internal-import.md`.

## API (local demo)

- `GET /api/health`
- `GET /api/concepts?q=<term>` — semantic search (empty result = HTTP 200 + `[]`)
- `GET /api/tree` — class-hierarchy browse tree
- `GET /api/concepts/{id}` — detail for `Deposit`, `bc:Loan`, `DemoHousingLoan`, …
- `POST /api/reasoning/demo` — provenance-tagged reasoning facts
- `POST /api/chat` — RAG question answering `{question, history?}` → `{answer, mode, citations, context, retrieval_summary}`
- `POST /api/agent/chat` — tool-calling agent QA `{question, history?}` → `{answer, mode, citations, trace, retrieval_summary}`

## Development loop

Behavior is specified in `openspec/changes/banking-concept-kb-mvp/specs/` and
tracked by `tasks.md`. Change specs → re-run `make test`; demo scripts in
`docs/demo-script.md` mirror the spec scenarios.
