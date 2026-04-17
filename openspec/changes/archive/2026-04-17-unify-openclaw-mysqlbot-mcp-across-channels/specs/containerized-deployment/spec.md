## ADDED Requirements

### Requirement: Dedicated MCP service SHALL be explicitly exposed in supported deployment shapes
The system SHALL define the dedicated mysqlbot MCP service as an explicit deployment concern, including startup configuration, port/path exposure, and environment-driven configuration in supported development and production topologies.

#### Scenario: Operator starts a supported deployment
- **WHEN** an operator starts a supported mysqlbot deployment that includes OpenClaw integration
- **THEN** the dedicated MCP service SHALL start with its declared configuration and SHALL be reachable through the documented canonical endpoint

### Requirement: Dedicated MCP service SHALL expose an independent health contract
The system SHALL expose a health signal for the dedicated MCP service so operators can distinguish MCP readiness from main web/API readiness.

#### Scenario: Operator checks service readiness
- **WHEN** an operator inspects service health after deployment
- **THEN** the system SHALL allow them to determine whether the MCP service is healthy independently from the main application service
