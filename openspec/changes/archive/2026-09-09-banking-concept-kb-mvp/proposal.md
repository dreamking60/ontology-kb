## Why

Banking staff routinely need to answer questions such as "What product types exist?", "Is a certificate of deposit a kind of deposit?", "Which concepts are related to a wealth-management product?" — but this knowledge lives scattered across documents, wikis, and tribal knowledge. A lightweight ontology-driven knowledge base can structure banking business and product concepts so that semantic search (including class-hierarchy expansion) and rule reasoning work out of the box. This change scaffolds the **first runnable MVP** of such a knowledge base in this (currently empty) repository, as the foundation for a future internal financial-model/concept knowledge platform in a commercial-bank context (CMB staff), following a spec-first development approach.

This is a greenfield MVP: no code exists yet in `/home/dreamking/ontology`. The goal is a small, reproducible, demo-able system — not a production platform.

## What Changes

- Scaffold the repository into a runnable demo project: an **ontology-driven banking business/product concept knowledge base**.
- Introduce a small, self-authored **core OWL ontology** (`banking-core`) covering the product class hierarchy (e.g. deposit → time deposit → certificate of deposit), accounts, parties, transactions, and rate/risk attributes, with **Chinese labels and synonyms** for banking vocabulary. FIBO is used only as a **terminology-alignment reference** (annotations + an alignment note), never wholesale-imported.
- Ship a **curated seed dataset**: 15–20 public, generic banking product/business concept cards (no internal or confidential bank data), with a documented import interface for future internal data.
- Provide an **RDF/OWL storage + reasoning stack** and a small **JSON API** exposing semantic search and reasoning-demo queries.
- Provide a lightweight **web UI** (browser-based) for concept search, hierarchy browsing, and a rule-reasoning demo.
- Include reproducible setup/run scripts and a README so the demo runs locally with few commands.
- Explicitly **out of scope for this change** (deferred to a later phase): LLM/RAG question answering, ingestion from live bank documents, user auth/roles, and deployment hardening.

## Capabilities

### New Capabilities

- `knowledge-content`: The curated OWL ontology and seed corpus shipped by the MVP — consistent and loadable, bilingual (Chinese/English labels plus synonyms), aligned to FIBO terminology, and covering at least 15 public/generic banking product & business concept cards (deposits, loans, wealth management, accounts, parties).
- `concept-search`: Semantic search over banking product/business concepts — matches labels and synonyms (Chinese and English), expands results along the class hierarchy (subclass/superclass), and returns structured concept details.
- `concept-browser`: Browse the concept knowledge base as a hierarchy tree with concept detail pages showing properties, synonyms, and relationships.
- `reasoning-demo`: Run the ontology reasoner on sample rules and display inferred/classified facts (e.g. subclass inheritance of attributes) with an explanation of what was inferred.

### Modified Capabilities

_(none — greenfield change; no existing specs under `openspec/specs/`)_

## Impact

- **Repository**: `/home/dreamking/ontology` transitions from empty to the demo project root (source, ontology files, seed data, tests, docs live at the top level; `openspec/` holds specs and changes).
- **Runtime/toolchain**: Python 3.11+; ontology authoring via Protégé-compatible OWL files; RDF storage and reasoning library (see `design.md` for the concrete Jena-vs-pure-Python decision).
- **Data files**: `.owl`/`.ttl` ontology and seed artifacts under a `data/` or `ontology/` directory.
- **APIs**: small local JSON HTTP API for search and reasoning queries; no external network services required.
- **New dependencies**: Python packages for the web server, UI, and RDF stack; Java runtime only if the Jena/Pellet path is chosen in design.
- **Docs**: README with setup, run, and demo-query instructions.
