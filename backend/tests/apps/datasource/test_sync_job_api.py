from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from sqlmodel import Session

from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    DatasourceSyncJobStatusResponse,
    DatasourceSyncJobSubmitResponse,
    SyncJobPhase,
    SyncJobStatus,
)
from common.core.config import settings


# ---------------------------------------------------------------------------
# POST /sync-jobs — submit
# ---------------------------------------------------------------------------


def test_submit_sync_job_returns_202(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api
    from apps.datasource.models.datasource import CoreDatasource

    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", True)
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 2)

    fake_ds = CoreDatasource(id=1, name="test", oid=1)  # pyright: ignore[reportCallIssue]
    submit_calls: list[dict[str, Any]] = []

    def fake_submit(session: Session, **kw: Any) -> DatasourceSyncJobSubmitResponse:
        submit_calls.append(kw)
        return DatasourceSyncJobSubmitResponse(
            job_id=42,
            datasource_id=kw["ds_id"],
            status=SyncJobStatus.PENDING,
            phase=SyncJobPhase.SUBMIT,
            reused_active_job=False,
        )

    monkeypatch.setattr(sync_job_api, "submit_datasource_sync_job", fake_submit)
    monkeypatch.setattr(sync_job_api, "dispatch_sync_job", lambda job_id: None)

    def fake_exec(self: Session, statement: Any, **kw: Any) -> Any:
        class _FakeResult:
            def first(self) -> CoreDatasource:
                return fake_ds

        return _FakeResult()

    monkeypatch.setattr(Session, "exec", fake_exec)

    response = test_app.post(
        "/api/v1/sync-jobs",
        headers=auth_headers,
        json={"datasource_id": 1, "tables": ["orders", "customers"]},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == 42
    assert data["datasource_id"] == 1
    assert data["status"] == "pending"
    assert data["phase"] == "submit"
    assert data["reused_active_job"] is False
    assert len(submit_calls) == 1
    assert submit_calls[0]["ds_id"] == 1
    assert submit_calls[0]["total_tables"] == 2


def test_submit_sync_job_reuses_active_job(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api
    from apps.datasource.models.datasource import CoreDatasource

    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", True)
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 1)

    fake_ds = CoreDatasource(id=5, name="test", oid=1)  # pyright: ignore[reportCallIssue]

    monkeypatch.setattr(
        sync_job_api,
        "submit_datasource_sync_job",
        lambda *a, **kw: DatasourceSyncJobSubmitResponse(
            job_id=10,
            datasource_id=5,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            reused_active_job=True,
        ),
    )
    monkeypatch.setattr(sync_job_api, "dispatch_sync_job", lambda job_id: None)

    def fake_exec(self: Session, statement: Any, **kw: Any) -> Any:
        class _FakeResult:
            def first(self) -> CoreDatasource:
                return fake_ds

        return _FakeResult()

    monkeypatch.setattr(Session, "exec", fake_exec)

    response = test_app.post(
        "/api/v1/sync-jobs",
        headers=auth_headers,
        json={"datasource_id": 5, "tables": ["orders"]},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["reused_active_job"] is True
    assert data["job_id"] == 10


def test_submit_sync_job_rejected_when_flag_off(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", False)
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 1)

    response = test_app.post(
        "/api/v1/sync-jobs",
        headers=auth_headers,
        json={"datasource_id": 1, "tables": ["orders"]},
    )

    assert response.status_code == 422
    assert "async sync not available" in response.text


def test_submit_sync_job_rejected_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", True)
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 100)

    response = test_app.post(
        "/api/v1/sync-jobs",
        headers=auth_headers,
        json={"datasource_id": 1, "tables": ["orders"]},
    )

    assert response.status_code == 422


def test_submit_sync_job_404_missing_datasource(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", True)
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 1)

    def fake_exec(self: Session, statement: Any, **kw: Any) -> Any:
        class _FakeResult:
            def first(self) -> None:
                return None

        return _FakeResult()

    monkeypatch.setattr(Session, "exec", fake_exec)

    response = test_app.post(
        "/api/v1/sync-jobs",
        headers=auth_headers,
        json={"datasource_id": 9999, "tables": ["orders"]},
    )

    assert response.status_code == 404
    assert "datasource not found" in response.text


# ---------------------------------------------------------------------------
# GET /sync-jobs/{job_id} — status
# ---------------------------------------------------------------------------


def test_get_sync_job_status_returns_progress(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    now = datetime(2026, 3, 31, 12, 0, 0)
    payload = DatasourceSyncJobStatusResponse(
        job_id=1,
        datasource_id=7,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        total_tables=100,
        completed_tables=12,
        failed_tables=0,
        skipped_tables=0,
        total_fields=40,
        completed_fields=30,
        current_table_name="orders",
        error_summary=None,
        create_time=now,
        update_time=now,
        start_time=now,
        finish_time=None,
    )

    monkeypatch.setattr(
        sync_job_api,
        "get_sync_job_by_id",
        lambda session, job_id: object() if job_id == 1 else None,
    )
    monkeypatch.setattr(
        sync_job_api,
        "build_sync_job_status_response",
        lambda job: payload,
    )

    response = test_app.get("/api/v1/sync-jobs/1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["job_id"] == 1
    assert data["datasource_id"] == 7
    assert data["status"] == "running"
    assert data["phase"] == "stage"
    assert data["completed_tables"] == 12
    assert data["current_table_name"] == "orders"


def test_get_sync_job_status_404_on_missing(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    monkeypatch.setattr(
        sync_job_api, "get_sync_job_by_id", lambda session, job_id: None
    )

    response = test_app.get("/api/v1/sync-jobs/999", headers=auth_headers)

    assert response.status_code == 404
    assert "sync job not found" in response.text


# ---------------------------------------------------------------------------
# GET /sync-jobs?datasource_id= — list
# ---------------------------------------------------------------------------


def test_list_sync_jobs_returns_summary_list(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    now = datetime(2026, 3, 31, 12, 0, 0)
    job_newer = DatasourceSyncJob(
        id=2,
        ds_id=8,
        oid=1,
        create_by=1,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
        total_tables=20,
        completed_tables=1,
        failed_tables=0,
        skipped_tables=0,
        total_fields=0,
        completed_fields=0,
        create_time=now,
        update_time=now,
    )
    job_older = DatasourceSyncJob(
        id=1,
        ds_id=8,
        oid=1,
        create_by=1,
        status=SyncJobStatus.SUCCEEDED,
        phase=SyncJobPhase.FINALIZE,
        total_tables=10,
        completed_tables=10,
        failed_tables=0,
        skipped_tables=0,
        total_fields=0,
        completed_fields=0,
        create_time=now,
        update_time=now,
        finish_time=now,
    )

    monkeypatch.setattr(
        sync_job_api,
        "list_sync_jobs_by_ds",
        lambda session, ds_id: [job_newer, job_older] if ds_id == 8 else [],
    )

    response = test_app.get(
        "/api/v1/sync-jobs", params={"datasource_id": 8}, headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["job_id"] == 2
    assert data[0]["status"] == "running"
    assert data[0]["total_tables"] == 20
    assert data[1]["job_id"] == 1
    assert data[1]["status"] == "succeeded"
    assert data[1]["finish_time"] is not None


def test_list_sync_jobs_empty(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    monkeypatch.setattr(
        sync_job_api,
        "list_sync_jobs_by_ds",
        lambda session, ds_id: [],
    )

    response = test_app.get(
        "/api/v1/sync-jobs", params={"datasource_id": 99}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["data"] == []


# ---------------------------------------------------------------------------
# POST /sync-jobs/{job_id}/cancel
# ---------------------------------------------------------------------------


def test_cancel_sync_job_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    now = datetime(2026, 3, 31, 12, 0, 0)
    job = DatasourceSyncJob(
        id=5,
        ds_id=8,
        oid=1,
        create_by=1,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        total_tables=20,
        completed_tables=3,
        failed_tables=0,
        skipped_tables=0,
        total_fields=50,
        completed_fields=10,
        create_time=now,
        update_time=now,
    )

    monkeypatch.setattr(
        sync_job_api,
        "get_sync_job_by_id",
        lambda session, job_id: job if job_id == 5 else None,
    )

    def fake_cancel(session: Session, job: DatasourceSyncJob) -> DatasourceSyncJob:
        job.status = SyncJobStatus.CANCELLED
        job.error_summary = "sync job cancelled by operator"
        job.finish_time = now
        return job

    monkeypatch.setattr(sync_job_api, "cancel_sync_job", fake_cancel)

    response = test_app.post("/api/v1/sync-jobs/5/cancel", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "cancelled"
    assert data["error_summary"] == "sync job cancelled by operator"


def test_cancel_sync_job_terminal_rejected(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    monkeypatch.setattr(
        sync_job_api,
        "get_sync_job_by_id",
        lambda session, job_id: object() if job_id == 5 else None,
    )

    def fail_cancel(session: Session, job: object) -> None:
        raise ValueError("sync job is not cancelable")

    monkeypatch.setattr(sync_job_api, "cancel_sync_job", fail_cancel)

    response = test_app.post("/api/v1/sync-jobs/5/cancel", headers=auth_headers)

    assert response.status_code == 409
    assert "sync job is not cancelable" in response.text


def test_cancel_sync_job_404_missing(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    monkeypatch.setattr(
        sync_job_api, "get_sync_job_by_id", lambda session, job_id: None
    )

    response = test_app.post("/api/v1/sync-jobs/999/cancel", headers=auth_headers)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /sync-jobs/{job_id}/retry
# ---------------------------------------------------------------------------


def test_retry_sync_job_returns_submit_response(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    now = datetime(2026, 3, 31, 12, 0, 0)
    job = DatasourceSyncJob(
        id=7,
        ds_id=1,
        oid=1,
        create_by=1,
        status=SyncJobStatus.PARTIAL,
        phase=SyncJobPhase.STAGE,
        total_tables=20,
        completed_tables=19,
        failed_tables=1,
        skipped_tables=0,
        total_fields=50,
        completed_fields=49,
        requested_tables='[{"table_name":"orders","table_comment":"Orders"}]',
        create_time=now,
        update_time=now,
    )

    monkeypatch.setattr(
        sync_job_api,
        "get_sync_job_by_id",
        lambda session, job_id: job if job_id == 7 else None,
    )
    monkeypatch.setattr(
        sync_job_api,
        "retry_sync_job",
        lambda session, job, oid, create_by: DatasourceSyncJobSubmitResponse(
            job_id=8,
            datasource_id=job.ds_id,
            status=SyncJobStatus.PENDING,
            phase=SyncJobPhase.SUBMIT,
            reused_active_job=False,
        ),
    )
    monkeypatch.setattr(sync_job_api, "dispatch_sync_job", lambda job_id: None)

    response = test_app.post("/api/v1/sync-jobs/7/retry", headers=auth_headers)

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == 8
    assert data["datasource_id"] == 1
    assert data["status"] == "pending"
    assert data["reused_active_job"] is False


def test_retry_sync_job_non_terminal_rejected(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import sync_job as sync_job_api

    now = datetime(2026, 3, 31, 12, 0, 0)
    job = DatasourceSyncJob(
        id=9,
        ds_id=1,
        oid=1,
        create_by=1,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        total_tables=20,
        completed_tables=10,
        failed_tables=0,
        skipped_tables=0,
        total_fields=50,
        completed_fields=25,
        requested_tables='[{"table_name":"orders","table_comment":"Orders"}]',
        create_time=now,
        update_time=now,
    )

    monkeypatch.setattr(
        sync_job_api,
        "get_sync_job_by_id",
        lambda session, job_id: job if job_id == 9 else None,
    )

    def fail_retry(session: Session, job: object, oid: int, create_by: int) -> None:
        raise ValueError("sync job is not retryable")

    monkeypatch.setattr(sync_job_api, "retry_sync_job", fail_retry)

    response = test_app.post("/api/v1/sync-jobs/9/retry", headers=auth_headers)

    assert response.status_code == 409
    assert "sync job is not retryable" in response.text


# ---------------------------------------------------------------------------
# Feature flag routing through chooseTables
# ---------------------------------------------------------------------------


def test_choose_tables_flag_off_uses_sync_path(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api

    called: list[tuple[int, int]] = []

    def fake_choose_tables(
        session: Session, trans: object, ds_id: int, tables: list[object]
    ) -> None:
        _ = session
        _ = trans
        called.append((ds_id, len(tables)))

    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", False)
    monkeypatch.setattr(datasource_api, "chooseTables", fake_choose_tables)

    response = test_app.post(
        "/api/v1/datasource/chooseTables/1",
        headers=auth_headers,
        json=[{"table_name": "orders", "table_comment": "Orders"}],
    )

    assert response.status_code == 200
    assert response.json() == {"code": 0, "data": None, "msg": None}
    assert called == [(1, 1)]


def test_choose_tables_flag_on_submits_async(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api

    called: list[tuple[int, int]] = []

    def fake_submit(
        session: Session,
        trans: object,
        user: object,
        ds_id: int,
        tables: list[object],
    ) -> DatasourceSyncJobSubmitResponse:
        _ = session
        _ = trans
        _ = user
        called.append((ds_id, len(tables)))
        return DatasourceSyncJobSubmitResponse(
            job_id=99,
            datasource_id=ds_id,
            status=SyncJobStatus.PENDING,
            phase=SyncJobPhase.SUBMIT,
            reused_active_job=False,
        )

    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", True)
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 1)
    monkeypatch.setattr(datasource_api, "_submit_async_sync_job", fake_submit)

    response = test_app.post(
        "/api/v1/datasource/chooseTables/1",
        headers=auth_headers,
        json=[
            {"table_name": "orders", "table_comment": "Orders"},
            {"table_name": "customers", "table_comment": "Customers"},
        ],
    )

    assert response.status_code == 200
    assert response.json()["data"]["job_id"] == 99
    assert response.json()["data"]["reused_active_job"] is False
    assert called == [(1, 2)]
