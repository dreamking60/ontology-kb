## 1. Project scaffolding

- [x] 1.1 Initialize a git repository at the repo root and add a `.gitignore` (Python venv, `__pycache__`, `internal/`, `.env`); verify `git status` shows a clean tracked set including `openspec/`, `.agents/`, `AGENTS.md`
- [x] 1.2 Create `requirements.txt` (fastapi, uvicorn, rdflib, owlrl, streamlit, requests, pytest, owlready2 for the optional consistency check) and scaffold `src/banking_kb/` with an empty `__init__.py`; verify `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` succeeds
- [x] 1.3 Add a `Makefile` with targets `setup`, `load`, `test`, `api`, `ui`, `check-consistency`; verify `make setup` completes and `make load` reports the ontology files parsed
- [x] 1.4 Add a `README.md` skeleton (what it is, layout, setup/run commands, no-internal-data policy) and `docs/demo-script.md` placeholder; verify both render as expected markdown files

## 2. Core ontology (TBox)

- [x] 2.1 Author `ontology/banking-core.ttl` with the `bc:` namespace and top-level classes 产品/Product, 账户/Account, 主体/Party plus supporting classes (e.g. 利率/Rate); verify the file parses with rdflib and Protégé opens it without errors
- [x] 2.2 Model the deposit hierarchy (存款 → 活期存款/定期存款 → 大额存单) and the loan and wealth-management hierarchies with bilingual `rdfs:label` (@zh/@en) on every class; verify a SPARQL query lists no class missing either label
- [x] 2.3 Define object/datatype properties used by concept cards (e.g. term, minimum amount, liquidity, risk level, offered-by) with domains/ranges within declared entities; verify the structural test (no dangling references) passes
- [x] 2.4 Keep expressivity OWL2-RL-friendly; verify `owlrl` materialization runs without errors on the empty ABox

## 3. Seed corpus and FIBO alignment

- [x] 3.1 Author `ontology/seed-corpora.ttl` with at least 15 public/generic concept cards covering deposits, loans, wealth-management products, accounts, and parties (≥1 per category); verify the coverage test counts ≥15 entries and every category is present
- [x] 3.2 Give every card a definition (`skos:definition`), synonyms for common alternative names (e.g. 定存), and key attribute values; verify the synonym lookup test (定存 → 定期存款) passes
- [x] 3.3 Author `ontology/fibo-alignment.ttl` with `bc:alignedToFibo` annotations for the mapped classes and `docs/fibo-alignment.md` listing each mapping with the FIBO term identifier; verify a sample class returns its alignment annotation via SPARQL
- [x] 3.4 Add the internal-data import convention (git-ignored `internal/` directory, loaded only via an explicit flag) and document it in the README; verify the shipped corpus contains no internal-data markers and provenance notes exist per card

## 4. Knowledge layer and semantic search

- [x] 4.1 Implement `src/banking_kb/kb.py` (load the three ontology files into one rdflib graph, expose SPARQL helpers for superclass/subclass/attributes); verify `make load` builds the dataset and a smoke SPARQL query returns results
- [x] 4.2 Implement `src/banking_kb/search.py` with normalized matching and ranking (exact zh label > synonym > prefix > en label) plus hierarchy expansion in results; verify unit tests cover the four spec scenarios including the no-result case
- [x] 4.3 Implement concept detail assembly (identifier, labels, synonyms, definition, superclass, subclasses, attribute-value pairs, non-hierarchical relationships); verify a detail test returns all fields for a sample concept

## 5. Reasoning demo

- [x] 5.1 Implement `src/banking_kb/reasoning.py` running `owlrl` over the base graph into a separate inference graph, never mutating the base graph; verify a type-propagation test (individual typed 定期存款 also reported as 存款) passes and the base graph triple count is unchanged
- [x] 5.2 Implement `src/banking_kb/rules.py` with the declarative demo rule (e.g. deposit term ≥ 60 months → long-term deposit product) returning rule-tagged triples; verify the rule fires on a crafted seed individual and is tagged `rule-derived`
- [x] 5.3 Assemble demo output with provenance tags (`asserted` | `inferred` | `rule-derived`) for every fact and a rule-text field on rule-derived facts; verify the provenance test assigns exactly one tag per fact
- [x] 5.4 Add `make check-consistency` (HermiT via owlready2 when Java is present; clear "Java missing" message otherwise); verify it reports no unsatisfiable classes on this machine or the documented fallback path works

## 6. JSON API

- [x] 6.1 Implement `src/banking_kb/api.py` (FastAPI) exposing `GET /api/concepts?q=`, `GET /api/tree`, `GET /api/concepts/{id}`, and `POST /api/reasoning/demo`; verify the app starts with uvicorn and each endpoint responds
- [x] 6.2 Add API contract tests for search (including the 200 empty-result case), tree, detail, and reasoning payload shapes; verify `make test` runs them green against a live test client

## 7. Web UI

- [x] 7.1 Implement `ui/app.py` (Streamlit) with a Search panel calling `/api/concepts?q=` and rendering results with hierarchy context; verify manually that 存款 and 定存 return the expected concepts
- [x] 7.2 Add a Browse panel (tree from `/api/tree`, detail from `/api/concepts/{id}`) and a Reasoning panel (`POST /api/reasoning/demo` with provenance labels); verify the demo flow in `docs/demo-script.md` works end to end

## 8. Integration and acceptance

- [x] 8.1 Write/complete pytest coverage for every spec scenario across `specs/knowledge-content`, `specs/concept-search`, `specs/concept-browser`, and `specs/reasoning-demo`; verify `make test` is fully green
- [x] 8.2 Finalize README (setup/run/demo instructions, layout, internal-data import) and `docs/demo-script.md`; verify a fresh clone can follow them to a running demo
- [x] 8.3 Run `openspec validate --changes banking-concept-kb-mvp` and the full demo script; verify all requirements in the four delta specs are demonstrably met before requesting archive
