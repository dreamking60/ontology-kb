# Banking Concept Knowledge Base (MVP)

An ontology-driven **banking business/product concept knowledge base** with a
modern **AI-chat web app** — built spec-first under OpenSpec in this repository.
Banking staff can ask natural-language questions (RAG / tool-calling agent),
look up concepts such as 存款 / 定期存款 / 大额存单, browse the class hierarchy,
and watch OWL reasoning derive facts with full provenance.

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
- **Modern LLM-chat web UI** (specs/chat-interface): bubbles + markdown + mode
  badges + citations + agent tool-trace, SSE streaming, in-app LLM API
  configuration with masked reads, and explicit no-key fallback messaging —
  served by the FastAPI server itself (no separate UI process).

## Quick start

```bash
make setup              # python3 -m venv .venv + pip install -r requirements.txt
make load               # parse ontology/ files, print dataset summary
make test               # run spec-scenario pytest suite
make api                # API + web UI on http://127.0.0.1:8000  (keep running)
```

Then open **http://127.0.0.1:8000** in a browser: use **💬 AI 对话** to chat
(standard or 🤖 Agent tool mode), **🔎 概念探索** to search/browse, **🧠 推理演示**
for the reasoner, and **⚙️ 设置** to configure the LLM API from the app.

Optional: `make check-consistency` runs a HermiT satisfiability gate
(needs Java); the fallback is Protégé's HermiT tab.

Try: ask "大额存单和定期存款有什么区别？" or "哪些示例产品受存款保险保障？";
search 存款 / 定存 / 按揭 / LPR; browse 产品 → 存款 → 定期存款 → 大额存单; run the
reasoning demo to see 示例十年期定期存款 classified as 长期定期存款（演示分类）.

## RAG question answering (chat)

`POST /api/chat` answers natural-language questions **grounded in the concept
knowledge base** — the answer cites the source concepts it used, and questions
with no matching content get an explicit "not found" response instead of a
made-up answer.

**Without an LLM key** the endpoint still answers via a deterministic retrieval
summary (`"mode": "fallback"`). To enable synthesized answers, either export an
OpenAI-compatible endpoint (see `.env.example`, persists across restarts):

```bash
export BANKING_KB_LLM_BASE_URL=https://api.deepseek.com/v1   # or any compatible URL
export BANKING_KB_LLM_API_KEY=sk-...                          # never commit this
export BANKING_KB_LLM_MODEL=deepseek-chat
make api
```

…or configure it **inside the app**: open **⚙️ 设置**, fill Base URL / API Key /
Model and click 保存并应用 (runtime-only, masked reads, no key on disk). The web
UI consumes the streaming endpoints (`/api/chat/stream`,
`/api/agent/chat/stream`) and renders answers progressively.

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
src/banking_kb/         # Python package (load, search, reasoning, rag, agent, llm, api)
ui/static/              # web app (index.html / style.css / app.js — no build step)
tests/                  # pytest — one test file per OpenSpec delta spec
docs/                   # fibo-alignment.md, demo-script.md, internal-import.md, reference/
openspec/               # OpenSpec specs & changes (source of truth for behavior)
.agents/skills/         # OpenSpec workflow skills
```

## Data policy — no internal bank data

All shipped content (`ontology/*.ttl`) is **public and generic**; every entry
carries a `skos:editorialNote` provenance marker. Internal bank data is
**never** committed: place it in the git-ignored `internal/` directory and load
it explicitly with `make load-internal`. See `docs/internal-import.md`.

## API (local demo)

- `GET /` — the web app
- `GET /api/health`
- `GET /api/config` · `POST /api/config` · `DELETE /api/config` — runtime LLM config (masked)
- `GET /api/concepts?q=<term>` — semantic search (empty result = HTTP 200 + `[]`)
- `GET /api/tree` — class-hierarchy browse tree
- `GET /api/concepts/{id}` — detail for `Deposit`, `bc:Loan`, `DemoHousingLoan`, …
- `POST /api/reasoning/demo` — provenance-tagged reasoning facts
- `POST /api/chat` — RAG QA `{question, history?}` → `{answer, mode, citations, context, retrieval_summary}`
- `POST /api/chat/stream` — same, as an SSE stream (deltas + citations + done)
- `POST /api/agent/chat` — tool-calling agent QA (one-shot)
- `POST /api/agent/chat/stream` — same, as an SSE stream (step events + deltas)

## OpenSpec skills in every session (global install)

DeepSeek Harness discovers skills from **project roots** (`<project>/.dsh/skills`,
`<project>/.agents/skills`) and **user-global roots** (`$DSH_HOME/skills` →
`~/.dsh/skills`, and `$DSH_AGENTS_HOME/skills` → `~/.agents/skills`). `openspec init
--tools agents` writes project-local skills only, so they would otherwise appear
just in this repository's sessions.

Install them globally — then they are available in every DSH session, any
workspace, any standard mode:

```bash
make install-skills        # copy    → robust, independent of this checkout
make install-skills-link   # symlink → `openspec update` refreshes them automatically
```

- Script: `scripts/install_global_skills.sh`; destination
  `${DSH_AGENTS_HOME:-$HOME/.agents}/skills` (all-session root). `~/.dsh/skills` is
  an equivalent alternative if you prefer DSH-only scoping.
- **Project roots rank higher than user roots**, so a repository's own generated
  skills always win over the global copy with the same name.
- After upgrading OpenSpec (`openspec update` regenerates this repo's skills),
  re-run `make install-skills` to refresh the global copies.
- The global install lives outside the repository and is never committed.

## Development loop

Behavior is specified in `openspec/specs/` (main specs, synced at archive) and
each change's delta specs + `tasks.md`. Change specs → re-run `make test`;
`docs/demo-script.md` mirrors the spec scenarios.
