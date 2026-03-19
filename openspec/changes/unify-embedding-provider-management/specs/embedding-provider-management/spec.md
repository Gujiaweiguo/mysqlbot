## ADDED Requirements

### Requirement: Embedding configuration uses supplier-driven UX with provider-type routing
The system SHALL let administrators configure embeddings by selecting a supplier and model through a supplier-driven UI, while the backend normalizes the selection into an explicit provider type for runtime behavior.

#### Scenario: Administrator selects a supported supplier
- **WHEN** an administrator chooses an embedding supplier in the UI
- **THEN** the form shows the supplier-appropriate model and connection fields and the backend resolves the selection into the correct provider type

#### Scenario: Provider type is derived from supplier selection
- **WHEN** a saved supplier/model pair is submitted
- **THEN** the system stores or derives the provider type needed for runtime routing rather than treating the supplier label itself as the runtime adapter key

### Requirement: First-rollout remote embedding validation uses the shared OpenAI-compatible contract
The system MUST validate embedding configuration using the shared OpenAI-compatible embeddings contract for the first supported supplier set.

#### Scenario: Supported supplier validation
- **WHEN** the selected provider type is `openai_compatible`
- **THEN** validation uses an OpenAI-compatible embeddings probe against the configured base URL and model

#### Scenario: Unsupported supplier contract is selected
- **WHEN** an administrator selects a supplier whose embedding contract is not implemented
- **THEN** the system reports that the supplier is not currently supported for embeddings and does not enable embedding

### Requirement: New config writes use provider-type structure
The system MUST persist embedding configuration using the new provider-type-oriented structure even if older deployments still contain legacy `remote/local` configuration data.

#### Scenario: Legacy config is read
- **WHEN** the system loads an existing legacy embedding configuration
- **THEN** it normalizes the data into the current provider-type view for API responses and runtime use

#### Scenario: Administrator saves config after migration
- **WHEN** an administrator saves embedding configuration after the new structure is available
- **THEN** the stored configuration uses the provider-type structure rather than the old `remote/local` shape

### Requirement: Embedding lifecycle remains singleton and guarded
The system MUST preserve singleton embedding lifecycle semantics even when the UI becomes supplier-driven.

#### Scenario: Administrator saves new supplier/model configuration
- **WHEN** embedding supplier or model changes are saved
- **THEN** embedding does not automatically enable and the system enters a state that requires validation and risk review

#### Scenario: Provider or model change risks vector compatibility
- **WHEN** an administrator changes a compatibility-sensitive embedding setting
- **THEN** the system marks the configuration as requiring reindex review before safe enablement
