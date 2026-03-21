## ADDED Requirements

### Requirement: Backend chat decomposition SHALL preserve a stable orchestration entrypoint
The backend SHALL perform staged chat decomposition behind a stable orchestration entrypoint so transport-level callers do not need to track internal collaborator movement during migration.

#### Scenario: Chat endpoint invokes decomposed backend flow during migration
- **WHEN** a chat endpoint starts a request while backend extraction is still in progress
- **THEN** the endpoint invokes the stable orchestration entrypoint defined by the backend chat contract
- **AND** internal collaborator changes do not require endpoint-specific branching for old versus new module layouts
