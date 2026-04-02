## 1. Per-Table Error Isolation

- [x] 1.1 Add `PARTIAL = "partial"` to `SyncJobStatus` enum in `backend/apps/datasource/models/sync_job.py`, update terminal status handling to include `PARTIAL`
- [x] 1.2 Confirm `failed_tables` integer column already exists in `datasource_sync_job` model and migration history
- [x] 1.3 Refactor `sync_job_runtime.py` introspect loop: wrap each table's `get_fields_from_context()` call in per-table `try/except`, increment `failed_tables` counter on exception, log error with table name, continue to next table
- [x] 1.4 Refactor `sync_job_runtime.py` stage loop: isolate per-table failures while preserving visibility guarantees, only finalize/publish when all tables stage successfully, and keep old schema visible on `PARTIAL` / `FAILED`
- [x] 1.5 Update terminal status logic in `sync_job_runtime.py`: if `failed_tables > 0` and `completed_tables > 0`, set status to `PARTIAL`; if all tables failed, set status to `FAILED`; if no failures, set status to `SUCCEEDED`
- [x] 1.6 Confirm `failed_tables` is already returned in the job status API response and update progress accounting for successful stage counts

## 2. Database-Level Concurrency Guard

- [x] 2.1 Create Alembic migration with `CREATE UNIQUE INDEX CONCURRENTLY uq_ds_one_active_sync_job ON datasource_sync_job (ds_id) WHERE status IN ('pending', 'running', 'finalizing')` — use `op.execute()` with `autocommit` block for concurrent index creation
- [x] 2.2 Update `submit_datasource_sync_job()` in `sync_job.py` to catch `IntegrityError` on insert and treat it as "active job already exists" — return existing active job info with `reused_active_job=True`
- [x] 2.3 Keep migration `069_ds_sync_job_partial_unique_index.py` as the source of truth for the PostgreSQL partial unique index; do not add a misleading SQLModel declaration that cannot express the partial predicate correctly

## 3. Periodic Stale Recovery

- [x] 3.1 Add `DATASOURCE_SYNC_JOB_STALE_RECOVERY_INTERVAL_SECONDS: int = 300` config setting to `backend/common/core/config.py`
- [x] 3.2 Create periodic stale recovery task in `sync_job_runtime.py`: loop with `asyncio.sleep(interval)`, call `recover_stale_sync_jobs()` via `run_in_executor`, handle graceful shutdown
- [x] 3.3 Wire the periodic task into FastAPI lifespan in `main.py`: start the task alongside existing startup recovery and cancel it on shutdown

## 4. Tests

- [x] 4.1 Test per-table error isolation and `PARTIAL` status behavior, including terminal-state plumbing and publish contract
- [x] 4.2 Test all-tables-failure and visibility preservation when all introspection work fails
- [x] 4.3 Test concurrent submission guard behavior via active-job reuse and `IntegrityError` handling path
- [x] 4.4 Test periodic stale recovery and visibility guarantees on partial failure / rollback scenarios
- [x] 4.5 Run targeted regression suite for async sync contracts, runner logic, visibility guarantees, and `main.py`; run changed-files lint gate successfully

## Final Verification Wave

- [x] F1 Oracle review: verify error isolation logic is correct — no silent exception swallowing, no data corruption on partial / failed runs
- [x] F2 Oracle review: verify partial unique index migration is safe for production deployment — no table locks, works on empty and populated tables
- [x] F3 Build gate: changed-files `bash scripts/lint.sh` + targeted async-sync `uv run pytest` pass with zero errors on changed files
- [x] F4 Spec compliance: async sync execution scenarios for `PARTIAL`, `FAILED`, visibility preservation, concurrency guard, and stale recovery are implemented and covered by tests
