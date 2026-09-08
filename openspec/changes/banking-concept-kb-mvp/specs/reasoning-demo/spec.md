## Purpose

Demonstrates rule-based inference over the knowledge base: the reasoner classifies classes and individuals and derives facts that were not explicitly asserted, and every derived fact is shown with the source and rule that produced it, making the reasoning transparent to demo viewers.

## ADDED Requirements

### Requirement: Class-hierarchy inference

The system SHALL run an OWL reasoner over the knowledge base and expose facts that follow from the class hierarchy but are not explicitly asserted (for example subclass transitivity and type propagation from a class to its superclasses).

#### Scenario: Inferred supertype is reported

- **WHEN** the reasoning demo runs over the seed corpus containing an individual asserted only as an instance of 定期存款, where 定期存款 is a subclass of 存款
- **THEN** the output also reports the individual as an instance of 存款, marked as inferred (not asserted), with the class chain that justifies it

#### Scenario: Only consistent derivations are shown

- **WHEN** the reasoner classifies the ontology
- **THEN** the demo output contains no unsatisfiable-class errors and lists only facts consistent with the ontology

### Requirement: User-defined demo rule evaluation

The system SHALL evaluate at least one configurable demo rule over the seed individuals and report every fact the rule derives, together with the rule's text so viewers can read why the fact was derived.

#### Scenario: Rule-derived facts are reported with their rule

- **WHEN** a user triggers the reasoning demo that includes a demo rule (for example classifying a product as long-term when its term attribute exceeds a threshold)
- **THEN** every individual satisfying the rule's conditions appears in the derived-facts list, and each derived fact is tagged with the rule identifier and rule text that produced it

### Requirement: Derived facts carry provenance

Every fact produced by the reasoning demo SHALL be labelled with its provenance — asserted, inferred by the reasoner, or derived by a demo rule — so that asserted data is never confused with derivations.

#### Scenario: Provenance labels on all demo output

- **WHEN** the reasoning demo returns its fact list
- **THEN** each fact carries exactly one provenance tag (`asserted`, `inferred`, or `rule-derived`) and the tags match how the fact was obtained

### Requirement: Reasoning does not mutate the stored data

Reasoning and rule evaluation SHALL run over a derived view and SHALL NOT write derived facts back into the authoritative dataset.

#### Scenario: Store unchanged after reasoning

- **WHEN** the reasoning demo has run on the seed corpus
- **THEN** a comparison of the authoritative store before and after shows no added, removed, or changed triples
