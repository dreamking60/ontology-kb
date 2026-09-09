## Purpose

Lets bank staff ask natural-language questions about the banking concept knowledge base and receive answers that are grounded in its content — every answer cites the source concepts it relied on, works without an external LLM key through a deterministic fallback, and refuses cleanly when the knowledge base holds no answer.

## ADDED Requirements

### Requirement: Knowledge-grounded question answering

The system SHALL answer a natural-language question about banking product/business concepts (in Chinese or English) using only content retrievable from the knowledge base — labels, synonyms, definitions, attributes, hierarchy, and relationships — and SHALL NOT fabricate facts outside that content.

#### Scenario: Question about a known concept is answered from its definition

- **WHEN** a user asks "什么是大额存单？"
- **THEN** the answer is based on the definition and attributes of the 大额存单 concept and cites that concept

#### Scenario: Out-of-corpus question is refused, not invented

- **WHEN** a user asks about a topic with no matching content in the knowledge base (for example a specific company's stock price)
- **THEN** the system returns a clear "not found in the knowledge base" response and provides no fabricated details

### Requirement: Retrieval over the concept knowledge base

The system SHALL retrieve candidate concepts for a question using label and synonym matching plus overlap with definitions and attribute text, and SHALL expand each candidate with its definition, key attributes, and direct hierarchy context for use in the answer.

#### Scenario: Synonym question retrieves the same concepts

- **WHEN** a user asks a question that uses the synonym 定存 instead of 定期存款
- **THEN** the retrieval result includes the 定期存款 concept with its definition and attributes

#### Scenario: Attribute-difference question surfaces both products

- **WHEN** a user asks "定期存款和活期存款有什么区别？"
- **THEN** retrieval returns both the 定期存款 and 活期存款 concepts so the answer can compare their attributes

### Requirement: Optional LLM synthesis with deterministic fallback

When an OpenAI-compatible LLM is configured via environment variables, the system SHALL synthesize a natural-language answer from the retrieved context. When no LLM is configured, the system SHALL still answer with a deterministic retrieval summary instead of failing or returning an error.

#### Scenario: LLM configured produces a synthesized answer

- **WHEN** `BANKING_KB_LLM_BASE_URL`, `BANKING_KB_LLM_API_KEY`, and `BANKING_KB_LLM_MODEL` are set and the endpoint is reachable
- **THEN** the response mode is `llm` and the answer is synthesized from the retrieved concept context

#### Scenario: No LLM key degrades to a summary

- **WHEN** no LLM configuration is present and a user asks a question with matching concepts
- **THEN** the system returns a deterministic summary of the matched concepts (mode `fallback`) that still answers from the knowledge base

### Requirement: Answer citations and provenance

Every answer SHALL list the source concepts it used, each with its identifier and Chinese label, so users can trace claims back to the knowledge base. Fallback summaries SHALL cite exactly the concepts they summarize.

#### Scenario: Answer carries citations

- **WHEN** a question is answered about one or more concepts
- **THEN** the response includes a citations list whose entries reference the concepts the answer actually used, and each citation exposes the concept identifier and label

### Requirement: Chat endpoint contract

The system SHALL expose `POST /api/chat` accepting a JSON body `{"question": "...", "history": [{"role": "user"|"assistant", "content": "..."}]}` and SHALL respond with `{"answer", "mode", "citations", "context", "retrieval_summary"}`; an empty or missing question SHALL be rejected with a 422-style error, and history SHALL be optional (single-turn Q&A works without it).

#### Scenario: Chat request without history

- **WHEN** a client posts `{"question": "什么是信用贷款？"}` without history
- **THEN** the response has HTTP 200 with the contract fields and mode `llm` or `fallback`

#### Scenario: Empty question is rejected

- **WHEN** a client posts a request with an empty or whitespace-only `question`
- **THEN** the endpoint rejects it with an HTTP 422 and does not call the LLM
