# Concept Search Specification

## Purpose

Lets bank staff find banking product and business concepts by name or synonym and see each concept's place in the class hierarchy, so lookups succeed even when the query wording differs from the stored label.

## Requirements

### Requirement: Label and synonym lookup

The system SHALL return concepts whose Chinese or English label or synonym matches the user's search term, using normalized matching (trimmed, case-insensitive for Latin text, prefix-tolerant for Chinese terms).

#### Scenario: Match on Chinese label

- **WHEN** a user searches for 存款
- **THEN** the result set includes the deposit concept labeled 存款 and ranks it at the top

#### Scenario: Match on Chinese synonym

- **WHEN** a user searches for 定存, which is declared as a synonym of 定期存款
- **THEN** the result set includes the time-deposit concept

#### Scenario: Match on English label

- **WHEN** a user searches for `deposit`
- **THEN** the result set includes deposit concepts matched through their English labels

#### Scenario: No matching concept

- **WHEN** a user searches for a term that matches no label or synonym
- **THEN** the system returns an empty result set with a clear "no results" indication rather than an error

### Requirement: Hierarchy expansion in search results

When a search matches a concept, the results SHALL also surface that concept's direct superclass and direct subclasses so the user sees where it sits in the hierarchy.

#### Scenario: Result shows hierarchy context

- **WHEN** a search matches 存款 (Deposit)
- **THEN** the result includes 存款's direct superclass (such as 产品/Product) and its direct subclasses (such as 活期存款 and 定期存款 as present in the corpus)

### Requirement: Structured concept details

For every concept returned by a search, the system SHALL provide a structured detail object containing its identifier, Chinese and English labels, synonyms, definition, direct superclass, direct subclasses, and key attribute-value pairs.

#### Scenario: Result payload carries full detail

- **WHEN** a search returns a concept
- **THEN** each returned concept includes identifier, `zh`/`en` labels, synonyms, definition text, direct superclass identifier, direct subclass identifiers, and the concept's attribute-value pairs
