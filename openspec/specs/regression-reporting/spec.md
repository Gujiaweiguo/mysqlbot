# regression-reporting Specification

## Purpose
Require each full-regression run to produce a structured, evidence-linked report capturing scope, gate results, unresolved issues, and a release-readiness decision.
## Requirements
### Requirement: Structured regression report
Each full-regression run SHALL produce a structured report that includes scope, environment, executed commands, gate results, evidence references, unresolved issues, and release recommendation. When G4 is executed with the deterministic CI provider path, the report SHALL record that execution mode.

#### Scenario: Report generation after run
- **WHEN** all regression gates complete
- **THEN** a structured report is produced with all required sections and final decision status

#### Scenario: G4 runs with deterministic CI provider mode
- **WHEN** a regression report includes G4 happy-path results from CI
- **THEN** the report records that G4 used the deterministic CI provider path
- **AND** reviewers can distinguish that run mode from historical external-provider executions

### Requirement: Evidence traceability
Regression reports MUST include evidence references for each gate result so outcomes can be independently verified. G4 evidence MUST remain traceable to the provider mode used for the run.

#### Scenario: Evidence review
- **WHEN** a reviewer audits regression results
- **THEN** each gate can be traced to concrete logs, outputs, or screenshots linked from the report

#### Scenario: Reviewer inspects G4 provider context
- **WHEN** a reviewer audits G4 evidence from a CI regression run
- **THEN** the evidence identifies the provider mode used for that run

