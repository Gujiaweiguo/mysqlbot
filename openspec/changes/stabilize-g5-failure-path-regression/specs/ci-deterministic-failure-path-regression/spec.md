## ADDED Requirements

### Requirement: Deterministic CI failure-path provider contract for G5
The system SHALL provide a deterministic CI execution path for G5 failure-path regression so hosted CI can validate rate-limit and transient-provider behavior without relying on uncontrolled external services.

#### Scenario: GitHub Actions executes G5
- **WHEN** the `Integration Test (G0-G5)` workflow reaches the G5 failure-path gate in CI
- **THEN** the workflow uses a deterministic mock-provider path with explicitly configured connectivity between the runner and the backend container
- **AND** the gate evaluates controlled HTTP 429 and transient failure scenarios against stable acceptance criteria

### Requirement: G5 evidence remains resilience-focused
The deterministic CI failure-path regression MUST produce evidence that shows whether failures were controlled, whether retry/recovery behavior was observed, and which mock-provider scenario was executed.

#### Scenario: Reviewer audits G5 evidence
- **WHEN** a reviewer inspects G5 evidence from a CI run
- **THEN** the evidence identifies the mock-provider scenario, status codes, retry observations, and whether each failure-path case passed or failed
