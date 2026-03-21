## ADDED Requirements

### Requirement: Frontend chat surfaces SHALL consume stream events through a shared adapter
The system SHALL route frontend chat stream consumption through a shared adapter or composable that interprets the backend streaming contract before view state is updated.

#### Scenario: Frontend receives streamed chat events
- **WHEN** a chat surface receives incremental stream events from the backend contract
- **THEN** a shared stream-consumption adapter normalizes those events for the frontend
- **AND** page-level chat views do not implement incompatible event parsing rules locally
