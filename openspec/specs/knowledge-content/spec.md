# Knowledge Content Specification

## Purpose

Defines the curated OWL ontology and seed corpus delivered with the MVP: the reusable banking business/product concept model and its reference data, including the consistency, labeling, terminology-alignment, and coverage guarantees that every other demo capability depends on.

## Requirements

### Requirement: Consistent, loadable ontology

The delivered `banking-core` ontology SHALL parse and load without errors in the MVP toolchain and SHALL contain no unsatisfiable classes under the MVP's OWL reasoner.

#### Scenario: Ontology loads cleanly

- **WHEN** the MVP loads the ontology files into the RDF store and runs the reasoner
- **THEN** loading completes with no parse or import errors and the reasoner reports no inconsistent (unsatisfiable) classes

#### Scenario: Referential integrity

- **WHEN** the ontology is structurally validated (all class/property references, domains, and ranges resolve to declared entities)
- **THEN** validation reports no dangling or unresolved references

### Requirement: Bilingual labels and synonyms

Every concept class SHALL carry at least one Chinese (`zh`) and one English (`en`) label, and SHALL declare synonyms for common alternative names where domain vocabulary exists (for example 定存 for 定期存款).

#### Scenario: No class lacks either label

- **WHEN** a reviewer lists all concept classes and checks for `zh` and `en` labels
- **THEN** every class has both a Chinese and an English label

#### Scenario: Synonyms are queryable

- **WHEN** a synonym such as 定存 is declared for the time-deposit concept
- **THEN** a lookup by that synonym resolves to the same concept

### Requirement: FIBO terminology alignment

Each class that maps to a Financial Industry Business Ontology (FIBO) term SHALL carry an explicit alignment annotation, and the complete mapping list SHALL be documented in a machine-readable and human-readable alignment note (for example `docs/fibo-alignment.md`).

#### Scenario: Aligned classes are annotated

- **WHEN** a reviewer queries classes that the alignment note declares as mapped to FIBO terms
- **THEN** each such class carries at least one alignment annotation referencing the FIBO term

#### Scenario: Alignment is documented

- **WHEN** the alignment note is opened
- **THEN** it lists every class-to-FIBO mapping used by the seed corpus with the source term identifier

### Requirement: MVP content coverage

The seed corpus SHALL contain at least 15 curated, public and generic banking product/business concept entries (no confidential or internal bank data) that together cover at least deposit products, loan products, wealth-management products, account types, and parties; each entry SHALL include labels, a definition, and its key attributes.

#### Scenario: Minimum corpus size and coverage

- **WHEN** the seed corpus is counted per top-level category
- **THEN** the total number of curated concept entries is at least 15, and the deposit, loan, wealth-management, account, and party categories each contain at least one curated entry

#### Scenario: No internal data in the corpus

- **WHEN** the README and corpus provenance notes are reviewed
- **THEN** they state that all shipped content is public/generic and that internal data is supported only through a documented import interface, never shipped inside the repository

### Requirement: Expanded, source-verified corpus

After the ontology-enrichment change the curated corpus SHALL contain at least 50 concept classes and at least 30 curated individuals, all public and generic, covering at least: deposit products and deposit-account arrangements, loan products (personal, housing/mortgage, consumption, business and credit classes as curated), wealth-management products (including 现金管理类/固收类/混合类/权益类 classification), account types (savings, settlement, time-deposit, loan/credit accounts), parties and customer roles, rate & pricing concepts, and account/transaction event concepts. Every class and individual added by that change SHALL carry Chinese and English labels, a definition, and, where attributes apply, key attributes, and SHALL be marked as public/generic with a source note.

#### Scenario: Expanded coverage minimums are met

- **WHEN** the curated corpus is counted per top-level category after enrichment
- **THEN** the total number of concept classes is at least 50, the number of curated individuals is at least 30, and every category in the extended category set (deposit, loan, wealth management, account, party/role, rate & pricing, transaction event) contains at least one curated class with a definition

#### Scenario: Every new entry is bilingual, defined and provenance-marked

- **WHEN** a reviewer lists the classes and individuals added by the ontology-enrichment change
- **THEN** each carries both a Chinese and an English label, a non-empty definition, and a `skos:editorialNote` that marks the entry as public/generic and identifies the source type used for its alignment

### Requirement: Verified FIBO alignment

Every `bc:alignedToFibo` annotation in the corpus SHALL reference an IRI that exists as a class or named individual in a pinned FIBO release module downloaded during implementation, and the mapping SHALL be documented in `docs/fibo-alignment.md` with the module IRI and verification date. FIBO SHALL never be imported into the running dataset.

#### Scenario: Alignment annotations resolve to real FIBO terms

- **WHEN** the alignment file is checked against the pinned FIBO snapshot
- **THEN** every aligned IRI appears in the corresponding module file, and no annotation points at an invented or deprecated IRI

#### Scenario: Alignment documentation lists modules and verification

- **WHEN** the alignment note is opened
- **THEN** it lists each mapping with the FIBO module IRI it was verified against and the verification date, and states that FIBO content is used by alignment only and never imported

### Requirement: External sources and licensing are documented

The research dossier (`docs/reference/ontology-sources.md`) SHALL list every external source used for alignment or taxonomy guidance, with its URL, accessed/verified date, and license/copyright notice, and SHALL state that definitions in this repository are self-authored rather than copied from external ontologies.

#### Scenario: Sources dossier is complete

- **WHEN** the sources dossier and the corpus provenance notes are compared
- **THEN** every source referenced by an `editorialNote` appears in the dossier, and the dossier records the license notice of each source

### Requirement: Backward-compatible corpus evolution

Enrichment SHALL NOT break the behavior guaranteed by the existing main specs: semantic search and synonym scenarios, tree browsing to leaf product types, provenance-tagged reasoning (including the long-term deposit demo rule firing), RAG grounding and citations, and the agent read-only tools all SHALL keep their previously specified behavior, and the ontology SHALL remain structurally valid and consistent.

#### Scenario: All prior capability scenarios still pass

- **WHEN** the full pytest suite and `openspec validate --specs` run after the enrichment
- **THEN** every existing scenario test for `concept-search`, `concept-browser`, `reasoning-demo`, `rag-question-answering`, and `agentic-question-answering` passes unchanged, and the HermiT consistency gate reports no inconsistent classes
