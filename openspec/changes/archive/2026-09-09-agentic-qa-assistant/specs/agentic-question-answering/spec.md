## Purpose

Lets bank staff ask questions that require several knowledge-base operations — chained search, structured querying, and reasoning — by letting an LLM agent decide which read-only KB tools to call, observe results, and iterate, then synthesize a grounded final answer whose reasoning is inspectable through a step trace.

## ADDED Requirements

### Requirement: Multi-step tool-calling question answering

The system SHALL answer a natural-language question by letting an LLM agent call knowledge-base tools iteratively (a bounded number of turns) and then produce a final answer grounded in the tool results; it SHALL expose the executed steps so users can inspect how the answer was reached.

#### Scenario: Question requiring chained operations

- **WHEN** a user asks a question that needs more than one operation (for example "哪些示例产品受存款保险保障？它们的期限分别是多少？")
- **THEN** the agent calls more than one tool before answering (for example a SPARQL query plus concept-detail calls), the final answer cites the relevant concepts, and the response trace lists at least the two executed steps with their tool names

#### Scenario: Final answer appears only after tool results

- **WHEN** the LLM's first response requests tools and the tools return results
- **THEN** the system feeds those results back to the LLM and continues the loop, and the response contains a final natural-language answer rather than raw tool output

### Requirement: Read-only tool registry

The system SHALL provide tools for semantic concept search, concept detail, class-hierarchy browsing, the reasoning demo, and read-only SPARQL querying; every tool SHALL operate read-only on the in-memory knowledge base and SHALL return structured, human-readable results.

#### Scenario: All registry tools are callable

- **WHEN** the agent (or a test driver) invokes each of `search_concepts`, `concept_detail`, `browse_tree`, `reasoning_demo`, and `sparql_query`
- **THEN** each tool returns a non-empty result summary appropriate to its purpose

#### Scenario: SPARQL tool rejects mutations

- **WHEN** a caller submits a SPARQL statement that is not a read-only `SELECT`/`ASK` query (for example `INSERT`, `DELETE`, `LOAD`, `CLEAR`)
- **THEN** the tool returns an explicit read-only error and executes nothing

### Requirement: Bounded agent loop with graceful termination

The agent loop SHALL terminate when the LLM returns a final answer without tool calls, or when the configured iteration budget is exhausted; an exhausted budget SHALL yield a final answer that says the question needs more steps, never an infinite loop.

#### Scenario: Budget exhaustion is reported

- **WHEN** an LLM (or a test fake) requests tools on every turn
- **THEN** the loop stops at the budget limit and the answer states that the question could not be fully answered within the step limit

#### Scenario: Tool errors do not crash the loop

- **WHEN** a tool returns an error result (for example an invalid SPARQL query)
- **THEN** the error text is returned to the LLM as the tool result and the loop continues or terminates normally

### Requirement: Degradation without tool-calling or LLM

When no LLM is configured, the system SHALL answer with the deterministic retrieval summary (`mode` `fallback`). When an LLM is configured but rejects the tools parameter, the system SHALL fall back to single-turn RAG synthesis (`mode` `llm`). Neither case SHALL return an error.

#### Scenario: No LLM key degrades to fallback

- **WHEN** no `BANKING_KB_LLM_*` configuration is present and a user asks a question with matching concepts
- **THEN** the endpoint returns `mode` `fallback` with a deterministic summary and its citations

#### Scenario: Model without tool support degrades to RAG synthesis

- **WHEN** the configured endpoint responds with an error indicating the `tools` parameter is unsupported
- **THEN** the system retries as a single-turn RAG question and returns `mode` `llm` with a synthesized, cited answer

### Requirement: Agent chat endpoint contract

The system SHALL expose `POST /api/agent/chat` accepting `{"question": "...", "history": [...]}` and SHALL respond with `{"answer", "mode", "citations", "trace", "retrieval_summary"}` where `trace` is an array of executed tool steps `{step, tool, arguments, summary}`; an empty or whitespace-only question SHALL be rejected with HTTP 422 without calling the LLM, and `history` SHALL be optional.

#### Scenario: Agent chat request without history

- **WHEN** a client posts `{"question": "哪些示例产品受存款保险保障？"}` without history
- **THEN** the response has HTTP 200 with all contract fields, a `mode` of `agent`, `llm`, or `fallback`, and a citations list for the concepts used

#### Scenario: Empty question is rejected before the LLM

- **WHEN** a client posts a request with an empty or whitespace-only `question`
- **THEN** the endpoint rejects it with HTTP 422 and no LLM call is made
