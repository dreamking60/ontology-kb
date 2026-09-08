# Concept Browser Specification

## Purpose

Lets users explore the ontology as a browsable hierarchy — from top-level categories down to concrete product types — and inspect any concept's full detail without having to write SPARQL queries.

## Requirements

### Requirement: Hierarchical tree browsing

The system SHALL present the concept hierarchy as a navigable tree whose top level exposes the main categories of the corpus (at least 产品/Product, 账户/Account, 主体/Party, and related categories as defined in the ontology).

#### Scenario: Browse from top-level categories

- **WHEN** a user opens the concept browser
- **THEN** the top-level categories are shown, and expanding a category such as Product reveals its class hierarchy down to the leaf product types present in the corpus (for example 大额存单 under 定期存款 under 存款)

### Requirement: Concept detail view

When a user selects a concept in the browser, the system SHALL display that concept's identifier, Chinese and English labels, synonyms, definition, direct superclass, direct subclasses, and attribute-value pairs.

#### Scenario: Open a concept's detail

- **WHEN** a user selects the concept 大额存单 in the tree
- **THEN** the detail view shows 大额存单 as a subclass of 定期存款, lists its labels and definition, and renders its declared attributes and their values

### Requirement: Relationship visibility

The concept detail view SHALL also list the concept's non-hierarchical relationships to other concepts, each labelled with the property name that connects them.

#### Scenario: Related concepts are shown

- **WHEN** a concept with non-hierarchical relationships (for example a product whose attributes reference 利率/Rate or 主体/Party) is displayed
- **THEN** the detail view lists those relationships with the connecting property names, and each referenced concept is identifiable
