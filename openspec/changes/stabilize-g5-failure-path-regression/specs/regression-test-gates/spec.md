## MODIFIED Requirements

### Requirement: Full regression gate sequence
The system SHALL define a full regression process composed of mandatory gates that are executed in a deterministic order: runtime health, backend quality checks, frontend quality checks, key functional journeys, failure-path validation, and final reporting. When the G5 failure-path gate runs in automated CI, it SHALL use an explicitly configured deterministic mock-provider path rather than relying on unmanaged runner/container behavior.

#### Scenario: Automated CI executes G5 failure-path regression
- **WHEN** the integration workflow reaches the G5 failure-path gate in CI after G4 has passed
- **THEN** the gate runs with explicit deterministic failure-path configuration prepared for that run
- **AND** the gate remains mandatory in the release decision flow
