## MODIFIED Requirements

### Requirement: Embedding configuration is managed through an admin workflow
The system SHALL provide an administrator-facing embedding workflow that follows the current supplier + model interaction style used by AI model configuration while preserving singleton embedding state.

#### Scenario: Administrator selects supplier and model
- **WHEN** an administrator configures embedding in the UI
- **THEN** the workflow presents supplier selection first, model selection second, and then the provider-specific configuration fields required by the selected supplier/provider type

#### Scenario: Administrator saves embedding configuration
- **WHEN** an administrator saves updated embedding configuration
- **THEN** the system persists the normalized provider-type configuration without automatically enabling embedding

### Requirement: Embedding is disabled until validation succeeds
The system MUST treat embedding as disabled until the current configuration has passed provider-specific validation.

#### Scenario: Configuration has not been validated yet
- **WHEN** an administrator has saved embedding configuration but has not run or passed validation
- **THEN** the system marks embedding as disabled and does not allow enablement-dependent status to appear as active

#### Scenario: Validation succeeds
- **WHEN** the administrator validates the current embedding configuration successfully
- **THEN** the system may transition to a verified-but-disabled state and allow the administrator to enable embedding explicitly

#### Scenario: Provider or model change invalidates prior enabled state
- **WHEN** an administrator changes the embedding supplier, provider type, embedding model, or other compatibility-sensitive setting after embedding was previously enabled
- **THEN** the system MUST not continue treating the configuration as fully current until the new configuration is re-validated and reviewed

### Requirement: Validation exercises the selected supplier/provider contract
The system SHALL validate embedding configuration by performing a provider-specific runtime probe rather than relying only on static field checks.

#### Scenario: Validation fails because supplier protocol is unsupported
- **WHEN** the administrator chooses a supplier whose embedding contract is not implemented in the current release
- **THEN** the system reports a clear validation failure that explains the supplier is not yet supported for embedding

#### Scenario: Validation fails after a provider/model change
- **WHEN** an administrator updates a compatibility-sensitive embedding setting and validation fails
- **THEN** the system keeps embedding in a non-fully-enabled cautionary state and clearly reports that the new configuration is not safe to activate

### Requirement: Runtime behavior respects embedding enablement state
The system MUST ensure embedding-dependent runtime paths do not behave as fully enabled when embedding is disabled, unverified, or stale.

#### Scenario: Persisted admin config overrides bootstrap defaults
- **WHEN** a persisted administrator-managed embedding configuration exists
- **THEN** runtime behavior follows the persisted embedding state and normalized provider configuration rather than assuming environment bootstrap defaults remain authoritative
