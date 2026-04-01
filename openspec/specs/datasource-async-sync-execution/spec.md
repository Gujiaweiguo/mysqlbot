# datasource-async-sync-execution Specification

## Purpose
TBD - created by archiving change improve-datasource-1000-table-async-sync. Update Purpose after archive.
## Requirements
### Requirement: Large datasource sync SHALL execute as a durable async job
The system SHALL submit large datasource table sync requests as datasource-scoped async jobs when the async rollout flag is enabled and the selected table count exceeds the configured threshold. The submission endpoint SHALL return without waiting for full schema synchronization to complete.

#### Scenario: Async submit for large selection
- **WHEN** a datasource table selection exceeds the configured async threshold and the async feature flag is enabled
- **THEN** the system creates a datasource sync job
- **AND** the submission response returns the job identifier and initial status without waiting for schema sync completion

#### Scenario: Legacy path while flag is disabled
- **WHEN** the async feature flag is disabled
- **THEN** the existing synchronous datasource save behavior remains active
- **AND** no datasource sync job is created by the large-selection submit path

### Requirement: Datasource sync SHALL enforce one active job per datasource
The system SHALL prevent overlapping active sync jobs for the same datasource. A second large-sync submission for a datasource with an active job SHALL return deterministic conflict or dedupe behavior defined by the API contract.

#### Scenario: Duplicate submit while job is active
- **WHEN** a datasource already has an active sync job in a non-terminal state
- **THEN** a second large-sync submission for the same datasource does not start a second concurrent job
- **AND** the response follows the defined conflict or dedupe contract

### Requirement: Datasource sync progress SHALL be durably observable
The system SHALL persist durable sync job state, phase, and progress counts so that clients can recover progress after navigation, refresh, or worker restart. Polling status endpoints SHALL expose the authoritative job snapshot.

#### Scenario: Polling after refresh
- **WHEN** a client reloads the page during an active datasource sync job
- **THEN** the client can retrieve the current job state from the status endpoint
- **AND** the returned state reflects persisted progress rather than ephemeral in-memory worker state

#### Scenario: Worker interruption recovery
- **WHEN** a worker stops unexpectedly during an active datasource sync job
- **THEN** the system detects or reconciles the stale running state
- **AND** the job transitions to a recoverable terminal or retryable state according to the lifecycle rules

### Requirement: Visible datasource schema SHALL remain stable until finalize succeeds
The system SHALL keep the previously completed datasource schema visible to normal readers while a new async sync job is running. Newly staged schema rows SHALL NOT become the visible datasource schema until finalize succeeds.

#### Scenario: Read during running job
- **WHEN** a datasource sync job is in a non-terminal pre-finalize state
- **THEN** reads of datasource schema return the previously completed schema
- **AND** in-progress staged rows are not exposed through normal datasource schema reads

#### Scenario: Finalize success publishes new schema
- **WHEN** a datasource sync job reaches finalize success
- **THEN** subsequent datasource schema reads return the newly synchronized schema
- **AND** the job transitions to a succeeded terminal state

#### Scenario: Job failure preserves previous schema
- **WHEN** a datasource sync job fails before finalize succeeds
- **THEN** the previously completed datasource schema remains visible
- **AND** the failed job records terminal failure details without partially publishing staged schema

### Requirement: Sync execution SHALL batch writes and reuse remote metadata connections
The async datasource sync worker SHALL avoid per-field commit behavior and SHALL reuse remote datasource metadata connections within the execution lifecycle or chunk strategy. The hot path SHALL use bounded commit frequency and bounded worker concurrency.

#### Scenario: Batched local metadata writes
- **WHEN** a datasource sync job stages table and field metadata
- **THEN** the worker performs batched local writes with bounded commit frequency
- **AND** the worker does not commit once per field in the hot path

#### Scenario: Reused remote metadata access
- **WHEN** the worker introspects metadata for many tables in the same datasource sync job
- **THEN** it reuses remote connection or engine resources according to the batching strategy
- **AND** it does not create a new remote engine for every single table fetch in the hot path

### Requirement: Post-finalization embedding SHALL be bounded and non-corrupting
The system SHALL trigger datasource/table embedding follow-up only after schema finalize succeeds. Embedding follow-up failures SHALL NOT invalidate the finalized datasource schema.

#### Scenario: Embedding runs after finalize
- **WHEN** a datasource sync job finalizes successfully
- **THEN** post-sync embedding follow-up is dispatched after finalize
- **AND** schema publication is not blocked on synchronous embedding completion inside the submit request

#### Scenario: Embedding failure after finalize
- **WHEN** post-sync embedding follow-up fails after schema finalize success
- **THEN** the finalized datasource schema remains visible and valid
- **AND** the system records the follow-up failure in job or follow-up status information

