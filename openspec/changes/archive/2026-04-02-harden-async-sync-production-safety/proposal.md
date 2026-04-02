## Why

The async datasource sync feature (1000+ tables) is functionally complete with performance optimization and Prometheus observability, but has three production-safety gaps that must be resolved before enabling `DATASOURCE_ASYNC_SYNC_ENABLED=true` in production: (1) a single table's introspection or staging failure aborts the entire job, wasting work on all other tables; (2) the "one active job per datasource" guard uses a read-then-write pattern with no database-level constraint, allowing race conditions under concurrent API load; (3) stale job recovery only runs at app startup, leaving hung workers undetected on long-running servers.

## What Changes

- Add per-table error isolation in the introspect and stage loops: each table's processing is wrapped in try/except, failed tables are counted and logged, and the job can complete with a new `PARTIAL` terminal status when some tables succeed but others fail.
- Replace the soft duplicate-job guard with a PostgreSQL partial unique index `(ds_id) WHERE status IN ('pending','running','finalizing')` enforced at the database level, catching `IntegrityError` on submit.
- Convert the startup-only stale job recovery into a periodic background task (configurable interval, default 5 minutes) so hung workers are detected and cleaned up on long-running servers.
- Add Alembic migration for the partial unique index.
- Add comprehensive test coverage for all three hardening changes.

## Capabilities

### New Capabilities

_None_ — all changes strengthen existing capabilities.

### Modified Capabilities

- `datasource-async-sync-execution`: Requirements changing — (1) per-table error isolation with partial success, (2) database-enforced one-active-job constraint, (3) periodic stale recovery replacing startup-only recovery.

## Impact

- **Database**: New Alembic migration adding a partial unique index on `datasource_sync_job`. Zero downtime — index creation is concurrent on PostgreSQL for existing data.
- **Backend API**: New `PARTIAL` job status value in responses. Existing `FAILED` behavior unchanged for fully-failed jobs. No new endpoints.
- **Backend code**: `sync_job_runtime.py` (per-table try/except, periodic recovery), `sync_job.py` (IntegrityError catch), `sync_job model` (PARTIAL enum value), `datasource.py` (per-table isolation in sync_fields).
- **Frontend**: Existing `isFailedSyncJobStatus` already checks for partial/failure keywords. The `PARTIAL` status will be treated as a warning (yellow) terminal state. Minimal or no frontend changes expected.
- **Dependencies**: No new external dependencies.
- **Rollback**: Set `DATASOURCE_ASYNC_SYNC_ENABLED=false` and restart. The partial unique index is benign when the async path is disabled.
