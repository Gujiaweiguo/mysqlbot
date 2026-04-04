## MODIFIED Requirements

### Requirement: Structured regression report
Each full-regression run SHALL produce a structured report that includes scope, environment, executed commands, gate results, evidence references, unresolved issues, and release recommendation. When G5 is executed with the deterministic mock-provider path, the report SHALL record that execution mode.

#### Scenario: G5 runs with deterministic failure-path mode
- **WHEN** a regression report includes G5 failure-path results from CI
- **THEN** the report records that G5 used the deterministic mock-provider path
- **AND** reviewers can distinguish that run mode from infrastructure failures unrelated to the intended failure-path scenarios

### Requirement: Evidence traceability
Regression reports MUST include evidence references for each gate result so outcomes can be independently verified. G5 evidence MUST remain traceable to the executed failure-path mode and mock-provider observations.

#### Scenario: Reviewer inspects G5 provider context
- **WHEN** a reviewer audits G5 evidence from a CI regression run
- **THEN** the evidence identifies the failure-path execution mode and the observed mock-provider behavior
