# openclaw-integration-config-assistant Specification

## Purpose
Define the administrator-facing mysqlbot workflow for viewing validated OpenClaw MCP setup metadata and generating copyable onboarding configuration without misleading operators when setup is incomplete.

## Requirements
### Requirement: Administrators SHALL be able to view OpenClaw MCP connection settings in mysqlbot
The system SHALL provide an administrator-facing workflow in the mysqlbot web UI that displays the MCP connection parameters required to onboard OpenClaw.

#### Scenario: Administrator opens the OpenClaw integration assistant
- **WHEN** an administrator navigates to the OpenClaw integration assistant in mysqlbot
- **THEN** the UI SHALL display the current MCP endpoint, expected authentication scheme, and any required connection metadata needed for OpenClaw setup

### Requirement: The integration assistant SHALL generate copyable OpenClaw configuration text
The system SHALL generate copyable OpenClaw configuration text from current mysqlbot runtime settings so operators can paste it into OpenClaw without manual reconstruction. When OpenClaw onboarding depends on a mysqlbot API Key credential, the generated guidance SHALL distinguish the raw JWT token artifact used in configuration from the header-style `sk <jwt>` value used on outbound requests.

#### Scenario: Administrator copies generated OpenClaw configuration
- **WHEN** an administrator requests generated OpenClaw MCP configuration text
- **THEN** the system SHALL produce a copyable text block whose values reflect the current validated mysqlbot MCP settings
- **AND** the guidance SHALL identify the mysqlbot token artifact expected in configuration versus the header-style value sent at request time

### Requirement: Generated configuration SHALL reflect invalid or incomplete setup state
The system SHALL indicate when required MCP configuration is incomplete or invalid instead of generating misleading configuration text.

#### Scenario: MCP endpoint is not fully configured
- **WHEN** the administrator opens the integration assistant while required MCP runtime settings are missing or invalid
- **THEN** the UI SHALL identify the missing configuration state and SHALL NOT present the setup as ready for copy-paste onboarding
