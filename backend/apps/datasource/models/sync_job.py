from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy import BigInteger, Column, DateTime, Identity, String, Text
from sqlmodel import Field, SQLModel

from apps.datasource.models.datasource import SelectedTablePayload


class SyncJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINALIZING = "finalizing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class SyncJobPhase(str, Enum):
    SUBMIT = "submit"
    INTROSPECT = "introspect"
    STAGE = "stage"
    FINALIZE = "finalize"
    POST_PROCESS = "post_process"


ACTIVE_DATASOURCE_SYNC_JOB_STATUSES = frozenset(
    {
        SyncJobStatus.PENDING,
        SyncJobStatus.RUNNING,
        SyncJobStatus.FINALIZING,
    }
)


TERMINAL_DATASOURCE_SYNC_JOB_STATUSES = frozenset(
    {
        SyncJobStatus.SUCCEEDED,
        SyncJobStatus.FAILED,
        SyncJobStatus.PARTIAL,
        SyncJobStatus.CANCELLED,
    }
)


def should_publish_datasource_sync_result(status: SyncJobStatus) -> bool:
    return status == SyncJobStatus.SUCCEEDED


class DatasourceSyncJob(SQLModel, table=True):
    __tablename__ = cast(Any, "datasource_sync_job")

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger, Identity(always=True), nullable=False, primary_key=True
        ),
    )
    ds_id: int = Field(sa_column=Column(BigInteger, nullable=False, index=True))
    oid: int = Field(sa_column=Column(BigInteger, nullable=False))
    create_by: int = Field(sa_column=Column(BigInteger, nullable=False))
    status: SyncJobStatus = Field(
        default=SyncJobStatus.PENDING,
        sa_column=Column(String(32), nullable=False, index=True),
    )
    phase: SyncJobPhase | None = Field(
        default=SyncJobPhase.SUBMIT,
        sa_column=Column(String(32), nullable=True),
    )
    total_tables: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    completed_tables: int = Field(
        default=0, sa_column=Column(BigInteger, nullable=False)
    )
    failed_tables: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    skipped_tables: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    total_fields: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    completed_fields: int = Field(
        default=0, sa_column=Column(BigInteger, nullable=False)
    )
    current_table_name: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    requested_tables: str = Field(default="[]", sa_column=Column(Text, nullable=False))
    embedding_followup_status: str | None = Field(
        default=None,
        sa_column=Column(String(32), nullable=True),
    )
    error_summary: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    create_time: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=False, index=True)
    )
    update_time: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=False)
    )
    start_time: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    finish_time: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )


class DatasourceSyncJobSubmitResponse(BaseModel):
    job_id: int
    datasource_id: int
    status: SyncJobStatus
    phase: SyncJobPhase | None = SyncJobPhase.SUBMIT
    reused_active_job: bool = False


class DatasourceSyncJobStatusResponse(BaseModel):
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


def dump_selected_tables_payload(tables: list[SelectedTablePayload]) -> str:
    return json.dumps([table.model_dump() for table in tables])


def load_selected_tables_payload(payload: str) -> list[SelectedTablePayload]:
    raw_items = json.loads(payload)
    return [SelectedTablePayload(**item) for item in raw_items]
