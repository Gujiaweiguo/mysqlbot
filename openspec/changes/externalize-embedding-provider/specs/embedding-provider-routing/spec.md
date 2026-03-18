## ADDED Requirements

### Requirement: Embedding provider selection is explicit
The system SHALL support explicit selection of an embedding provider so deployments can choose local or remote embedding execution without changing business-layer embedding callers.

#### Scenario: Deployment selects remote embedding provider
- **WHEN** configuration selects the remote embedding provider
- **THEN** query-time and persistence-time embedding operations use the remote provider implementation

#### Scenario: Deployment selects local embedding provider
- **WHEN** configuration selects the local embedding provider
- **THEN** query-time and persistence-time embedding operations use the local provider implementation

### Requirement: Embedding callers use a stable provider interface
The system MUST route terminology, data training, datasource, and table embedding operations through a stable provider interface that supports query embedding and document embedding.

#### Scenario: Terminology embedding save executes
- **WHEN** terminology save or backfill code requests embeddings
- **THEN** it does so through the shared embedding provider interface rather than directly instantiating a local HuggingFace model

#### Scenario: Datasource/table semantic selection executes
- **WHEN** datasource or table retrieval logic needs a query embedding
- **THEN** it does so through the shared embedding provider interface rather than directly instantiating a local HuggingFace model

### Requirement: Provider or model changes require controlled vector migration
The system MUST define a controlled migration path when the embedding provider or embedding model changes so stored vectors and retrieval thresholds remain consistent.

#### Scenario: Provider changes from local to remote
- **WHEN** operators switch the configured embedding provider or embedding model
- **THEN** the system exposes a documented re-embedding workflow and does not assume old vectors remain semantically compatible by default

#### Scenario: Deployment validates post-migration retrieval
- **WHEN** a provider/model migration is completed
- **THEN** operators can verify retrieval quality and review similarity-threshold settings for terminology, data training, and metadata selection

### Requirement: Startup and maintenance embedding backfill are provider-aware
The system MUST support embedding backfill flows that work with the selected provider and do not require local torch runtime when remote embedding is configured.

#### Scenario: Startup runs with remote embedding configured
- **WHEN** startup-triggered or maintenance-triggered backfill runs under the remote embedding provider
- **THEN** the system uses the remote provider path and applies the documented execution strategy for remote backfill

#### Scenario: Remote backfill is deferred by deployment policy
- **WHEN** deployment policy disables eager remote backfill at startup
- **THEN** the system preserves startup correctness and provides an explicit path to run the required backfill later
