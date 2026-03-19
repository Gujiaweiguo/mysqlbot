## ADDED Requirements

### Requirement: Embedding configuration is managed through an admin workflow
The system SHALL provide an administrator-facing workflow for viewing and editing the active embedding configuration without requiring direct environment-variable edits.

#### Scenario: Administrator opens embedding configuration
- **WHEN** an administrator navigates to the embedding configuration workflow
- **THEN** the system shows the current embedding provider settings and the current embedding runtime state

#### Scenario: Administrator saves embedding configuration
- **WHEN** an administrator saves updated embedding provider settings
- **THEN** the system persists the configuration without automatically enabling embedding

### Requirement: Embedding is disabled until validation succeeds
The system MUST treat embedding as disabled until the current configuration has passed provider validation.

#### Scenario: Configuration has not been validated yet
- **WHEN** an administrator has saved embedding configuration but has not run or passed validation
- **THEN** the system marks embedding as disabled and does not allow enablement-dependent status to appear as active

#### Scenario: Validation succeeds
- **WHEN** the administrator validates the current embedding configuration successfully
- **THEN** the system may transition to a verified-but-disabled state and allow the administrator to enable embedding explicitly

#### Scenario: Provider or model change invalidates prior enabled state
- **WHEN** an administrator changes the embedding provider, embedding model, or other compatibility-sensitive setting after embedding was previously enabled
- **THEN** the system MUST not continue treating the configuration as fully current until the new configuration is re-validated and reviewed

### Requirement: Validation exercises the real provider contract
The system SHALL validate embedding configuration by performing a provider-specific runtime probe rather than relying only on static field checks.

#### Scenario: Remote provider validation succeeds
- **WHEN** the current configuration points to a reachable remote embedding provider with a valid model identifier
- **THEN** the system reports validation success based on a real embedding probe

#### Scenario: Validation fails
- **WHEN** the provider cannot generate a test embedding because of connectivity, authentication, or model errors
- **THEN** the system reports validation failure and keeps embedding disabled

### Requirement: Provider or model changes surface reindex risk
The system MUST signal that embedding vectors may need regeneration when operators change the provider, model, or equivalent compatibility-sensitive settings.

#### Scenario: Administrator changes embedding provider
- **WHEN** the administrator saves a new provider or embedding model
- **THEN** the system marks the embedding configuration as requiring caution and informs the administrator that re-embedding may be necessary

#### Scenario: Administrator reviews state after provider/model change
- **WHEN** the administrator returns to the embedding configuration workflow after a compatibility-sensitive change
- **THEN** the workflow shows that prior validation/enabled state should not be treated as fully current until the new configuration is validated and reviewed

#### Scenario: Validation fails after a previously enabled configuration change
- **WHEN** an administrator updates a compatibility-sensitive embedding setting and validation fails
- **THEN** the system keeps embedding in a non-fully-enabled cautionary state and clearly reports that the new configuration is not safe to activate

### Requirement: Runtime behavior respects embedding enablement state
The system MUST ensure embedding-dependent runtime paths do not behave as fully enabled when embedding is disabled or unverified.

#### Scenario: Embedding remains disabled
- **WHEN** embedding is disabled or still unverified
- **THEN** embedding-dependent enhancement paths remain inactive or degrade safely according to system policy

#### Scenario: Embedding is enabled after validation
- **WHEN** the administrator enables embedding after successful validation
- **THEN** embedding-capable runtime paths may use the configured provider according to the current embedding policy

#### Scenario: Persisted admin config overrides bootstrap defaults
- **WHEN** a persisted administrator-managed embedding configuration exists
- **THEN** runtime behavior follows the persisted embedding state and configuration rather than assuming environment bootstrap defaults remain authoritative
