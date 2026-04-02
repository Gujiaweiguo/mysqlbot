## MODIFIED Requirements

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

## ADDED Requirements

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
