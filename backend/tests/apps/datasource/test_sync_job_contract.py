from datetime import datetime

import pytest

from apps.datasource.models.sync_job import (
    DatasourceSyncJobStatusResponse,
    DatasourceSyncJobSubmitResponse,
    SyncJobPhase,
    SyncJobStatus,
    should_publish_datasource_sync_result,
)
from common.core.config import Settings


def test_async_sync_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATASOURCE_ASYNC_SYNC_ENABLED", raising=False)
    monkeypatch.delenv("DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", raising=False)
    monkeypatch.delenv("DATASOURCE_SYNC_JOB_MAX_WORKERS", raising=False)
    monkeypatch.delenv("DATASOURCE_SYNC_JOB_STALE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("DATASOURCE_SYNC_EMBEDDING_CHUNK_SIZE", raising=False)
    local_settings = Settings()

    assert local_settings.DATASOURCE_ASYNC_SYNC_ENABLED is False
    assert local_settings.DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD == 100
    assert local_settings.DATASOURCE_SYNC_JOB_MAX_WORKERS == 4
    assert local_settings.DATASOURCE_SYNC_JOB_STALE_TIMEOUT_SECONDS == 3600
    assert local_settings.DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS == 2
    assert local_settings.DATASOURCE_SYNC_EMBEDDING_CHUNK_SIZE == 50


def test_submit_response_contract_shape() -> None:
    payload = DatasourceSyncJobSubmitResponse(
        job_id=11,
        datasource_id=22,
        status=SyncJobStatus.PENDING,
        phase=SyncJobPhase.SUBMIT,
        reused_active_job=False,
    )

    assert payload.model_dump(mode="json") == {
        "job_id": 11,
        "datasource_id": 22,
        "status": "pending",
        "phase": "submit",
        "reused_active_job": False,
    }


def test_status_response_contract_exposes_progress_fields() -> None:
    now = datetime(2026, 3, 31, 12, 0, 0)
    payload = DatasourceSyncJobStatusResponse(
        job_id=11,
        datasource_id=22,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
        total_tables=1000,
        completed_tables=10,
        failed_tables=1,
        skipped_tables=2,
        total_fields=200,
        completed_fields=30,
        current_table_name="orders",
        error_summary=None,
        create_time=now,
        update_time=now,
        start_time=now,
        finish_time=None,
    )

    assert payload.model_dump(mode="json") == {
        "job_id": 11,
        "datasource_id": 22,
        "status": "running",
        "phase": "introspect",
        "total_tables": 1000,
        "completed_tables": 10,
        "failed_tables": 1,
        "skipped_tables": 2,
        "total_fields": 200,
        "completed_fields": 30,
        "current_table_name": "orders",
        "embedding_followup_status": None,
        "error_summary": None,
        "create_time": "2026-03-31T12:00:00",
        "update_time": "2026-03-31T12:00:00",
        "start_time": "2026-03-31T12:00:00",
        "finish_time": None,
    }


@pytest.mark.parametrize(
    ("status", "phase", "error_summary", "finish_time"),
    [
        (SyncJobStatus.PENDING, SyncJobPhase.SUBMIT, None, None),
        (
            SyncJobStatus.SUCCEEDED,
            SyncJobPhase.FINALIZE,
            None,
            datetime(2026, 3, 31, 12, 10, 0),
        ),
        (
            SyncJobStatus.FAILED,
            SyncJobPhase.STAGE,
            "boom",
            datetime(2026, 3, 31, 12, 10, 0),
        ),
        (
            SyncJobStatus.PARTIAL,
            SyncJobPhase.STAGE,
            "1 of 2 tables failed during sync",
            datetime(2026, 3, 31, 12, 10, 0),
        ),
        (
            SyncJobStatus.CANCELLED,
            SyncJobPhase.FINALIZE,
            None,
            datetime(2026, 3, 31, 12, 10, 0),
        ),
    ],
)
def test_status_response_contract_for_terminal_and_pending_states(
    status: SyncJobStatus,
    phase: SyncJobPhase,
    error_summary: str | None,
    finish_time: datetime | None,
) -> None:
    now = datetime(2026, 3, 31, 12, 0, 0)
    payload = DatasourceSyncJobStatusResponse(
        job_id=5,
        datasource_id=9,
        status=status,
        phase=phase,
        total_tables=20,
        completed_tables=10,
        failed_tables=1,
        skipped_tables=0,
        total_fields=100,
        completed_fields=50,
        current_table_name="orders",
        error_summary=error_summary,
        create_time=now,
        update_time=now,
        start_time=now,
        finish_time=finish_time,
    )

    dumped = payload.model_dump(mode="json")
    assert dumped["status"] == status.value
    assert dumped["phase"] == phase.value
    assert dumped["embedding_followup_status"] is None
    assert dumped["error_summary"] == error_summary
    if finish_time is None:
        assert dumped["finish_time"] is None
    else:
        assert dumped["finish_time"] == finish_time.isoformat()


def test_only_succeeded_jobs_publish_new_schema() -> None:
    assert should_publish_datasource_sync_result(SyncJobStatus.PENDING) is False
    assert should_publish_datasource_sync_result(SyncJobStatus.RUNNING) is False
    assert should_publish_datasource_sync_result(SyncJobStatus.FINALIZING) is False
    assert should_publish_datasource_sync_result(SyncJobStatus.FAILED) is False
    assert should_publish_datasource_sync_result(SyncJobStatus.PARTIAL) is False
    assert should_publish_datasource_sync_result(SyncJobStatus.CANCELLED) is False
    assert should_publish_datasource_sync_result(SyncJobStatus.SUCCEEDED) is True
