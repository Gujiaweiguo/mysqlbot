# chat-frontend-boundaries Specification

## Purpose
Structure the frontend chat surface as a composition shell that delegates message rendering, input handling, and session/stream state to focused collaborators and shared controllers, reused across both embedded and standard chat.
## Requirements
### Requirement: Chat page shells SHALL delegate to focused frontend collaborators
The frontend SHALL implement chat page-level views as composition shells that delegate message rendering, input handling, and other focused responsibilities to child components or shared composables.

#### Scenario: Full chat page renders an active session
- **WHEN** the full chat page renders an active chat session
- **THEN** the page-level shell coordinates high-level layout and routing concerns
- **AND** focused collaborators own message rendering and input-specific behavior

### Requirement: Chat session and stream state SHALL use shared controllers
The frontend SHALL coordinate chat session state and stream-progress updates through shared controllers or composables instead of page-local ad hoc state alone.

#### Scenario: Streamed answer updates active session state
- **WHEN** a chat request emits incremental stream events
- **THEN** the shared chat state/controller layer consumes those updates
- **AND** page-level views react to normalized state rather than parsing stream effects inline

### Requirement: Embedded and standard chat surfaces SHALL share core orchestration behavior
The frontend SHALL reuse the same core chat orchestration behavior across embedded and standard chat surfaces even when their surrounding layout differs.

#### Scenario: Embedded chat starts a streamed conversation
- **WHEN** a user starts a chat flow from an embedded surface
- **THEN** the embedded surface reuses the shared chat orchestration and stream-consumption behavior
- **AND** only surface-specific layout concerns differ from the standard chat page
