## MODIFIED Requirements

### Requirement: The integration assistant SHALL generate copyable OpenClaw configuration text
The system SHALL generate copyable OpenClaw configuration text from current mysqlbot runtime settings so operators can paste it into OpenClaw without manual reconstruction. When OpenClaw onboarding depends on a mysqlbot API Key credential, the generated guidance SHALL distinguish the raw JWT token artifact used in configuration from the header-style `sk <jwt>` value used on outbound requests.

#### Scenario: Administrator copies generated OpenClaw configuration
- **WHEN** an administrator requests generated OpenClaw MCP configuration text
- **THEN** the system SHALL produce a copyable text block whose values reflect the current validated mysqlbot MCP settings
- **AND** the guidance SHALL identify the mysqlbot token artifact expected in configuration versus the header-style value sent at request time
