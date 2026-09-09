## Purpose

Presents the knowledge base and its RAG/agent question answering as a modern LLM chat product: conversational bubbles with markdown, per-answer mode and citations, an agent tool trace, an empty state with suggestions, streaming responses, and an in-app settings view where the LLM API can be configured — while making the no-key deterministic fallback an explicit, understandable state rather than a bare text dump.

## ADDED Requirements

### Requirement: Chat-style conversation interface

The web interface SHALL present a chat conversation in an LLM-assistant style: alternating user/assistant message bubbles, markdown rendering of assistant answers (headings, bold, lists, inline and fenced code), a visible "mode" badge per assistant message (`agent` | `llm` | `fallback`), citations rendered as tappable source chips, and an empty state offering suggested questions when no conversation has started.

#### Scenario: Assistant answer renders like a chat message

- **WHEN** a user sends a question and receives an answer
- **THEN** the answer is displayed in an assistant bubble with rendered markdown, a mode badge, and — when citations exist — source chips derived from the response citations

#### Scenario: Empty state offers suggestions

- **WHEN** a user opens the chat page with no messages yet
- **THEN** the page shows a welcome prompt plus at least three suggested-question chips that, when clicked, send that question

### Requirement: Agent tool trace is visible

When the agent endpoint produced a `trace`, the interface SHALL show the executed tool steps (step number, tool name, arguments, summary) in a collapsible, timeline-like panel attached to the answer, without cluttering the bubble.

#### Scenario: Tool steps are inspectable per answer

- **WHEN** an assistant message carries a non-empty `trace`
- **THEN** the interface renders a collapsible "工具执行轨迹" panel listing each step with its tool name, arguments, and summary

### Requirement: In-app LLM API configuration with masked status

The web interface SHALL expose a settings view that (a) shows whether an OpenAI-compatible LLM is configured and which endpoint/model is in use, (b) lets the user set or clear `base_url`, `api_key` and `model` at runtime through the API, and (c) never reveals the full API key back to the browser. The server SHALL persist runtime configuration only in memory (process scope) and SHALL keep the key out of logs and responses.

#### Scenario: Configure and read back masked config

- **WHEN** a user saves an API configuration and reloads the settings view
- **THEN** the view shows the configured base URL and model, an indicator that a key is present (without the key value), and a clear button; when no configuration exists the view explains the fallback (retrieval-summary) mode

#### Scenario: Runtime config never leaks the key

- **WHEN** the GET config endpoint is called after a key was set
- **THEN** the response contains no full key material — only a boolean/placeholder indicating presence

### Requirement: Explicit no-key degradation messaging

When no LLM API is configured, the interface SHALL state this condition clearly (status chip/banner on the chat page and in settings) and SHALL label answers produced without an LLM as fallback retrieval summaries, so the experience reads as intentional rather than broken.

#### Scenario: No-key state is communicated

- **WHEN** the app starts with no LLM configuration and the user opens the chat page
- **THEN** a visible status indicator says the LLM is not configured and that answers use the deterministic retrieval summary (mode=fallback), and the settings view offers the configuration path

### Requirement: Streaming chat responses

The interface SHALL consume streaming responses for chat and agent questions: `POST /api/chat/stream` SHALL stream answer content deltas when an LLM is configured, and `POST /api/agent/chat/stream` SHALL stream agent step events followed by the final answer; when no LLM is configured (or streaming fails) both SHALL emit a complete non-stream fallback event set instead of erroring, and the UI SHALL render progressively and end cleanly.

#### Scenario: Chat streams deltas with LLM configured

- **WHEN** a user sends a question and the LLM is configured and streaming succeeds
- **THEN** the answer text appears progressively (delta events) and the stream ends with citations and a terminal event

#### Scenario: Stream degrades without an LLM

- **WHEN** no LLM is configured and a user sends a question
- **THEN** the stream endpoint emits one answer event set (mode `fallback`) and terminates normally without an error
