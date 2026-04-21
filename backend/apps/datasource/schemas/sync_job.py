"""Datasource sync job schema contract.

Defines the exact Pydantic payload shapes for the async sync job API.
The SQLModel persistence layer lives in ``apps.datasource.models.sync_job``;
this module provides the *wire-contract* schemas consumed by the API layer.

Re-exports the canonical ``SyncJobStatus`` and ``SyncJobPhase`` enums from
the models module so that API routers can import everything from one place.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from apps.datasource.models.sync_job import SyncJobPhase, SyncJobStatus

__all__ = [
    "SyncJobStatus",
    "SyncJobPhase",
    "SyncJobSubmitRequest",
    "SyncJobSubmitResponse",
    "SyncJobStatusResponse",
    "SyncJobSummary",
    "SyncJobTableDetail",
]


class SyncJobSubmitRequest(BaseModel):
    """Client payload for submitting a new async sync job."""

    datasource_id: int
    tables: list[str]


class SyncJobSubmitResponse(BaseModel):
    """Server response for ``POST /sync-jobs`` — always 202 Accepted."""

    job_id: int
    datasource_id: int
    status: SyncJobStatus
    phase: SyncJobPhase | None = SyncJobPhase.SUBMIT
    reused_active_job: bool = False


class SyncJobStatusResponse(BaseModel):
    """Server response for ``GET /sync-jobs/{job_id}`` — 200 with progress."""

    job_id: int
    datasource_id: int
    status: SyncJobStatus
    phase: SyncJobPhase | None = None
    total_tables: int = 0
    completed_tables: int = 0
    failed_tables: int = 0
    skipped_tables: int = 0
    total_fields: int = 0
    completed_fields: int = 0
    current_table_name: str | None = None
    embedding_followup_status: str | None = None
    error_summary: str | None = None
    create_time: datetime
    update_time: datetime
    start_time: datetime | None = None
    finish_time: datetime | None = None


class SyncJobSummary(BaseModel):
    """Lightweight summary used in list endpoints."""

    job_id: int
    datasource_id: int
    status: SyncJobStatus
    total_tables: int = 0
    completed_tables: int = 0
    failed_tables: int = 0
    skipped_tables: int = 0
    create_time: datetime
    finish_time: datetime | None = None


class SyncJobTableDetail(BaseModel):
    """Per-table outcome within a completed sync job."""

    table_name: str
    status: SyncJobStatus
    fields_synced: int = 0
    fields_total: int = 0
    error: str | None = None
