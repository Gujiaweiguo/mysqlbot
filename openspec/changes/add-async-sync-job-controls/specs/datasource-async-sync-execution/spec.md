## ADDED Requirements

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

## MODIFIED Requirements

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
