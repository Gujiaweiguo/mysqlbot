## MODIFIED Requirements

### Requirement: Embedding provider selection is explicit
The system SHALL support explicit selection of an embedding provider so deployments and administrators can choose local or remote embedding execution without changing business-layer embedding callers.

#### Scenario: Deployment selects remote embedding provider
- **WHEN** configuration selects the remote embedding provider
- **THEN** query-time and persistence-time embedding operations use the remote provider implementation

#### Scenario: Deployment selects local embedding provider
- **WHEN** configuration selects the local embedding provider
- **THEN** query-time and persistence-time embedding operations use the local provider implementation

#### Scenario: Administrator saves embedding configuration visually
- **WHEN** an administrator updates the active embedding provider through the admin workflow
- **THEN** the selected provider becomes the runtime provider only according to the embedding configuration lifecycle and enablement policy

### Requirement: Provider or model changes require controlled vector migration
The system MUST define a controlled migration path when the embedding provider or embedding model changes so stored vectors, retrieval thresholds, and administrative state remain consistent.

#### Scenario: Provider changes from local to remote
- **WHEN** operators switch the configured embedding provider or embedding model
- **THEN** the system exposes a documented re-embedding workflow and does not assume old vectors remain semantically compatible by default

#### Scenario: Deployment validates post-migration retrieval
- **WHEN** a provider/model migration is completed
- **THEN** operators can verify retrieval quality and review similarity-threshold settings for terminology, data training, and metadata selection

#### Scenario: Administrator changes provider or model through the admin workflow
- **WHEN** a compatibility-sensitive embedding setting is changed in the admin UI
- **THEN** the system marks prior validation/activation state as stale until the new configuration is validated and reviewed
