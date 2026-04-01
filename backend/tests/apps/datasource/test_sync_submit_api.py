from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from sqlmodel import Session

from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    DatasourceSyncJobStatusResponse,
    SyncJobPhase,
    SyncJobStatus,
)
from common.core.config import settings


def test_choose_tables_legacy_path_when_flag_off(
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


def test_choose_tables_legacy_path_below_threshold(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api

    called: list[str] = []

    def fake_choose_tables(
        session: Session, trans: object, ds_id: int, tables: list[object]
    ) -> None:
        _ = session
        _ = trans
        _ = ds_id
        called.append(str(len(tables)))

    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", True)
    monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 5)
    monkeypatch.setattr(datasource_api, "chooseTables", fake_choose_tables)

    response = test_app.post(
        "/api/v1/datasource/chooseTables/1",
        headers=auth_headers,
        json=[{"table_name": "orders", "table_comment": "Orders"}],
    )

    assert response.status_code == 200
    assert response.json() == {"code": 0, "data": None, "msg": None}
    assert called == ["1"]


def test_choose_tables_submits_job_when_flag_on_above_threshold(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api
    from apps.datasource.models.sync_job import DatasourceSyncJobSubmitResponse

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
    assert response.json() == {
        "code": 0,
        "data": {
            "job_id": 99,
            "datasource_id": 1,
            "status": "pending",
            "phase": "submit",
            "reused_active_job": False,
        },
        "msg": None,
    }
    assert called == [(1, 2)]


def test_get_sync_job_status_returns_progress(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api

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
        datasource_api,
        "get_sync_job_by_id",
        lambda session, job_id: object() if job_id == 1 else None,
    )
    monkeypatch.setattr(
        datasource_api,
        "build_sync_job_status_response",
        lambda job: payload,
    )

    response = test_app.get("/api/v1/datasource/syncJob/1", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["job_id"] == 1
    assert response.json()["data"]["datasource_id"] == 7
    assert response.json()["data"]["status"] == "running"
    assert response.json()["data"]["phase"] == "stage"
    assert response.json()["data"]["completed_tables"] == 12
    assert response.json()["data"]["current_table_name"] == "orders"


def test_get_sync_job_status_404_on_missing(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api

    monkeypatch.setattr(
        datasource_api, "get_sync_job_by_id", lambda session, job_id: None
    )

    response = test_app.get("/api/v1/datasource/syncJob/999", headers=auth_headers)

    assert response.status_code == 404
    assert "sync job not found" in response.text


def test_list_sync_jobs_scoped_to_datasource(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api

    now = datetime(2026, 3, 31, 12, 0, 0)
    newer = DatasourceSyncJob(
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
    older = DatasourceSyncJob(
        id=1,
        ds_id=8,
        oid=1,
        create_by=1,
        status=SyncJobStatus.PENDING,
        phase=SyncJobPhase.SUBMIT,
        total_tables=10,
        completed_tables=0,
        failed_tables=0,
        skipped_tables=0,
        total_fields=0,
        completed_fields=0,
        create_time=now,
        update_time=now,
    )

    monkeypatch.setattr(
        datasource_api,
        "list_sync_jobs_by_ds",
        lambda session, ds_id: [newer, older] if ds_id == 8 else [],
    )

    response = test_app.get("/api/v1/datasource/syncJobs/8", headers=auth_headers)

    assert response.status_code == 200
    assert [item["job_id"] for item in response.json()["data"]] == [2, 1]
    assert all(item["datasource_id"] == 8 for item in response.json()["data"])


def test_sync_job_stream_scaffold_returns_501(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api

    monkeypatch.setattr(
        datasource_api,
        "get_sync_job_by_id",
        lambda session, job_id: object() if job_id == 1 else None,
    )
    monkeypatch.setattr(
        datasource_api,
        "iter_sync_job_events",
        lambda session_factory, job_id, poll_interval_seconds: iter(
            [
                'data:{"type":"sync_progress","job_id":1,"status":"succeeded"}\n\n',
                'data:{"type":"finish"}\n\n',
            ]
        ),
    )

    response = test_app.get(
        "/api/v1/datasource/syncJob/1/stream",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert (
        'data:{"type":"sync_progress","job_id":1,"status":"succeeded"}' in response.text
    )
    assert 'data:{"type":"finish"}' in response.text


def test_sync_job_stream_returns_404_for_missing_job(
    monkeypatch: pytest.MonkeyPatch,
    test_app: Any,
    auth_headers: dict[str, str],
) -> None:
    from apps.datasource.api import datasource as datasource_api

    monkeypatch.setattr(
        datasource_api,
        "get_sync_job_by_id",
        lambda session, job_id: None,
    )

    response = test_app.get(
        "/api/v1/datasource/syncJob/1/stream",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "sync job not found" in response.text
