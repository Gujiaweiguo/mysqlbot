## MODIFIED Requirements

### Requirement: Chat endpoints SHALL delegate to orchestration services
The system SHALL implement backend chat HTTP handlers and agent-facing adapter handlers as transport adapters that resolve request context and delegate chat execution to orchestration services. Chat HTTP handlers and OpenClaw-facing adapter handlers MUST NOT directly embed multi-step generation, record mutation sequencing, or stage-specific parsing behavior.

#### Scenario: Stream endpoint starts chat execution
- **WHEN** a backend `/chat` endpoint accepts a new generation request
- **THEN** the endpoint resolves transport-level dependencies and passes a structured command to a chat orchestration service
- **THEN** the endpoint does not directly perform stage-by-stage generation or persistence writes inline

#### Scenario: OpenClaw-facing adapter starts question or analysis execution
- **WHEN** an OpenClaw-facing adapter endpoint accepts a supported question or analysis request
- **THEN** the adapter resolves transport-level authentication, workspace, and session context
- **AND** the adapter delegates execution to the stable chat orchestration entrypoint instead of embedding the NL-query pipeline inline
