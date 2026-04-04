# regression-test-gates Specification

## Purpose
Define an ordered sequence of mandatory regression gates (runtime health, backend/frontend quality, functional journeys, failure paths, reporting) with stop-on-fail policy and explicit waiver requirements.
## Requirements
### Requirement: Full regression gate sequence
The system SHALL define a full regression process composed of mandatory gates that are executed in a deterministic order: runtime health, backend quality checks, frontend quality checks, key functional journeys, failure-path validation, and final reporting. When the G4 happy-path gate runs in automated CI, it SHALL use the deterministic CI provider path rather than depending on unmanaged external provider state.

#### Scenario: Gate sequence execution
- **WHEN** a release-candidate regression run starts
- **THEN** each mandatory gate is executed in the defined order and recorded with pass/fail status

#### Scenario: Automated CI executes G4 happy-path regression
- **WHEN** the integration workflow reaches the G4 happy-path gate in CI
- **THEN** the gate runs with explicit deterministic provider configuration prepared for that run
- **AND** the gate remains mandatory in the release decision flow

### Requirement: Gate stop policy
The regression workflow MUST enforce stop-on-fail for mandatory gates unless an explicit waiver is recorded.

#### Scenario: Mandatory gate failure
- **WHEN** a mandatory gate fails
- **THEN** subsequent release decision is blocked until the failure is fixed or an explicit waiver with risk justification is documented

