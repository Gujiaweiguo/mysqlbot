# Async Datasource Sync — Performance Baseline (2026-04-01)

## Environment

- **Host**: localhost PostgreSQL 15432 (dev container)
- **Datasource type**: pg
- **Table shape**: 5 columns each (id bigint PK, name text, score numeric, is_active boolean, created_at timestamp)
- **Max workers**: 4 (ThreadPool)
- **Progress throttle**: 2s

## Results (Parallel Introspect — 2026-04-01)

| Tables | Fields | Introspect | Stage | Post-process | Total |
|--------|--------|------------|-------|--------------|-------|
| 500    | 2,500  | 3.44s      | 10.93s| 0.08s        | 14.45s |
| 1,000  | 5,000  | 6.60s      | 25.54s| 0.17s        | 32.32s |

## Previous Results (Sequential Introspect — 2026-04-01)

| Tables | Fields | Introspect | Stage | Post-process | Total |
|--------|--------|------------|-------|--------------|-------|
| 500    | 2,500  | 6.03s      | 8.93s | 0.10s        | 15.07s |
| 1,000  | 5,000  | 15.95s     | 21.38s| 0.27s        | 37.61s |

## Speedup Analysis

| Metric | 500 tables | 1000 tables |
|--------|------------|-------------|
| Introspect speedup | 1.75x | 2.42x |
| Total speedup | 1.04x | 1.16x |

The introspect phase shows significant improvement (1.75x–2.42x), but total speedup is limited because stage dominates. The 4-worker parallel introspect doesn't achieve theoretical 4x because:

1. ThreadPoolExecutor overhead (creation, synchronization)
2. PostgreSQL connection pool contention
3. Network latency to remote datasource

## Scaling (Current)

- **Introspect** (parallel metadata fetch): ~7ms/table — near-linear, parallelized.
- **Stage** (reconcile + prune + commit): ~25ms/table — near-linear, single-threaded.
- **Post-process** (embedding dispatch): negligible (<0.5s).
- **Total** at 1,000 tables ≈ 32s — well within the 1-hour stale timeout.

## Observations

1. Parallel introspect cuts the introspect phase by 50–60%.
2. Stage is now the dominant phase (~80% of total time). Further optimization should focus on parallelizing `_reconcile_single_table` or batching inserts.
3. Post-process embedding dispatch fires 10 parallel threads (chunk_size=50) against the remote embedding API; latency depends on external API.

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
