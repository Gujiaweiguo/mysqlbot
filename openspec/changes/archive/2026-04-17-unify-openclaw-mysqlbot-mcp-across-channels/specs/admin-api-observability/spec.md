## ADDED Requirements

### Requirement: MCP-originated OpenClaw traffic SHALL be observable
The system SHALL emit sufficient outcome, error, and latency signals for OpenClaw-originated MCP traffic so operators can detect channel-specific failures and degraded behavior.

#### Scenario: Operator inspects OpenClaw MCP traffic health
- **WHEN** OpenClaw clients invoke mysqlbot through the canonical MCP service
- **THEN** the system SHALL expose signals that distinguish MCP-originated requests and their outcomes from unrelated runtime traffic

### Requirement: Capability discovery and connection failures SHALL surface actionable signals
The system SHALL expose observable signals for MCP connection failures, capability discovery failures, and channel-specific error spikes that affect OpenClaw onboarding or runtime use.

#### Scenario: MCP capability discovery starts failing for a channel
- **WHEN** a supported OpenClaw channel experiences repeated MCP connection or capability discovery failures
- **THEN** the system SHALL expose signals that allow operators to identify the failure mode and affected integration path
