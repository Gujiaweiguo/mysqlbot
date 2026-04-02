from prometheus_client import Counter, Histogram

SYNC_JOBS_SUBMITTED = Counter(
    "sqlbot_sync_jobs_submitted_total",
    "Total datasource sync job submissions",
    ["reused_active"],
)

SYNC_JOB_STATUS_TRANSITIONS = Counter(
    "sqlbot_sync_job_status_transitions_total",
    "Sync job status transition counts",
    ["status"],
)

SYNC_JOB_PHASE_DURATION = Histogram(
    "sqlbot_sync_job_phase_duration_seconds",
    "Duration of sync job phases",
    ["phase"],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)

SYNC_JOB_TOTAL_DURATION = Histogram(
    "sqlbot_sync_job_total_duration_seconds",
    "Total wall time for sync jobs",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

SYNC_JOB_TABLES_FIELDS = Histogram(
    "sqlbot_sync_job_tables_fields",
    "Tables and fields per sync job",
    ["metric"],
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000),
)

SYNC_EMBEDDING_FOLLOWUP = Counter(
    "sqlbot_sync_embedding_followup_total",
    "Embedding follow-up dispatch outcomes",
    ["outcome"],
)
