from __future__ import annotations

from collections.abc import Generator
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel

from apps.datasource.crud.sync_job import (
    create_sync_job,
    get_active_sync_job,
    get_sync_job_by_id,
    increment_sync_job_progress,
    update_sync_job_status,
)
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    SyncJobStatus,
)


@pytest.fixture
def sync_job_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [cast(Any, DatasourceSyncJob).__table__]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


def test_create_sync_job_persists_pending_defaults(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables

    job = create_sync_job(
        test_db,
        ds_id=7,
        oid=1,
        create_by=3,
        total_tables=1000,
        total_fields=20000,
    )

    assert job.id is not None
    assert job.ds_id == 7
    assert job.oid == 1
    assert job.create_by == 3
    assert job.status == SyncJobStatus.PENDING
    assert job.phase == SyncJobPhase.SUBMIT
    assert job.total_tables == 1000
    assert job.total_fields == 20000
    assert job.completed_tables == 0
    assert job.completed_fields == 0
    assert job.create_time == job.update_time
    assert job.start_time is None
    assert job.finish_time is None


def test_get_active_sync_job_ignores_terminal_jobs(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    terminal_job = create_sync_job(test_db, ds_id=9, oid=1, create_by=3)
    update_sync_job_status(
        test_db,
        job=terminal_job,
        status=SyncJobStatus.FAILED,
        phase=SyncJobPhase.FINALIZE,
        error_summary="boom",
    )
    active_job = create_sync_job(test_db, ds_id=9, oid=1, create_by=3)
    update_sync_job_status(
        test_db,
        job=active_job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
        current_table_name="orders",
    )

    loaded = get_active_sync_job(test_db, 9)

    assert loaded is not None
    assert loaded.id == active_job.id
    assert loaded.status == SyncJobStatus.RUNNING
    assert loaded.current_table_name == "orders"


def test_update_sync_job_status_sets_start_and_finish_timestamps(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=11, oid=1, create_by=3)

    running = update_sync_job_status(
        test_db,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        total_tables=50,
        completed_tables=10,
        total_fields=500,
        completed_fields=100,
        current_table_name="customers",
    )

    assert running.start_time is not None
    assert running.finish_time is None
    assert running.phase == SyncJobPhase.STAGE
    assert running.completed_tables == 10
    assert running.completed_fields == 100
    assert running.current_table_name == "customers"

    finished = update_sync_job_status(
        test_db,
        job=running,
        status=SyncJobStatus.SUCCEEDED,
        phase=SyncJobPhase.FINALIZE,
        completed_tables=50,
        completed_fields=500,
    )

    assert finished.finish_time is not None
    assert finished.status == SyncJobStatus.SUCCEEDED
    assert finished.phase == SyncJobPhase.FINALIZE

    loaded = get_sync_job_by_id(test_db, cast(int, finished.id))
    assert loaded is not None
    assert loaded.finish_time is not None
    assert loaded.completed_tables == 50
    assert loaded.completed_fields == 500


def test_increment_sync_job_progress_skips_commit_within_threshold(
    sync_job_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=12, oid=1, create_by=3)
    commit_count = 0
    original_commit = test_db.commit

    def counting_commit() -> None:
        nonlocal commit_count
        commit_count += 1
        original_commit()

    monkeypatch.setattr(test_db, "commit", counting_commit)
    monkeypatch.setattr(
        "apps.datasource.crud.sync_job.settings.DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
        9999,
    )

    increment_sync_job_progress(
        test_db,
        job=job,
        completed_tables_delta=1,
        completed_fields_delta=5,
        current_table_name="orders",
    )

    assert commit_count == 0
    assert job.completed_tables == 1
    assert job.completed_fields == 5
    assert job.current_table_name == "orders"


def test_increment_sync_job_progress_commits_after_threshold(
    sync_job_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=13, oid=1, create_by=3)
    commit_count = 0
    original_commit = test_db.commit

    def counting_commit() -> None:
        nonlocal commit_count
        commit_count += 1
        original_commit()

    monkeypatch.setattr(test_db, "commit", counting_commit)
    monkeypatch.setattr(
        "apps.datasource.crud.sync_job.settings.DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
        0,
    )

    increment_sync_job_progress(
        test_db,
        job=job,
        completed_tables_delta=2,
        failed_tables_delta=1,
        completed_fields_delta=10,
        current_table_name="customers",
    )

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert commit_count == 1
    assert loaded is not None
    assert loaded.completed_tables == 2
    assert loaded.failed_tables == 1
    assert loaded.completed_fields == 10
    assert loaded.current_table_name == "customers"


def test_increment_sync_job_progress_force_commit_persists_accumulated_values(
    sync_job_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=14, oid=1, create_by=3)
    monkeypatch.setattr(
        "apps.datasource.crud.sync_job.settings.DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
        9999,
    )

    increment_sync_job_progress(
        test_db,
        job=job,
        completed_tables_delta=1,
        completed_fields_delta=3,
    )
    increment_sync_job_progress(
        test_db,
        job=job,
        completed_tables_delta=2,
        completed_fields_delta=7,
        force_commit=True,
    )

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.completed_tables == 3
    assert loaded.completed_fields == 10
