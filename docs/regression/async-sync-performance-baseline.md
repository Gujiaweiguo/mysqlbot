# Async Datasource Sync — Performance Baseline (2026-04-01)

## Environment

- **Host**: localhost PostgreSQL 15432 (dev container)
- **Datasource type**: pg
- **Table shape**: 5 columns each (id bigint PK, name text, score numeric, is_active boolean, created_at timestamp)
- **Max workers**: 4 (ThreadPool)
- **Progress throttle**: 2s

## Results

| Tables | Fields | Introspect | Stage | Post-process | Total |
|--------|--------|------------|-------|--------------|-------|
| 500    | 2,500  | 6.03s      | 8.93s | 0.10s        | 15.07s |
| 1,000  | 5,000  | 15.95s     | 21.38s| 0.27s        | 37.61s |

## Scaling

- **Introspect** (metadata fetch + field enumeration): ~12ms/table — near-linear.
- **Stage** (reconcile + prune + commit): ~18ms/table — near-linear.
- **Post-process** (embedding dispatch): negligible (<0.5s).
- **Total** at 1,000 tables ≈ 38s — well within the 1-hour stale timeout.

## Observations

1. Introspect is dominated by per-table `get_fields_from_context` calls; each call opens a SQLAlchemy session and queries `information_schema`. Parallelizing field introspection across tables could cut this time.
2. Stage is dominated by `_reconcile_single_table` per table (insert/update core_table + core_field rows). The single-commit-at-end pattern keeps DB round-trips low.
3. Post-process embedding dispatch fires 10 parallel threads (chunk_size=50) against the remote embedding API; latency depends on external API.
4. With 4 workers the job runs single-threaded for the sync phases (introspect + stage). The executor only parallelizes embedding batches.

## Artifacts

- `scripts/regression/generate_perf_schema.py` — creates N-table test schemas
- `scripts/regression/run_perf_baseline.py` — submits async job and waits for completion
- `common/utils/sync_job_runtime.py` — timing instrumentation (`sync_job_timing` JSON log line)

## Reproduce

```bash
cd /opt/code/mysqlbot/backend
# 1. Generate schema
uv run python scripts/regression/generate_perf_schema.py --count 500
# 2. Create datasource via SQLModel (see run_perf_baseline.py for pattern)
# 3. Enable async sync
#    Edit .env: DATASOURCE_ASYNC_SYNC_ENABLED=true
# 4. Run baseline
uv run python scripts/regression/run_perf_baseline.py <datasource_id>
# 5. Clean up
uv run python scripts/regression/generate_perf_schema.py --count 500 --drop
```
