## Context

The async datasource sync feature is functionally complete (DSYNC-001 through DSYNC-011, plus performance optimization and Prometheus metrics). The feature flag `DATASOURCE_ASYNC_SYNC_ENABLED` defaults to `false`. Before enabling it in production, three safety gaps must be addressed:

1. **No per-table error isolation**: A single table's introspection or staging failure throws an uncaught exception that aborts the entire sync job. For 1000-table schemas, this means one problematic table wastes all work on the other 999.

2. **Soft concurrency guard only**: `submit_datasource_sync_job()` uses a read-then-write pattern (`get_active_sync_job` → insert) with no database-level constraint. Under concurrent API requests, two transactions can both read "no active job" and both insert, creating duplicate running jobs for the same datasource.

3. **Startup-only stale recovery**: `recover_stale_sync_jobs()` runs exclusively at application startup. On a long-running server, if a worker thread hangs, the stale job is never detected or cleaned up until the next deployment restart.

Key files:
- `backend/common/utils/sync_job_runtime.py` — core execution runtime
- `backend/apps/datasource/crud/sync_job.py` — job CRUD and submission
- `backend/apps/datasource/crud/datasource.py` — `sync_fields()` stage logic
- `backend/apps/datasource/models/sync_job.py` — job model and status enum

## Goals / Non-Goals

**Goals:**
- Ensure a single table failure does not abort the entire sync job
- Enforce one-active-job-per-datasource at the database level (hard constraint)
- Detect and recover stale jobs periodically, not just at startup
- Maintain backward compatibility — no API contract changes beyond the new `PARTIAL` status value

**Non-Goals:**
- Retry mechanism for transient failures (Phase 2)
- Cancel/retry API endpoints (Phase 2)
- Runtime configuration toggling without restart
- Frontend UX changes (existing partial/failure handling already covers `PARTIAL`)

## Decisions

### D1: Per-table error isolation with `PARTIAL` status

**Decision**: Wrap each table's introspect + stage in a per-table `try/except` block. On failure, increment `failed_tables` counter and log the error, but continue processing remaining tables. After all tables are processed, if any failed but at least one succeeded, set job status to `PARTIAL`. If all failed, set to `FAILED`.

**Rationale**: This maximizes forward progress. A single bad table (e.g., permission denied on one view) should not prevent syncing 999 other tables. The `PARTIAL` status communicates partial success to the frontend.

**Alternative considered**: Collect all failures and abort. Rejected — this wastes work and provides no value over the current all-or-nothing behavior.

**Implementation**:
- In `sync_job_runtime.py`: wrap the introspect loop and `_reconcile_single_table()` calls in per-table try/except
- In `sync_job.py` model: add `PARTIAL = "partial"` to `SyncJobStatus` enum
- Add `failed_tables` counter to job progress tracking
- The existing `work_session.rollback()` on total failure remains — partial success still commits staged tables for the successful ones

**Important nuance**: Since `_reconcile_single_table` uses `auto_commit=False` and the final `work_session.commit()` is a single atomic transaction, we need to decide: commit per-table or commit all-at-once with per-table error tolerance?

**Chosen approach**: Switch to per-table commit for the stage phase. Each table's `_reconcile_single_table()` call commits independently. If it fails, we skip that table and continue. The finalize step (`_finalize_sync_table_prune`) remains a single commit since it's a prune operation. This trades the atomicity of the full stage for resilience — a fair trade at 1000-table scale where losing one table is acceptable but losing all is not.

### D2: PostgreSQL partial unique index for concurrency

**Decision**: Add a partial unique index:
```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_ds_one_active_sync_job
ON datasource_sync_job (ds_id) WHERE status IN ('pending', 'running', 'finalizing');
```

In `submit_datasource_sync_job()`, catch `IntegrityError` from the insert and treat it as "active job already exists" — return the existing active job info.

**Rationale**: Database-level constraints are the only reliable way to prevent race conditions in read-then-write patterns. The partial unique index ensures at most one active job per datasource regardless of transaction timing.

**Alternative considered**: `SELECT ... FOR UPDATE` in `get_active_sync_job()`. Rejected — this serializes all submissions (even for different datasources) and requires careful transaction management. The partial index is more targeted and has lower contention.

**Migration**: Use `CREATE UNIQUE INDEX CONCURRENTLY` to avoid locking the table during migration. The `CONCURRENTLY` keyword requires running outside a transaction block (`op.execute()` with `autocommit`).

### D3: Periodic stale recovery via asyncio background task

**Decision**: Add an `asyncio` background task that runs `recover_stale_sync_jobs()` on a configurable interval (default: 300 seconds / 5 minutes). The task starts during application lifespan setup alongside the existing startup recovery.

**Rationale**: The stale recovery logic already exists and works correctly. The only gap is that it runs once at startup. Making it periodic is a minimal change that closes the gap without introducing new infrastructure.

**Alternative considered**: APScheduler or Celery beat. Rejected — these add external dependencies and operational complexity for a single periodic task. A simple `asyncio.create_task` loop is sufficient.

**Implementation**:
- In `main.py` lifespan: spawn an `asyncio.Task` that loops `await asyncio.sleep(interval)` + calls the sync recovery function via `run_in_executor`
- Add `DATASOURCE_SYNC_JOB_STALE_RECOVERY_INTERVAL_SECONDS` config (default: 300)
- Handle graceful shutdown: cancel the task when lifespan shuts down

## Risks / Trade-offs

**[Risk] Per-table commit loses full-stage atomicity** → If the process crashes mid-stage, some tables are committed and others are not. Mitigation: The finalize step (`_finalize_sync_table_prune`) handles this correctly — it prunes tables not in the final set. A partial stage + finalize will produce a consistent result (just missing the tables that weren't staged).

**[Risk] Partial unique index migration on large tables** → If the `datasource_sync_job` table already has many rows, `CREATE INDEX CONCURRENTLY` takes time but does not block writes. Mitigation: The table is new (feature not yet enabled in production), so it should be small or empty.

**[Risk] Periodic recovery could mark a slow-but-valid job as stale** → A legitimate 2000-table sync could take > 1 hour. Mitigation: The stale timeout is already configurable (`DATASOURCE_SYNC_JOB_STALE_TIMEOUT_SECONDS`, default 3600). Admins should set this higher than the expected max sync duration.

**[Risk] `PARTIAL` status may confuse existing API consumers** → The `PARTIAL` value is new. Mitigation: The feature flag is off by default. Consumers only see this status after explicitly enabling async sync. The frontend already handles partial/warning states.
