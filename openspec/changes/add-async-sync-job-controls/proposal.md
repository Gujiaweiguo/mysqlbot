## Why

The async datasource sync flow is now production-safe, but operators still lack backend controls when a job is stuck, partially fails, or needs to be retried without manually resubmitting table selections. Adding cooperative cancel and deterministic retry closes the operational gap between observability and actionable control.

## What Changes

- Add a backend cancel endpoint for active datasource sync jobs.
- Add a backend retry endpoint for terminal datasource sync jobs.
- Teach the worker to cooperatively stop on cancellation at phase boundaries.
- Preserve existing schema visibility guarantees: cancelled, partial, and failed jobs must not publish new schema.
- Add tests covering cancel-before-run, cancel-during-run, retry-after-terminal, and active-job conflict handling.

## Capabilities

### New Capabilities

_None_ — this change extends the existing async sync execution lifecycle.

### Modified Capabilities

- `datasource-async-sync-execution`: extend the datasource sync job lifecycle to support backend cancel and retry controls, including cooperative worker cancellation and retry from terminal jobs.

## Impact

- **Backend API**: new `POST /datasource/syncJob/{job_id}/cancel` and `POST /datasource/syncJob/{job_id}/retry` endpoints.
- **Runtime behavior**: sync workers must check for cancellation and exit before publish.
- **Data safety**: cancelled and retried jobs continue to respect one-active-job-per-datasource and schema visibility rules.
- **Tests**: additional runner / contract / visibility tests for cancel and retry semantics.
- **Dependencies**: no new external dependencies.
