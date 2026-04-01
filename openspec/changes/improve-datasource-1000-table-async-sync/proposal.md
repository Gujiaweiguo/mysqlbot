## Why

Datasource table selection currently becomes unreliable at large scale because the save path synchronously introspects remote schema metadata and writes local table/field rows with overly granular commits. The system already warns after 30 selected tables, but 1000-table support now needs to become a first-class capability with durable async execution, observable progress, and safe rollout.

## What Changes

- Introduce datasource-scoped async sync jobs for large table selections instead of relying on a single long-running request.
- Add durable job state, progress, conflict handling, finalization rules, and feature-flagged rollout for large sync execution.
- Refactor datasource schema sync internals to batch writes, reuse remote connections, and defer post-sync embedding safely.
- Add frontend progress and recovery UX for long-running datasource sync operations.
- Preserve the existing small-sync path when the new rollout flag is disabled.

## Capabilities

### New Capabilities
- `datasource-async-sync-execution`: Submit, run, observe, and finalize large datasource schema sync jobs safely.
- `datasource-sync-progress-experience`: Present recoverable progress, conflict, and terminal status for datasource sync jobs in the frontend.

### Modified Capabilities
- None.

## Impact

- Affected backend code: `backend/apps/datasource/api/`, `backend/apps/datasource/crud/`, `backend/apps/db/`, `backend/common/utils/`, `backend/alembic/`
- Affected frontend code: `frontend/src/views/ds/`, `frontend/src/api/datasource.ts`, `frontend/src/i18n/`
- New persistence: datasource sync job model/table and indexes
- API impact: new async submit/status endpoints and feature-flagged routing for large datasource sync
- Operational impact: bounded worker concurrency, default-off rollout flag, and explicit progress semantics
