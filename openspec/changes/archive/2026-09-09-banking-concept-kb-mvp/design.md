## Context

Greenfield MVP in an empty repository (`/home/dreamking/ontology`). Motivation and scope: see `proposal.md`. The MVP is an ontology-driven banking business/product concept knowledge base: a self-authored lightweight OWL core ontology aligned to FIBO terminology, a curated public seed corpus, RDF/OWL storage with SPARQL queries, an OWL reasoner plus one configurable demo rule, and a small web UI. Phase 2 (LLM/RAG) is deliberately out of scope. Requirements live in the four delta specs under `specs/`.

Constraints that shape the design:

- Runtime confirmed by the user: **Python-native core** (rdflib + owlrl). Java 21, Docker, and git are available on this machine but must not be mandatory for the demo to run.
- All shipped content is public/generic; no internal bank data.
- Ontology files must remain editable in Protégé (standard OWL2, Turtle/RDF-XML serializations).
- Demo must be locally reproducible with a short, documented command sequence.

## Goals / Non-Goals

**Goals:**

- One command to build/load the knowledge base, one to run tests, one to start the demo (API + UI).
- Authoritative knowledge lives in plain `.ttl` files under `ontology/`; the running system treats them as read-only input and derives everything else in memory.
- Every reasoning-demo fact carries provenance (`asserted` | `inferred` | `rule-derived`) and derivations are never written back.
- Spec scenarios map 1:1 to pytest tests so acceptance is mechanical.
- Ontology expressivity stays within what a pure-Python OWL2-RL engine can safely materialize, with a documented optional HermiT consistency check (Java present on this machine).

**Non-Goals:**

- No LLM/RAG, document ingestion, authN/authZ, or deployment hardening (later phases).
- No persistent triple store server (Fuseki/Jena TDB, RDF4J) in the MVP: the file-backed read-only dataset replaces it.
- No full FIBO import; FIBO is referenced by alignment annotations only.
- No non-`zh`/`en` languages and no i18n framework.

## Decisions

### D1: File-backed rdflib graph instead of a triple-store server

The authoritative dataset is the set of Turtle files under `ontology/`; the application loads them into an in-memory rdflib `Graph` at startup and serves SPARQL from it.

- **Why**: keeps RDF/OWL semantics and Protégé compatibility while removing JVM/server operations from the daily demo path; files are the single source of truth, which makes the "reasoning must not mutate data" requirement trivial to honor.
- **Alternatives considered**: Apache Jena TDB/Fuseki and RDF4J — full-featured servers, but add a running service and JVM footprint the MVP does not need; Neo4j property graph — rejected because it requires an OWL→property-graph mapping layer and dilutes the RDF/OWL story. Because the ontology is plain OWL2 files, a later phase can adopt Jena/RDF4J without re-authoring content.

### D2: Ontology split into three files with an annotation-only FIBO alignment

`ontology/banking-core.ttl` holds the TBox (classes/properties, `bc:` namespace, no `owl:imports`), `ontology/seed-corpora.ttl` holds the ABox/curated concept cards (individuals + card metadata), and `ontology/fibo-alignment.ttl` holds alignment annotations mapping selected classes to FIBO terms via a dedicated annotation property (for example `bc:alignedToFibo`).

- **Why**: separates concerns; dropping or updating FIBO alignment never touches core axioms; no network dependency at load time (no `owl:imports` of external ontologies).
- **Naming/labeling conventions** (enforced by tests): `rdfs:label` with `@zh` and `@en`; synonyms via `skos:altLabel`; definitions via `skos:definition`; attributes as datatype/object properties on the relevant classes.
- **Alternatives considered**: importing FIBO directly (huge, English-centric, drags licensing and load weight into every demo) — rejected for the MVP; reusing FTHO (event/time-oriented, mismatched with the business/product concept focus) — rejected; fully standalone without alignment notes — rejected because the user wants FIBO terminology grounding.

### D3: OWL2-RL materialization + declarative Python demo rules, with provenance tags

Reasoning output is produced in three strictly labelled layers over the read-only base graph:

1. **Asserted** — triples read from the corpus files.
2. **Inferred** — the OWL2-RL/RDFS closure from `owlrl` (subclass transitivity, type propagation from a class to its superclasses, etc.).
3. **Rule-derived** — results of the demo rule set: each rule is a small declarative Python record `{id, title, text, evaluate(graph) -> triples}` in `src/banking_kb/rules.py`. The MVP ships one rule, e.g. classifying a deposit individual as a long-term product when its term attribute exceeds the configured threshold.

Optional consistency check: `make check-consistency` runs a HermiT satisfiability pass (via owlready2 + local Java) and reports "no unsatisfiable classes", or clearly states the check was skipped because Java is unavailable. Protégé (HermiT tab) remains the documented authoring-time fallback.

- **Why**: pure-Python reasoning keeps the demo dependency-light; provenance is a first-class output because the demo's point is showing *what* was derived and *why*.
- **Alternatives considered**: Jena OWL reasoner / SWRL rule engine and Pellet — full DL + SWRL, but JVM-only; owlready2 `sync_reasoner` (HermiT) on every run — needs Java as a hard dependency. HermiT is kept only for the optional consistency gate.

### D4: One backend, three query surfaces

FastAPI exposes exactly the behaviours the specs require:

- `GET /api/concepts?q=<term>` — label/synonym lookup with hierarchy expansion (superclass + direct subclasses) and structured detail per result (see `specs/concept-search/spec.md`).
- `GET /api/tree` and `GET /api/concepts/{id}` — browse tree and detail view with relationships (`specs/concept-browser/spec.md`).
- `POST /api/reasoning/demo` — runs layer 2 + layer 3 in memory and returns provenance-tagged facts plus a store-unchanged proof (`specs/reasoning-demo/spec.md`, `specs/knowledge-content/spec.md`).

Matching and ranking: normalize the query (trim; lower-case Latin; treat Chinese as-is with prefix tolerance), score exact Chinese label > synonym > prefix match > English label. The UI is a small Streamlit app with three panels (Search / Browse / Reasoning demo) consuming these endpoints. Alternatives considered: plain static HTML+JS served by FastAPI (more bespoke code), Gradio (less suited to a tree browser).

### D5: Corpus authoring as "concept cards"

Each curated entry is authored as a block ("card") in `seed-corpora.ttl`: an individual or leaf class plus labels, definition, synonyms, and key attributes, with a `skos:editorialNote` pointing at the source type (public textbook/regulatory-style definition). Coverage targets from `specs/knowledge-content/spec.md` are asserted by tests: ≥ 15 entries; deposit, loan, wealth-management, account, and party categories each ≥ 1 entry; all classes bilingual. The import interface for future internal data is a documented convention (append an `internal/` directory, git-ignored, loaded via an explicit flag) — never shipped content.

### D6: Repository layout

```
ontology/                       # repo root (openspec/, .agents/, AGENTS.md live here)
├── README.md                   # setup, run, demo script
├── Makefile                    # make setup | load | test | api | ui | check-consistency
├── requirements.txt
├── ontology/
│   ├── banking-core.ttl        # TBox
│   ├── seed-corpora.ttl        # ABox / concept cards
│   └── fibo-alignment.ttl      # alignment annotations
├── src/banking_kb/
│   ├── kb.py                   # graph loading + SPARQL helpers
│   ├── search.py               # semantic search + ranking
│   ├── reasoning.py            # owlrl closure + provenance assembly
│   ├── rules.py                # declarative demo rules
│   └── api.py                  # FastAPI app
├── ui/app.py                   # Streamlit panels
├── tests/                      # pytest per spec scenario
└── docs/
    ├── fibo-alignment.md       # mapping list (machine- and human-readable)
    └── demo-script.md
```

## Risks / Trade-offs

- [OWL2-RL subset cannot express every DL axiom] → Keep the ontology within RL-friendly expressivity (hierarchy + property characteristics + a small number of restrictions); run the optional HermiT gate during authoring; document anything that needs a stronger reasoner.
- [Consistency check depends on optional Java/HermiT] → `make check-consistency` fails loudly with a clear "Java missing" message; Protégé/HermiT documented as fallback; the demo itself never hard-depends on Java.
- [Chinese search without tokenization] → Normalize and prefix-match on the whole term; add explicit synonyms (定存) to bridge vocabulary gaps; tests cover the synonym path.
- [Seed content drift or accidental internal data] → Provenance notes per card, coverage tests, git-ignored `internal/` import area, and a README policy statement.
- [owlrl over-materialization or partial entailment] → Materialize into a separate inference graph, never the base graph; assert store-unchanged in tests (spec scenario).

## Migration Plan

Greenfield: nothing to migrate. Adoption path: (1) `python3 -m venv .venv && make setup`, (2) `make load` (parses the three ontology files into the dataset), (3) `make test` (spec-scenario tests), (4) `make api` + `make ui` for the demo. If the ontology is later edited in Protégé, save as Turtle into the same files and re-run `make load && make test`. Phase 2 (RAG/LLM) will be proposed as a separate OpenSpec change after this change is archived; the file-based dataset and JSON API give that phase a clean integration point.

## Open Questions

- Final ontology namespace IRI (cosmetic; defaults to a placeholder domain).
- Exact seed card list beyond the spec'd coverage minimums — fleshed out during implementation within the spec constraints.
- Optional: swapping the local in-memory store for Fuseki in a later phase (does not change specs or file formats).
