## ADDED Requirements

### Requirement: Structured regression report
Each full-regression run SHALL produce a structured report that includes scope, environment, executed commands, gate results, evidence references, unresolved issues, and release recommendation.

#### Scenario: Report generation after run
- **WHEN** all regression gates complete
- **THEN** a structured report is produced with all required sections and final decision status

### Requirement: Evidence traceability
Regression reports MUST include evidence references for each gate result so outcomes can be independently verified.

#### Scenario: Evidence review
- **WHEN** a reviewer audits regression results
- **THEN** each gate can be traced to concrete logs, outputs, or screenshots linked from the report
