# Datasource Async Sync Job — API Contract

## Overview

This document defines the locked contract for the datasource-scoped async
schema sync job system.  The system supports syncing ~1000 selected tables
in a datasource without blocking the synchronous save path.

## Job States

| State        | Description                                              |
|--------------|----------------------------------------------------------|
| `pending`    | Job created, waiting to be picked up by the runner       |
| `running`    | Job actively processing tables                           |
| `finalizing` | All tables processed, publishing results                 |
| `succeeded`  | All tables synced successfully, new schema is visible    |
| `failed`     | Job failed; previous schema remains visible              |
| `partial`    | Some tables failed; previous schema remains visible      |
| `cancelled`  | Job cancelled by operator; previous schema remains visible|

Active states: `pending`, `running`, `finalizing`
Terminal states: `succeeded`, `failed`, `partial`, `cancelled`

## Job Phases

| Phase          | Description                               |
|----------------|-------------------------------------------|
| `submit`       | Job creation / validation                 |
| `introspect`   | Schema introspection of selected tables   |
| `stage`        | Staging table/field data                  |
| `finalize`     | Publishing synced data to visible state   |
| `post_process` | Embedding follow-up (non-blocking)        |

## One-Active-Job-Per-Datasource

At most one active job may exist per datasource at any time.

- **Duplicate submit**: If an active job already exists for the datasource,
  the submit endpoint returns the existing job's info with
  `reused_active_job: true` instead of creating a new job.
- **No 409 Conflict in submit path**: The submit endpoint is idempotent —
  it returns the active job info rather than rejecting the request.
- **409 Conflict applies at the API level**: If a caller attempts an
  operation that conflicts with an active job (e.g., editing datasource
  configuration while a job is running), the API returns `409 Conflict`
  with the active job ID in the response body.

## Endpoints

### POST /sync-jobs — Submit Sync Job

**Routing**: Only reached when `should_route_async()` returns `True`.

Request body (`SyncJobSubmitRequest`):
```json
{
  "datasource_id": 42,
  "tables": ["orders", "customers", "products"]
}
```

Response: `202 Accepted`
```json
{
  "job_id": 101,
  "datasource_id": 42,
  "status": "pending",
  "phase": "submit",
  "reused_active_job": false
}
```

If an active job already exists:
```json
{
  "job_id": 101,
  "datasource_id": 42,
  "status": "running",
  "phase": "stage",
  "reused_active_job": true
}
```

### GET /sync-jobs/{job_id} — Job Status

Response: `200 OK`
```json
{
  "job_id": 101,
  "datasource_id": 42,
  "status": "running",
  "phase": "stage",
  "total_tables": 1000,
  "completed_tables": 150,
  "failed_tables": 2,
  "skipped_tables": 0,
  "total_fields": 5000,
  "completed_fields": 800,
  "current_table_name": "orders",
  "embedding_followup_status": null,
  "error_summary": null,
  "create_time": "2026-04-21T10:00:00",
  "update_time": "2026-04-21T10:05:00",
  "start_time": "2026-04-21T10:00:01",
  "finish_time": null
}
```

### GET /sync-jobs?datasource_id={id} — List Jobs

Response: `200 OK` — array of `SyncJobSummary`
```json
[
  {
    "job_id": 101,
    "datasource_id": 42,
    "status": "succeeded",
    "total_tables": 1000,
    "completed_tables": 998,
    "failed_tables": 2,
    "skipped_tables": 0,
    "create_time": "2026-04-21T10:00:00",
    "finish_time": "2026-04-21T10:30:00"
  }
]
```

### GET /sync-jobs/{job_id}/stream — SSE Stream (Optional)

Optional SSE enhancement.  Emits `sync_progress` events using the
existing `emit_chat_event` pattern from `apps.chat.streaming.events`
until the job reaches a terminal state, then emits `finish`.

Polling is first-class; SSE is an optional enhancement.

### POST /sync-jobs/{job_id}/cancel — Cancel Job

Sets job status to `cancelled`.  No mid-table hard interruption in v1;
the runner checks the cancellation flag between tables.

## Feature Flag and Threshold Routing

**Feature flag key**: `DATASOURCE_ASYNC_SYNC_ENABLED` (default: `false`)

**Threshold**: `DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD` (default: 100)

**Routing rule** (`should_route_async`):
- Flag **off** → synchronous save path (current behavior, unchanged)
- Flag **on** + table count < threshold → synchronous save path
- Flag **on** + table count >= threshold → async job submit path (202)

## Visibility Rules

- **Previous complete schema remains visible** until a job reaches
  `succeeded` and the finalize phase completes.
- **In-progress staged data is NOT user-visible**.  Only `succeeded`
  jobs trigger the visibility swap (`should_publish_datasource_sync_result`).
- After a page refresh, the client polls `GET /sync-jobs/{job_id}` to
  recover the current job state and display progress.

## Cancellation (v1)

- Status model supports `cancelled`.
- No mid-table hard interruption — the runner checks cancellation
  between individual table processing steps.
- Cancelled jobs retain progress counts for debugging.

## Recovery Behavior

- If the backend restarts while a job is `running`, the stale job
  recovery mechanism (DSYNC-003) detects jobs exceeding
  `DATASOURCE_SYNC_JOB_STALE_TIMEOUT_SECONDS` and marks them `failed`.
- On page refresh, the client should call `GET /sync-jobs?datasource_id={id}`
  to discover any active or recent job for the datasource.

## Response Wrapping

All JSON responses pass through `ResponseMiddleware` which wraps them in:
```json
{"code": 0, "data": <payload>, "msg": null}
```

Non-200 responses (e.g., 409 Conflict) bypass wrapping and are returned
directly by the exception handler.
