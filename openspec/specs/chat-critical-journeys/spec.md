# chat-critical-journeys Specification

## Purpose
Define the first browser-level chat smoke journeys that the baseline E2E suite must cover.

## Requirements
### Requirement: The baseline SHALL cover the primary new-chat success flow
The system SHALL include a Playwright smoke test for the primary chat success path in which a user starts or enters a chat, submits a question, receives streamed assistant progress, and sees the final rendered answer state.

#### Scenario: User completes the primary chat smoke journey
- **WHEN** the browser test triggers the supported new-chat question flow
- **THEN** the UI submits the request, renders streaming updates, and reaches a stable assistant-answer state without runtime errors

### Requirement: The baseline SHALL cover one follow-up critical chat action
The system SHALL include at least one additional Playwright smoke journey for a follow-up chat action that reuses the existing chat state, such as recommended-question replay or loading a historical chat conversation.

#### Scenario: User completes a follow-up chat action
- **WHEN** the browser test exercises the selected second critical chat flow
- **THEN** the UI completes that action successfully and preserves the expected chat state transitions for the user

### Requirement: Baseline chat journeys SHALL assert user-visible outcomes
The system SHALL assert user-visible outcomes for the first covered chat journeys, including visible loading or streaming states and final rendered content, rather than only asserting that network requests were sent.

#### Scenario: Browser test verifies chat outcomes
- **WHEN** a baseline Playwright chat test finishes executing a covered journey
- **THEN** it verifies the expected UI state and rendered content that the user would rely on

### Requirement: Critical chat coverage SHALL include assistant default-datasource entry and switch behavior
The system SHALL include regression coverage for the assistant and embedded chat journey in which a configured default datasource is applied at direct entry and a datasource switch starts a new chat session.

#### Scenario: Assistant direct-entry journey succeeds with configured default datasource
- **WHEN** a regression test opens assistant or embedded chat configured with a default datasource and submits a first question
- **THEN** the chat starts without a manual datasource picker
- **AND** the rendered session shows the configured datasource as the active datasource

#### Scenario: Datasource switching opens a new assistant chat session
- **WHEN** a regression test switches datasource from an assistant or embedded chat session started through direct entry
- **THEN** the system opens a new chat session for the newly selected datasource
- **AND** the original session remains unchanged
