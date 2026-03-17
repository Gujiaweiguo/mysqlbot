## ADDED Requirements

### Requirement: The Playwright suite SHALL cover the primary chat streamed error path
The system SHALL include a deterministic Playwright browser test for the primary chat question flow in which the mocked streamed response emits a contract-shaped `error` event after the request starts.

#### Scenario: User sees a streamed chat error after question submission
- **WHEN** the browser test submits a chat question and the mocked chat stream emits an `error` event
- **THEN** the submitted user message remains visible in the chat UI
- **THEN** the failed assistant response renders the expected error outcome for that chat record

### Requirement: Error-path chat coverage SHALL assert recovery state
The system SHALL assert user-visible recovery behavior for the covered chat error path rather than only asserting that an error payload was received.

#### Scenario: Browser test verifies chat recovery after streamed error
- **WHEN** the covered error-path Playwright test finishes processing the mocked failure
- **THEN** the UI no longer remains stuck in an active thinking or streaming state
- **THEN** the test verifies a stable error-visible state instead of requiring a success-only completion path
