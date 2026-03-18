# chat-recommended-question-replay-journeys Specification

## Purpose
Define deterministic browser-level coverage for recommended-question replay on top of the existing Playwright chat baseline.

## Requirements
### Requirement: The Playwright suite SHALL cover recommended-question replay
The system SHALL include a deterministic Playwright browser test in which a user clicks a visible recommended follow-up question from an existing successful chat and the conversation continues through a mocked replayed response.

#### Scenario: User replays a recommended follow-up question
- **WHEN** the browser test loads a successful chat with visible recommended questions and the user activates one of them
- **THEN** the UI submits the replayed follow-up question within the same chat context
- **THEN** the chat displays the replayed conversation continuation without runtime errors

### Requirement: Replay coverage SHALL assert user-visible continuation outcomes
The system SHALL assert user-visible continuation behavior for the covered replay path rather than only asserting that a replay request was sent.

#### Scenario: Browser test verifies replay continuation outcome
- **WHEN** the covered replay Playwright test finishes processing the mocked follow-up response
- **THEN** the replayed user turn remains visible in the chat UI
- **THEN** the follow-up assistant result is rendered and the active thinking or streaming state is cleared
