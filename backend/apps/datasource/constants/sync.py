"""Datasource sync job constants.

Centralises feature-flag keys, threshold defaults, and state classification
helpers used by the async sync contract.  The canonical enum definitions
live in ``apps.datasource.models.sync_job`` (SyncJobStatus, SyncJobPhase);
this module re-exports them alongside routing-policy constants so that
callers have a single import surface for contract-level values.
"""

from __future__ import annotations

from apps.datasource.models.sync_job import (
    ACTIVE_DATASOURCE_SYNC_JOB_STATUSES,
    TERMINAL_DATASOURCE_SYNC_JOB_STATUSES,
    SyncJobPhase,
    SyncJobStatus,
)

__all__ = [
    "SYNC_FEATURE_FLAG_KEY",
    "SYNC_ASYNC_THRESHOLD_TABLES",
    "SYNC_BATCH_SIZE",
    "SYNC_FIELD_BATCH_SIZE",
    "SYNC_JOB_MAX_WORKERS",
    "SYNC_JOB_STALE_TIMEOUT_SECONDS",
    "SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
    "SYNC_EMBEDDING_CHUNK_SIZE",
    "SYNC_EMBEDDING_MAX_WORKERS",
    "SyncJobStatus",
    "SyncJobPhase",
    "ACTIVE_DATASOURCE_SYNC_JOB_STATUSES",
    "TERMINAL_DATASOURCE_SYNC_JOB_STATUSES",
    "should_route_async",
]

# Feature flag key. Default is OFF (False) in config.py. To enable async sync
# in a target environment, set DATASOURCE_ASYNC_SYNC_ENABLED=true in the env.
# The routing rule (flag_enabled AND table_count >= threshold) ensures that
# only large syncs use the async path while small syncs stay synchronous.
SYNC_FEATURE_FLAG_KEY: str = "DATASOURCE_ASYNC_SYNC_ENABLED"

# Minimum number of selected tables to trigger async job routing.
# Below this threshold, sync always uses the synchronous path regardless of flag.
SYNC_ASYNC_THRESHOLD_TABLES: int = 100

# Table-level batch size for introspection and staging. Each batch is committed
# together; if a batch fails, individual tables within it are retried one-by-one.
SYNC_BATCH_SIZE: int = 50

# Field-level flush size inside a table batch. Fields are inserted and flushed
# in chunks of this size to obtain primary keys before stale-field pruning.
SYNC_FIELD_BATCH_SIZE: int = 200

# Maximum concurrent sync job workers (ThreadPoolExecutor max_workers).
SYNC_JOB_MAX_WORKERS: int = 4

# A job whose update_time is older than this threshold (in seconds) is
# considered stale/orphaned and will be marked FAILED by the recovery loop.
SYNC_JOB_STALE_TIMEOUT_SECONDS: int = 3600

# Minimum interval (seconds) between progress-update commits during a sync.
# Throttles DB writes so that high-table-count syncs don't overwhelm the DB.
SYNC_JOB_PROGRESS_INTERVAL_SECONDS: int = 2

# Number of table IDs dispatched per embedding post-process chunk.
SYNC_EMBEDDING_CHUNK_SIZE: int = 50

# Maximum concurrent embedding workers. Must fit within PG pool capacity
# alongside SYNC_JOB_MAX_WORKERS (total 12 < pool capacity 50).
SYNC_EMBEDDING_MAX_WORKERS: int = 8


def should_route_async(
    *,
    flag_enabled: bool,
    selected_table_count: int,
    threshold: int = SYNC_ASYNC_THRESHOLD_TABLES,
) -> bool:
    """Decide whether a sync request should use the async job path.

    The routing rule is: feature flag **must** be enabled **and** the
    number of selected tables **must** meet or exceed the threshold.

    Parameters
    ----------
    flag_enabled:
        Current value of ``DATASOURCE_ASYNC_SYNC_ENABLED``.
    selected_table_count:
        Number of tables the user selected for sync.
    threshold:
        Minimum table count to trigger async routing (default 100).

    Returns
    -------
    bool
        ``True`` → use the async job submit path (202).
        ``False`` → use the existing synchronous save path (unchanged).
    """
    return flag_enabled and selected_table_count >= threshold
