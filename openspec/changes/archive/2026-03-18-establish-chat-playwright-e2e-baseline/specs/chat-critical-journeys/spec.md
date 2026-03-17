## ADDED Requirements

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
