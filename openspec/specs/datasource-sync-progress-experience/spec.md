# datasource-sync-progress-experience Specification

## Purpose
TBD - created by archiving change improve-datasource-1000-table-async-sync. Update Purpose after archive.
## Requirements
### Requirement: Frontend SHALL provide recoverable progress for large datasource sync jobs
When the async datasource sync path is active, the frontend SHALL show progress and terminal status for large datasource sync jobs without requiring the user to keep a single request open. The frontend SHALL be able to recover active job status after reload or re-entry.

#### Scenario: Submit transitions into progress experience
- **WHEN** a user submits a large datasource sync under the async path
- **THEN** the frontend returns control immediately after submit
- **AND** the frontend displays a progress experience tied to the job identifier

#### Scenario: Recover after refresh
- **WHEN** a user refreshes or reopens the datasource view while a sync job is active
- **THEN** the frontend restores the active job state from the backend status endpoint
- **AND** the frontend does not submit a second job automatically

### Requirement: Frontend SHALL surface deterministic conflict and terminal states
The frontend SHALL present clear messaging for active-job conflicts, success, failure, and cancellation outcomes using the backend job contract. Terminal views SHALL expose aggregate counts and access to failure details defined by the contract.

#### Scenario: Conflict while job already active
- **WHEN** a user attempts to start a large datasource sync while another job is active for the same datasource
- **THEN** the frontend shows deterministic conflict or reuse messaging
- **AND** the UI does not imply that a second independent job is running

#### Scenario: Terminal failure summary
- **WHEN** a datasource sync job ends in a failed or cancelled terminal state
- **THEN** the frontend shows terminal status and aggregate result counts
- **AND** the user can identify that the new schema was not finalized if finalize did not succeed

### Requirement: Large datasource table selection SHALL remain usable at 1000-table scale
The frontend SHALL preserve a usable table selection experience for large datasource table lists by using large-list rendering patterns that avoid full DOM expansion of the selected table list.

#### Scenario: Large list remains navigable
- **WHEN** the datasource table selection view contains approximately 1000 candidate tables
- **THEN** the selection UI uses the established large-list rendering pattern
- **AND** the page does not rely on rendering all checkbox rows into the DOM at once

### Requirement: Async routing policy SHALL be backed by backend-controlled rollout settings
The frontend SHALL respect backend-backed async rollout settings and threshold policy rather than relying on a frontend-only hardcoded table-count rule for large sync behavior.

#### Scenario: Feature flag disabled
- **WHEN** the async rollout setting is disabled
- **THEN** the frontend follows the legacy datasource save path
- **AND** the async progress experience is not activated for large table selections

#### Scenario: Feature flag enabled above threshold
- **WHEN** the async rollout setting is enabled and the selected table count exceeds the backend-controlled threshold
- **THEN** the frontend uses the async submit and progress workflow
- **AND** the UI messaging reflects that execution is being handled as a background job rather than a blocking save

