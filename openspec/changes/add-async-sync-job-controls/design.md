## Context

The async datasource sync workflow now has durable jobs, progress tracking, database-level active-job protection, periodic stale recovery, and safe `PARTIAL` handling that preserves visible schema on non-successful runs. What it still lacks is an operator control plane: once a job is queued or running, backend operators cannot cancel it, and a failed or partial job cannot be retried without reconstructing the original request manually.

This change is intentionally backend-only for the first iteration. The current frontend already understands terminal job states, but there is no UI button yet. The backend needs deterministic cancel and retry semantics first so operators can use the API directly and frontend integration can remain a follow-up.

## Goals / Non-Goals

**Goals:**
- Add a backend cancel endpoint for active datasource sync jobs.
- Add a backend retry endpoint for terminal datasource sync jobs.
- Make worker cancellation cooperative and safe: stop at phase boundaries and never publish schema after cancellation.
- Preserve the existing one-active-job-per-datasource constraint and visibility guarantees.
- Add targeted tests for cancel, retry, and conflict behavior.

**Non-Goals:**
- Frontend UI changes.
- Force-killing worker threads.
- Retrying in-place on the same job record.
- General-purpose background job framework changes outside datasource sync.

## Decisions

### D1: Cancellation is cooperative, not preemptive

The cancel endpoint will mark the job as `CANCELLED` in durable state. The worker will check current job state before entering major boundaries (before introspect work, during per-table loops, before finalize, and before embedding follow-up). If the job has been cancelled, the worker stops cleanly and rolls back unpublished work.

**Why this approach:** Python threadpool workers are not safely killable. Cooperative cancellation is predictable, testable, and preserves data consistency.

**Alternative considered:** force-stopping the worker thread. Rejected because it is unsafe and can leave DB work in an indeterminate state.

### D2: Retry creates a new job and reuses `requested_tables`

Retry will never mutate or resurrect the old job row. Instead, it will read the old job's `requested_tables`, validate that the source job is terminal (`FAILED`, `PARTIAL`, or `CANCELLED`), and submit a brand-new job through the existing submission path.

**Why this approach:** it preserves immutable job history, keeps metrics and auditability clean, and naturally reuses the existing active-job dedupe logic.

**Alternative considered:** resetting the old job back to `PENDING`. Rejected because it destroys lifecycle history and complicates observability.

### D3: Cancelled / partial / failed jobs never publish schema

The current runtime already guarantees that only full success reaches finalize-and-publish. This change keeps that invariant and makes it explicit for cancellation checks. If cancellation is detected before finalize succeeds, the worker rolls back the `work_session` and exits without publishing.

**Why this approach:** it keeps the user-visible schema model simple — readers only ever see the previous stable schema or the fully finalized new schema.

### D4: API contract remains minimal and backend-first

The new endpoints will return the same job response style already used in datasource sync APIs. Cancel returns current job status after transition; retry returns a normal submit response for the new job.

**Why this approach:** it avoids inventing new response shapes and makes frontend adoption straightforward later.

## Risks / Trade-offs

- **[Risk] Cancellation may not stop immediately** → Cooperative checks only occur at safe boundaries. Mitigation: check at every table iteration and before finalize so stop latency remains bounded.
- **[Risk] Retry after transient active-job race** → A retry request could race with another active job for the same datasource. Mitigation: reuse the existing DB-level active-job constraint and `IntegrityError` handling.
- **[Risk] Cancel during post-process embedding** → Schema may already be published by then. Mitigation: define cancellation as preventing further sync work before publish; after publish, cancel only affects remaining follow-up behavior and does not roll back finalized schema.
- **[Risk] API misuse against non-terminal / terminal jobs** → Invalid state transitions could confuse operators. Mitigation: reject cancel on terminal jobs and reject retry on non-terminal jobs with deterministic errors.

## Migration Plan

1. Add backend endpoints and CRUD helpers.
2. Add cooperative cancellation checks in runtime.
3. Add tests for state transitions and visibility protection.
4. Deploy without frontend changes.
5. Optionally add frontend buttons in a follow-up change.

Rollback: revert the backend code and stop using the new endpoints. No data migration is required.

## Open Questions

- Should retry be allowed for `SUCCEEDED` jobs to support deliberate re-sync of the exact same table set? Current recommendation: no, keep retry limited to unsuccessful terminal jobs.
- Should cancel during post-process embedding mark the job as `CANCELLED` or leave it `SUCCEEDED` with follow-up skipped? Current recommendation: once finalize succeeds, keep the sync result terminal state stable and treat cancellation as best-effort only before publish.
