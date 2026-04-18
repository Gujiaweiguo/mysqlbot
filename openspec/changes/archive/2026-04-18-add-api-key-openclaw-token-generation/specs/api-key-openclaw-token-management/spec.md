## ADDED Requirements

### Requirement: API Key management SHALL generate OpenClaw-ready tokens from existing API keys
The API Key management UI SHALL let the user generate a service token from an existing API key's `access_key` and `secret_key` so the user does not need to reconstruct the OpenClaw credential manually outside mysqlbot.

#### Scenario: User generates a token for an API key
- **WHEN** the user requests token generation for an API key in the API Key management UI
- **THEN** the UI SHALL derive a JWT token from that API key's `access_key` and `secret_key`
- **AND** the generated token SHALL be suitable for the existing `X-SQLBOT-ASK-TOKEN` authentication contract

### Requirement: API Key management SHALL support revealing and copying generated token artifacts
The API Key management UI SHALL let the user reveal and copy both the raw generated JWT token and a header-style `sk <jwt>` variant derived from the same API key.

#### Scenario: User copies raw JWT token for OrchestratorAgent configuration
- **WHEN** the user requests the generated token artifact intended for OrchestratorAgent configuration
- **THEN** the UI SHALL expose the raw JWT value without the `sk ` prefix
- **AND** the UI SHALL provide a copy action for that raw JWT value

#### Scenario: User copies header-style token value for direct callers
- **WHEN** the user requests the header-style credential form for a generated token
- **THEN** the UI SHALL expose the value as `sk <jwt>`
- **AND** the UI SHALL provide a copy action for that header-style value

### Requirement: API Key management SHALL explain token artifact usage
The API Key management UI SHALL distinguish among raw API key values, the generated JWT token, and the `sk <jwt>` header-style value so users know which artifact belongs in external integrations.

#### Scenario: User views generated token guidance
- **WHEN** the UI displays generated token outputs
- **THEN** the UI SHALL explain that OrchestratorAgent stores the raw JWT token as configuration
- **AND** the UI SHALL explain that the `sk <jwt>` value is the header-style form used on outbound requests

### Requirement: Generated token workflow SHALL preserve the current auth contract
The generated token workflow SHALL preserve the existing OpenClaw authentication contract instead of introducing a new token format or header scheme.

#### Scenario: Generated token is used with the current OpenClaw contract
- **WHEN** a user copies a generated token artifact from the API Key UI
- **THEN** the copied values SHALL remain compatible with the existing `X-SQLBOT-ASK-TOKEN` + `sk` scheme
- **AND** the workflow SHALL NOT require downstream callers to adopt a new authentication contract
