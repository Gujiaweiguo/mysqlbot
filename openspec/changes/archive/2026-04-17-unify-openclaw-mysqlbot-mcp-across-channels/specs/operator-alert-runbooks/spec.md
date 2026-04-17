## ADDED Requirements

### Requirement: Runbooks SHALL cover MCP-first OpenClaw operations
The system SHALL provide operator guidance for failures in the canonical MCP service, including startup, reachability, authentication, and capability discovery issues.

#### Scenario: Operator triages an MCP reachability alert
- **WHEN** an alert indicates the canonical mysqlbot MCP service is unavailable or unhealthy
- **THEN** the runbook SHALL identify the likely user impact, relevant endpoint or service boundary, and the first diagnostic steps to restore availability

### Requirement: Runbooks SHALL cover channel session-isolation failures
The system SHALL provide operator guidance for diagnosing session-scope errors or context leakage symptoms in supported OpenClaw channels.

#### Scenario: Operator investigates group-chat context leakage
- **WHEN** operators receive reports or alerts indicating possible OpenClaw group-chat session mix-up
- **THEN** the runbook SHALL identify which session identity inputs, logs, and channel metadata should be checked first
