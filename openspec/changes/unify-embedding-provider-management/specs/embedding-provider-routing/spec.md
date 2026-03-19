## MODIFIED Requirements

### Requirement: Embedding provider selection is explicit
The system SHALL support explicit selection of an embedding provider type so deployments and administrators can choose local or remote embedding execution without changing business-layer embedding callers.

#### Scenario: Deployment selects an OpenAI-compatible embedding provider
- **WHEN** configuration resolves to the `openai_compatible` provider type
- **THEN** query-time and persistence-time embedding operations use the OpenAI-compatible embedding implementation

#### Scenario: Deployment selects a local embedding provider
- **WHEN** configuration resolves to the `local` provider type
- **THEN** query-time and persistence-time embedding operations use the local provider implementation

#### Scenario: Administrator saves embedding configuration visually
- **WHEN** an administrator updates the active embedding configuration through the admin workflow
- **THEN** the resolved provider type becomes the runtime provider only according to the singleton lifecycle and enablement policy

### Requirement: Provider or model changes require controlled vector migration
The system MUST define a controlled migration path when the embedding provider or embedding model changes so stored vectors, retrieval thresholds, and administrative state remain consistent.

#### Scenario: Provider changes between supported provider types
- **WHEN** operators switch the configured embedding provider type or embedding model
- **THEN** the system exposes a documented re-embedding workflow and does not assume old vectors remain semantically compatible by default

#### Scenario: Administrator changes provider or model through the supplier-driven admin workflow
- **WHEN** a compatibility-sensitive embedding setting is changed in the admin UI
- **THEN** the system marks prior validation and activation state as stale until the new configuration is validated and reviewed
