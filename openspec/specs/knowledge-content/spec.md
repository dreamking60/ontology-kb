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
