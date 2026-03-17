## ADDED Requirements

### Requirement: Chat endpoints SHALL delegate to orchestration services
The system SHALL implement backend chat HTTP handlers as transport adapters that resolve request context and delegate chat execution to orchestration services. Chat HTTP handlers MUST NOT directly embed multi-step generation, record mutation sequencing, or stage-specific parsing behavior.

#### Scenario: Stream endpoint starts chat execution
- **WHEN** a backend `/chat` endpoint accepts a new generation request
- **THEN** the endpoint resolves transport-level dependencies and passes a structured command to a chat orchestration service
- **THEN** the endpoint does not directly perform stage-by-stage generation or persistence writes inline

### Requirement: Chat orchestration SHALL coordinate the backend pipeline
The system SHALL execute multi-step chat generation through a dedicated orchestration layer that coordinates question creation, datasource resolution, model interaction, parsing, post-processing, and record finalization through explicit collaborators.

#### Scenario: Multi-step generation runs successfully
- **WHEN** a chat request requires multiple backend stages such as SQL generation, SQL execution, and chart or analysis generation
- **THEN** a chat orchestration service coordinates those stages in order
- **THEN** each stage is invoked through an explicit collaborator boundary rather than hidden cross-module side effects

### Requirement: Persistence writes SHALL be isolated behind chat persistence collaborators
The system SHALL route chat record and log mutations through dedicated persistence collaborators. LLM pipeline components MUST NOT require direct knowledge of low-level chat CRUD mutation functions in order to complete generation stages.

#### Scenario: Backend stage stores chat progress
- **WHEN** a backend generation stage needs to persist an answer, log entry, or final record state
- **THEN** it does so through a chat persistence collaborator or adapter contract
- **THEN** the stage does not call record-level CRUD mutations as an implicit side effect of unrelated parsing or model logic

### Requirement: LLM pipeline stages SHALL have focused responsibilities
The system SHALL separate backend chat pipeline concerns into focused collaborators for context preparation, model invocation, response parsing, and post-processing. Each collaborator MUST accept and return typed intermediate data relevant to its stage.

#### Scenario: SQL answer parsing is extracted from orchestration
- **WHEN** the backend processes model output that may contain SQL-generation results
- **THEN** a parsing-focused collaborator converts that output into typed intermediate results
- **THEN** downstream persistence or streaming behavior consumes those results without duplicating parsing rules
