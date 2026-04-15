## MODIFIED Requirements

### Requirement: Alerts include operator-facing triage guidance
The system SHALL define operator guidance for each critical admin/runtime alert introduced by this change, including OpenClaw-originated mysqlbot integration alerts.

#### Scenario: Operator receives an alert for a critical admin/runtime API
- **WHEN** an alert is triggered for a monitored admin/runtime API
- **THEN** the operator SHALL have guidance describing likely user impact, the relevant endpoint group, and the first diagnostic steps

#### Scenario: Operator receives an alert for the OpenClaw integration path
- **WHEN** an alert is triggered for OpenClaw-originated mysqlbot traffic such as auth failures, timeout spikes, or adapter error-rate degradation
- **THEN** the operator SHALL have guidance describing the likely caller impact, the relevant integration endpoint group, and the first diagnostic steps

### Requirement: Runbook guidance maps to the restored admin capabilities
The system SHALL provide triage guidance specific to the restored admin/runtime capabilities, including authentication, platform integration, operation logs, custom prompts, appearance settings, AI model validation, permissions, and the OpenClaw integration path.

#### Scenario: Operator triages a feature-specific alert
- **WHEN** an alert corresponds to one of the restored admin/runtime capability groups
- **THEN** the guidance SHALL identify the related page(s), endpoint(s), and the first place to inspect in logs or monitoring output

#### Scenario: Operator triages an OpenClaw integration alert
- **WHEN** an alert corresponds to the OpenClaw integration path
- **THEN** the guidance SHALL identify the related contract operation, credential or workspace scope to inspect, and the first integration-specific logs or metrics to inspect
