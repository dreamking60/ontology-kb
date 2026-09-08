# Banking Concept Knowledge Base (MVP)

An ontology-driven **banking business/product concept knowledge base** demo —
part of the OpenSpec change `banking-concept-kb-mvp` in this repository.
Banking staff can look up concepts such as 存款 / 定期存款 / 大额存单, browse the
class hierarchy, and watch OWL reasoning derive facts with full provenance.

## What it is

- **`banking-core` ontology** (OWL2, Turtle): product, account and party
  concept hierarchies with bilingual (中文/English) labels, synonyms and
  definitions, authored for Protégé.
- **FIBO alignment by annotation only**: `ontology/fibo-alignment.ttl` maps
  selected classes to FIBO terms; FIBO itself is never imported.
- **Semantic search** with hierarchy expansion and synonym matching
  (specs/concept-search), **tree browser** (specs/concept-browser), and a
  **reasoning demo** with `asserted` / `inferred` / `rule-derived` provenance
  (specs/reasoning-demo).
- **No LLM/RAG in this phase** — a later OpenSpec change adds it.

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
长期定期存款（演示分类）by the demo rule.

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

## Development loop

Behavior is specified in `openspec/changes/banking-concept-kb-mvp/specs/` and
tracked by `tasks.md`. Change specs → re-run `make test`; demo scripts in
`docs/demo-script.md` mirror the spec scenarios.
