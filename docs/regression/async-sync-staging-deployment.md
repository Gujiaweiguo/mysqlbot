# Async Datasource Sync — Staging Gray Deployment Runbook

## Prerequisites

- Staging environment with PostgreSQL accessible
- Backend deployed via docker-compose or installer
- Existing datasources with >100 tables for testing

## Steps

### 1. Enable Feature Flag

In the staging `.env` file, set:

```bash
DATASOURCE_ASYNC_SYNC_ENABLED=true
DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD=100
DATASOURCE_SYNC_JOB_MAX_WORKERS=4
DATASOURCE_SYNC_JOB_STALE_TIMEOUT_SECONDS=3600
DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS=2
DATASOURCE_SYNC_EMBEDDING_CHUNK_SIZE=50
```

For docker-compose deployment, add to `docker-compose.yml` under `app` → `environment`:

```yaml
- DATASOURCE_ASYNC_SYNC_ENABLED=true
- DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD=100
- DATASOURCE_SYNC_JOB_MAX_WORKERS=4
```

### 2. Restart Backend

```bash
# docker-compose
docker compose restart app

# installer
sctl restart
```

### 3. Monitor Job Health

Watch for `sync_job_timing` log lines in backend logs:

```bash
docker compose logs -f app | grep sync_job_timing
```

Expected output:
```json
{"event": "sync_job_timing", "job_id": 42, "ds_id": 7, "total_tables": 150, "total_fields": 750, "introspect_seconds": 1.8, "stage_seconds": 2.7, "post_process_seconds": 0.05, "total_seconds": 4.55}
```

### 4. Validate Async Path

1. Open the datasource management page
2. Select a datasource with >100 tables
3. Click "Sync Tables" or "重新同步"
4. Verify progress panel appears (if frontend is updated)
5. Check that tables appear after sync completes

### 5. Monitor Failure Rate

Query the database for failed jobs:

```sql
SELECT status, phase, COUNT(*), AVG(EXTRACT(EPOCH FROM (finish_time - start_time))) as avg_seconds
FROM datasource_sync_job
WHERE create_time > NOW() - INTERVAL '1 day'
GROUP BY status, phase;
```

Expected: 0 failed jobs, `avg_seconds` < 120 for typical datasources.

### 6. Rollback

If issues arise, disable the feature:

```bash
DATASOURCE_ASYNC_SYNC_ENABLED=false
```

Restart the backend. No data migration is needed — the `datasource_sync_job` table will simply stop receiving new jobs.

## Success Criteria

- [ ] All datasources with >100 tables sync via async path
- [ ] No failed sync jobs in 24 hours
- [ ] Average sync time < 2 minutes for 500-table datasources
- [ ] Frontend progress panel shows accurate status
- [ ] Embedding follow-up dispatch succeeds

## Rollback Plan

Set `DATASOURCE_ASYNC_SYNC_ENABLED=false` and restart. Existing sync jobs will complete via the synchronous path on next sync attempt.
