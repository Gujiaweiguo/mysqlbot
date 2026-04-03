# datasource-async-sync-execution Specification

## Purpose
Execute large datasource schema sync operations as durable async jobs with exclusive-per-datasource constraints, schema-stability guarantees, batched writes, cooperative cancellation, retry controls, and per-table failure isolation.
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
The system SHALL prevent overlapping active sync jobs for the same datasource using a database-level partial unique constraint. A second large-sync submission for a datasource with an active job SHALL return deterministic conflict or dedupe behavior defined by the API contract. The uniqueness constraint SHALL be enforced at the database level via a partial unique index on `(ds_id) WHERE status IN ('pending', 'running', 'finalizing')`.

#### Scenario: Duplicate submit while job is active
- **WHEN** a datasource already has an active sync job in a non-terminal state
- **THEN** a second large-sync submission for the same datasource does not start a second concurrent job
- **AND** the response follows the defined conflict or dedupe contract
- **AND** the database-level partial unique index prevents duplicate active jobs even under concurrent API requests

#### Scenario: Concurrent submission race condition
- **WHEN** two concurrent API requests attempt to submit sync jobs for the same datasource simultaneously
- **THEN** at most one job is created due to the database-level constraint
- **AND** the second submission catches the constraint violation and returns the existing active job information

### Requirement: Datasource sync progress SHALL be durably observable
The system SHALL persist durable sync job state, phase, and progress counts so that clients can recover progress after navigation, refresh, or worker restart. Polling status endpoints SHALL expose the authoritative job snapshot. The system SHALL periodically detect and recover stale running jobs, not only at application startup.

#### Scenario: Polling after refresh
- **WHEN** a client reloads the page during an active datasource sync job
- **THEN** the client can retrieve the current job state from the status endpoint
- **AND** the returned state reflects persisted progress rather than ephemeral in-memory worker state

#### Scenario: Worker interruption recovery
- **WHEN** a worker stops unexpectedly during an active datasource sync job
- **THEN** the system detects or reconciles the stale running state
- **AND** the job transitions to a recoverable terminal or retryable state according to the lifecycle rules

#### Scenario: Periodic stale detection on long-running server
- **WHEN** a server has been running for longer than the stale recovery interval and a sync job has been in a running state beyond the stale timeout
- **THEN** the system detects the stale job during the periodic background sweep
- **AND** the stale job is marked as FAILED with an appropriate error summary
- **AND** no restart is required for detection to occur

### Requirement: Visible datasource schema SHALL remain stable until finalize succeeds
The system SHALL keep the previously completed datasource schema visible to normal readers while a new async sync job is running. Newly staged schema rows SHALL NOT become the visible datasource schema until finalize succeeds. Jobs that end in `failed`, `partial`, or `cancelled` before finalize success SHALL preserve the previously completed datasource schema.

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

#### Scenario: Partial job preserves previous schema
- **WHEN** a datasource sync job reaches a `partial` terminal state before finalize succeeds
- **THEN** the previously completed datasource schema remains visible
- **AND** the partial job records aggregate failure details without partially publishing staged schema

#### Scenario: Cancelled job preserves previous schema
- **WHEN** a datasource sync job is cancelled before finalize succeeds
- **THEN** the previously completed datasource schema remains visible
- **AND** the cancelled job does not publish partially staged schema

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

### Requirement: Datasource sync jobs SHALL support backend cancel controls
The system SHALL expose a backend cancel operation for datasource sync jobs in active non-terminal states. Cancellation SHALL be cooperative: the worker checks for cancellation at safe execution boundaries, stops further sync work, and SHALL NOT publish new schema unless finalize already succeeded before cancellation was observed.

#### Scenario: Cancel a pending or running sync job
- **WHEN** an operator sends a cancel request for a datasource sync job in `pending`, `running`, or `finalizing`
- **THEN** the job transitions to `cancelled`
- **AND** the worker stops further sync work at the next safe cancellation boundary

#### Scenario: Cancelled job preserves previous schema before finalize
- **WHEN** a sync job is cancelled before finalize succeeds
- **THEN** the previously completed datasource schema remains visible
- **AND** no partially staged schema is published

#### Scenario: Cancel request for terminal job is rejected
- **WHEN** an operator sends a cancel request for a job already in `succeeded`, `failed`, `partial`, or `cancelled`
- **THEN** the system rejects the request with a deterministic error
- **AND** the terminal job state remains unchanged

### Requirement: Datasource sync jobs SHALL support backend retry controls
The system SHALL expose a backend retry operation for terminal datasource sync jobs. Retry SHALL create a brand-new job using the source job's stored `requested_tables` and SHALL continue to enforce the one-active-job-per-datasource constraint.

#### Scenario: Retry a failed, partial, or cancelled sync job
- **WHEN** an operator sends a retry request for a job in `failed`, `partial`, or `cancelled`
- **THEN** the system creates a new datasource sync job using the original `requested_tables`
- **AND** the response returns the new job identifier and submit status contract

#### Scenario: Retry while another active job exists
- **WHEN** an operator retries a terminal job for a datasource that already has an active job
- **THEN** the retry does not create a second concurrent active job
- **AND** the response follows the existing active-job dedupe or conflict contract

#### Scenario: Retry request for non-terminal job is rejected
- **WHEN** an operator sends a retry request for a job in `pending`, `running`, or `finalizing`
- **THEN** the system rejects the request with a deterministic error
- **AND** no new job is created

### Requirement: Sync execution SHALL isolate per-table failures without aborting the entire job
The system SHALL wrap each table's introspection and staging in per-table error isolation. When a single table's processing fails, the system SHALL log the failure, increment a failed-table counter, and continue processing remaining tables. The job SHALL complete with a `PARTIAL` status when at least one table succeeds and at least one table fails.

#### Scenario: Single table introspection failure during large sync
- **WHEN** a sync job is processing 1000 tables and one table's metadata introspection raises an exception
- **THEN** the system logs the failed table name and error
- **AND** the system increments the failed-table counter
- **AND** the remaining 999 tables continue to be processed
- **AND** the job completes with `PARTIAL` status

#### Scenario: Partial job does not publish a partial schema
- **WHEN** a datasource sync job completes with a `partial` terminal state before finalize succeeds
- **THEN** the previously completed datasource schema remains visible
- **AND** the system does not publish partially staged schema

#### Scenario: All tables fail during sync
- **WHEN** every table in a sync job fails during introspection or staging
- **THEN** the job is marked as `FAILED` with an error summary
- **AND** no staged schema is finalized

#### Scenario: Per-table stage failure still produces a partial terminal state
- **WHEN** a datasource sync job stages metadata for multiple tables and at least one table fails during staging
- **THEN** the job completes with `PARTIAL` status
- **AND** the job records aggregate failure details without publishing a partial schema
