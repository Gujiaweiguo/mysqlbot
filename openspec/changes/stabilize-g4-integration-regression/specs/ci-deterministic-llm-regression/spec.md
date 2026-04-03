## ADDED Requirements

### Requirement: Deterministic CI provider path for G4
The system SHALL provide a deterministic CI-only model-provider path for the G4 happy-path regression so scheduled and manually triggered integration runs do not depend on external LLM credentials or provider variability.

#### Scenario: Scheduled integration regression runs G4
- **WHEN** the `Integration Test (G0-G5)` workflow executes the G4 happy-path regression in CI
- **THEN** the application has an explicit default model configuration available for the run
- **AND** that configuration uses a deterministic CI provider path instead of an unmanaged external provider

### Requirement: Deterministic provider preserves G4 happy-path evidence
The deterministic CI provider path MUST preserve G4's end-to-end evidence contract by allowing the regression to produce SQL-bearing and data-bearing results for the defined `demo_sales` happy-path cases.

#### Scenario: G4 evidence is reviewed after a deterministic CI run
- **WHEN** reviewers inspect G4 regression evidence from a CI run
- **THEN** each configured happy-path case records whether SQL was produced and whether meaningful data was returned
- **AND** the regression outcome remains pass/fail driven by the existing evidence contract rather than by external provider availability
