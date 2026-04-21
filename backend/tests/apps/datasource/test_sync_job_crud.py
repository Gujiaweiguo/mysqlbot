from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel

from apps.datasource.crud.sync_job import (
    build_sync_job_status_response,
    cancel_sync_job,
    create_sync_job,
    get_active_sync_job,
    get_sync_job_by_id,
    increment_sync_job_progress,
    list_sync_jobs_by_ds,
    retry_sync_job,
    submit_datasource_sync_job,
    update_sync_job_status,
)
from apps.datasource.models.datasource import SelectedTablePayload
from apps.datasource.models.sync_job import (
    ACTIVE_DATASOURCE_SYNC_JOB_STATUSES,
    DatasourceSyncJob,
    DatasourceSyncJobStatusResponse,
    SyncJobPhase,
    SyncJobStatus,
    TERMINAL_DATASOURCE_SYNC_JOB_STATUSES,
    dump_selected_tables_payload,
    load_selected_tables_payload,
)


@pytest.fixture
def sync_job_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [cast(Any, DatasourceSyncJob).__table__]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


# ---------------------------------------------------------------------------
# create_sync_job
# ---------------------------------------------------------------------------


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


def test_create_sync_job_defaults_zero_counters(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=1, oid=1, create_by=1)

    assert job.total_tables == 0
    assert job.completed_tables == 0
    assert job.failed_tables == 0
    assert job.skipped_tables == 0
    assert job.total_fields == 0
    assert job.completed_fields == 0
    assert job.requested_tables == "[]"


# ---------------------------------------------------------------------------
# get_active_sync_job
# ---------------------------------------------------------------------------


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


def test_get_active_sync_job_returns_none_when_no_active(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    assert get_active_sync_job(test_db, 99) is None


def test_get_active_sync_job_one_per_datasource_across_multiple(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    # ds_id=10 has an active RUNNING job
    job_a = create_sync_job(test_db, ds_id=10, oid=1, create_by=1)
    update_sync_job_status(
        test_db, job=job_a, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE
    )
    # ds_id=20 has a terminal job
    job_b = create_sync_job(test_db, ds_id=20, oid=1, create_by=1)
    update_sync_job_status(
        test_db, job=job_b, status=SyncJobStatus.SUCCEEDED, phase=SyncJobPhase.FINALIZE
    )
    # ds_id=30 has a PENDING job
    job_c = create_sync_job(test_db, ds_id=30, oid=1, create_by=1)

    active_10 = get_active_sync_job(test_db, 10)
    assert active_10 is not None
    assert active_10.id == job_a.id
    assert get_active_sync_job(test_db, 20) is None
    active_30 = get_active_sync_job(test_db, 30)
    assert active_30 is not None
    assert active_30.id == job_c.id
    assert get_active_sync_job(test_db, 40) is None


def test_get_active_sync_job_returns_most_recent(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    # Create two active jobs for same ds_id — CRUD layer doesn't enforce unique,
    # but get_active should return the newest one (ordered by create_time desc)
    first = create_sync_job(test_db, ds_id=50, oid=1, create_by=1)
    second = create_sync_job(test_db, ds_id=50, oid=1, create_by=1)

    loaded = get_active_sync_job(test_db, 50)
    assert loaded is not None
    assert loaded.id == second.id


# ---------------------------------------------------------------------------
# update_sync_job_status — status transitions & timestamps
# ---------------------------------------------------------------------------


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


def test_full_lifecycle_pending_to_succeeded(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=100, oid=1, create_by=1)

    # PENDING → RUNNING
    running = update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.INTROSPECT
    )
    assert running.start_time is not None
    assert running.finish_time is None
    assert running.status == SyncJobStatus.RUNNING

    # RUNNING → FINALIZING
    finalizing = update_sync_job_status(
        test_db,
        job=running,
        status=SyncJobStatus.FINALIZING,
        phase=SyncJobPhase.FINALIZE,
    )
    assert finalizing.status == SyncJobStatus.FINALIZING
    # start_time already set, should not change
    assert finalizing.start_time == running.start_time

    # FINALIZING → SUCCEEDED
    succeeded = update_sync_job_status(
        test_db,
        job=finalizing,
        status=SyncJobStatus.SUCCEEDED,
        phase=SyncJobPhase.POST_PROCESS,
    )
    assert succeeded.finish_time is not None
    assert succeeded.status == SyncJobStatus.SUCCEEDED


def test_full_lifecycle_pending_to_failed(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=101, oid=1, create_by=1)

    running = update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE
    )
    failed = update_sync_job_status(
        test_db,
        job=running,
        status=SyncJobStatus.FAILED,
        phase=SyncJobPhase.STAGE,
        error_summary="connection refused",
        failed_tables=3,
    )
    assert failed.finish_time is not None
    assert failed.status == SyncJobStatus.FAILED
    assert failed.error_summary == "connection refused"
    assert failed.failed_tables == 3


def test_full_lifecycle_pending_to_partial(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(
        test_db, ds_id=102, oid=1, create_by=1, total_tables=10, total_fields=100
    )

    running = update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE
    )
    partial = update_sync_job_status(
        test_db,
        job=running,
        status=SyncJobStatus.PARTIAL,
        phase=SyncJobPhase.FINALIZE,
        completed_tables=7,
        failed_tables=2,
        skipped_tables=1,
        error_summary="2 of 10 tables failed",
    )
    assert partial.finish_time is not None
    assert partial.status == SyncJobStatus.PARTIAL
    assert partial.completed_tables == 7
    assert partial.failed_tables == 2
    assert partial.skipped_tables == 1


def test_full_lifecycle_pending_to_cancelled(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=103, oid=1, create_by=1)

    running = update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.INTROSPECT
    )
    cancelled = update_sync_job_status(
        test_db, job=running, status=SyncJobStatus.CANCELLED
    )
    assert cancelled.finish_time is not None
    assert cancelled.status == SyncJobStatus.CANCELLED


def test_update_sync_job_status_does_not_overwrite_start_time(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=200, oid=1, create_by=1)
    running = update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE
    )
    original_start = running.start_time
    assert original_start is not None

    # Transition to FINALIZING — start_time should remain unchanged
    finalizing = update_sync_job_status(
        test_db, job=running, status=SyncJobStatus.FINALIZING, phase=SyncJobPhase.FINALIZE
    )
    assert finalizing.start_time == original_start


# ---------------------------------------------------------------------------
# increment_sync_job_progress — throttling
# ---------------------------------------------------------------------------


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


def test_increment_sync_job_progress_accumulates_skipped_and_total_fields(
    sync_job_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=15, oid=1, create_by=3)
    monkeypatch.setattr(
        "apps.datasource.crud.sync_job.settings.DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
        0,
    )

    increment_sync_job_progress(
        test_db,
        job=job,
        skipped_tables_delta=2,
        total_fields_delta=50,
    )
    increment_sync_job_progress(
        test_db,
        job=job,
        skipped_tables_delta=1,
        total_fields_delta=30,
    )

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.skipped_tables == 3
    assert loaded.total_fields == 80


# ---------------------------------------------------------------------------
# cancel_sync_job
# ---------------------------------------------------------------------------


def test_cancel_sync_job_on_pending(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=300, oid=1, create_by=1)
    cancelled = cancel_sync_job(test_db, job=job)

    assert cancelled.status == SyncJobStatus.CANCELLED
    assert cancelled.finish_time is not None
    assert cancelled.error_summary == "sync job cancelled by operator"


def test_cancel_sync_job_on_running(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=301, oid=1, create_by=1)
    running = update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE
    )
    cancelled = cancel_sync_job(test_db, job=running)

    assert cancelled.status == SyncJobStatus.CANCELLED
    assert cancelled.finish_time is not None


def test_cancel_sync_job_on_finalizing(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=302, oid=1, create_by=1)
    finalizing = update_sync_job_status(
        test_db,
        job=job,
        status=SyncJobStatus.FINALIZING,
        phase=SyncJobPhase.FINALIZE,
    )
    cancelled = cancel_sync_job(test_db, job=finalizing)

    assert cancelled.status == SyncJobStatus.CANCELLED


@pytest.mark.parametrize(
    "status",
    [
        SyncJobStatus.SUCCEEDED,
        SyncJobStatus.FAILED,
        SyncJobStatus.PARTIAL,
        SyncJobStatus.CANCELLED,
    ],
)
def test_cancel_sync_job_rejects_terminal_states(
    sync_job_tables: None,
    test_db: Session,
    status: SyncJobStatus,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=310, oid=1, create_by=1)
    update_sync_job_status(test_db, job=job, status=status)

    with pytest.raises(ValueError, match="not cancelable"):
        cancel_sync_job(test_db, job=job)


# ---------------------------------------------------------------------------
# retry_sync_job
# ---------------------------------------------------------------------------


def test_retry_sync_job_on_failed(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=400, oid=1, create_by=1)
    tables = [SelectedTablePayload(table_name="orders"), SelectedTablePayload(table_name="users")]
    job.requested_tables = dump_selected_tables_payload(tables)
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)

    update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.FAILED, error_summary="timeout"
    )

    result = retry_sync_job(test_db, job=job, oid=1, create_by=2)

    assert result.reused_active_job is False
    assert result.status == SyncJobStatus.PENDING
    assert result.datasource_id == 400


def test_retry_sync_job_on_partial(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=401, oid=1, create_by=1)
    tables = [SelectedTablePayload(table_name="t1")]
    job.requested_tables = dump_selected_tables_payload(tables)
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)

    update_sync_job_status(test_db, job=job, status=SyncJobStatus.PARTIAL)

    result = retry_sync_job(test_db, job=job, oid=1, create_by=1)
    assert result.reused_active_job is False


def test_retry_sync_job_on_cancelled(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=402, oid=1, create_by=1)
    tables = [SelectedTablePayload(table_name="t1")]
    job.requested_tables = dump_selected_tables_payload(tables)
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)

    update_sync_job_status(test_db, job=job, status=SyncJobStatus.CANCELLED)

    result = retry_sync_job(test_db, job=job, oid=1, create_by=1)
    assert result.reused_active_job is False


@pytest.mark.parametrize(
    "status",
    [
        SyncJobStatus.PENDING,
        SyncJobStatus.RUNNING,
        SyncJobStatus.FINALIZING,
        SyncJobStatus.SUCCEEDED,
    ],
)
def test_retry_sync_job_rejects_non_retryable_states(
    sync_job_tables: None,
    test_db: Session,
    status: SyncJobStatus,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=410, oid=1, create_by=1)
    update_sync_job_status(test_db, job=job, status=status)

    with pytest.raises(ValueError, match="not retryable"):
        retry_sync_job(test_db, job=job, oid=1, create_by=1)


def test_retry_sync_job_rejects_when_no_requested_tables(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(test_db, ds_id=420, oid=1, create_by=1)
    # requested_tables defaults to "[]"
    update_sync_job_status(test_db, job=job, status=SyncJobStatus.FAILED)

    with pytest.raises(ValueError, match="no requested tables"):
        retry_sync_job(test_db, job=job, oid=1, create_by=1)


# ---------------------------------------------------------------------------
# submit_datasource_sync_job — idempotent active-job reuse
# ---------------------------------------------------------------------------


def test_submit_returns_new_job_when_no_active(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    result = submit_datasource_sync_job(
        test_db,
        ds_id=500,
        oid=1,
        create_by=1,
        total_tables=10,
    )

    assert result.reused_active_job is False
    assert result.datasource_id == 500
    assert result.status == SyncJobStatus.PENDING


def test_submit_reuses_active_pending_job(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    first = submit_datasource_sync_job(
        test_db, ds_id=501, oid=1, create_by=1, total_tables=5
    )
    assert first.reused_active_job is False

    second = submit_datasource_sync_job(
        test_db, ds_id=501, oid=1, create_by=1, total_tables=5
    )
    assert second.reused_active_job is True
    assert second.job_id == first.job_id
    assert second.status == SyncJobStatus.PENDING


def test_submit_reuses_active_running_job(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    first = submit_datasource_sync_job(
        test_db, ds_id=502, oid=1, create_by=1, total_tables=5
    )
    job = get_sync_job_by_id(test_db, first.job_id)
    assert job is not None
    update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE
    )

    second = submit_datasource_sync_job(
        test_db, ds_id=502, oid=1, create_by=1, total_tables=5
    )
    assert second.reused_active_job is True
    assert second.status == SyncJobStatus.RUNNING


def test_submit_creates_new_job_after_terminal(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    first = submit_datasource_sync_job(
        test_db, ds_id=503, oid=1, create_by=1, total_tables=5
    )
    job = get_sync_job_by_id(test_db, first.job_id)
    assert job is not None
    update_sync_job_status(
        test_db, job=job, status=SyncJobStatus.SUCCEEDED, phase=SyncJobPhase.FINALIZE
    )

    second = submit_datasource_sync_job(
        test_db, ds_id=503, oid=1, create_by=1, total_tables=10
    )
    assert second.reused_active_job is False
    assert second.job_id != first.job_id


def test_submit_with_requested_tables(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    tables = [
        SelectedTablePayload(table_name="orders", table_comment="sales orders"),
        SelectedTablePayload(table_name="users", table_comment="user accounts"),
    ]
    result = submit_datasource_sync_job(
        test_db,
        ds_id=504,
        oid=1,
        create_by=1,
        total_tables=2,
        requested_tables=tables,
    )

    assert result.reused_active_job is False
    job = get_sync_job_by_id(test_db, result.job_id)
    assert job is not None
    loaded_tables = load_selected_tables_payload(job.requested_tables)
    assert len(loaded_tables) == 2
    assert loaded_tables[0].table_name == "orders"
    assert loaded_tables[1].table_name == "users"


# ---------------------------------------------------------------------------
# list_sync_jobs_by_ds
# ---------------------------------------------------------------------------


def test_list_sync_jobs_by_ds_returns_most_recent_first(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    j1 = create_sync_job(test_db, ds_id=600, oid=1, create_by=1)
    j2 = create_sync_job(test_db, ds_id=600, oid=1, create_by=1)
    j3 = create_sync_job(test_db, ds_id=600, oid=1, create_by=1)

    jobs = list_sync_jobs_by_ds(test_db, 600)

    assert len(jobs) == 3
    assert jobs[0].id == j3.id
    assert jobs[1].id == j2.id
    assert jobs[2].id == j1.id


def test_list_sync_jobs_by_ds_respects_limit(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    for _ in range(5):
        create_sync_job(test_db, ds_id=601, oid=1, create_by=1)

    jobs = list_sync_jobs_by_ds(test_db, 601, limit=2)
    assert len(jobs) == 2


def test_list_sync_jobs_by_ds_isolation(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    create_sync_job(test_db, ds_id=700, oid=1, create_by=1)
    create_sync_job(test_db, ds_id=701, oid=1, create_by=1)
    create_sync_job(test_db, ds_id=701, oid=1, create_by=1)

    assert len(list_sync_jobs_by_ds(test_db, 700)) == 1
    assert len(list_sync_jobs_by_ds(test_db, 701)) == 2
    assert len(list_sync_jobs_by_ds(test_db, 702)) == 0


# ---------------------------------------------------------------------------
# build_sync_job_status_response
# ---------------------------------------------------------------------------


def test_build_sync_job_status_response(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = create_sync_job(
        test_db, ds_id=800, oid=5, create_by=10, total_tables=20, total_fields=200
    )
    running = update_sync_job_status(
        test_db,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        completed_tables=5,
        completed_fields=50,
        current_table_name="products",
    )

    resp = build_sync_job_status_response(running)

    assert isinstance(resp, DatasourceSyncJobStatusResponse)
    assert resp.job_id == running.id
    assert resp.datasource_id == 800
    assert resp.status == SyncJobStatus.RUNNING
    assert resp.phase == SyncJobPhase.STAGE
    assert resp.total_tables == 20
    assert resp.completed_tables == 5
    assert resp.completed_fields == 50
    assert resp.current_table_name == "products"
    assert resp.start_time is not None
    assert resp.finish_time is None


def test_build_sync_job_status_response_raises_on_missing_id(
    sync_job_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_tables
    job = DatasourceSyncJob(
        ds_id=999,
        oid=1,
        create_by=1,
        status=SyncJobStatus.PENDING,
        phase=SyncJobPhase.SUBMIT,
        create_time=datetime.now(),
        update_time=datetime.now(),
    )
    # id is None because it was never persisted

    with pytest.raises(ValueError, match="sync job id is missing"):
        build_sync_job_status_response(job)


# ---------------------------------------------------------------------------
# Enum & frozenset completeness checks
# ---------------------------------------------------------------------------


def test_active_and_terminal_statuses_are_disjoint_and_complete() -> None:
    active_values = {s.value for s in ACTIVE_DATASOURCE_SYNC_JOB_STATUSES}
    terminal_values = {s.value for s in TERMINAL_DATASOURCE_SYNC_JOB_STATUSES}
    assert active_values.isdisjoint(terminal_values)

    all_values = active_values | terminal_values
    expected = {s.value for s in SyncJobStatus}
    assert all_values == expected


def test_all_seven_statuses_exist() -> None:
    assert len(SyncJobStatus) == 7
    assert len(SyncJobPhase) == 5


def test_requested_tables_payload_round_trip() -> None:
    tables = [
        SelectedTablePayload(table_name="orders", table_comment="sales"),
        SelectedTablePayload(table_name="users"),
    ]
    dumped = dump_selected_tables_payload(tables)
    loaded = load_selected_tables_payload(dumped)

    assert len(loaded) == 2
    assert loaded[0].table_name == "orders"
    assert loaded[0].table_comment == "sales"
    assert loaded[1].table_name == "users"
    assert loaded[1].table_comment == ""
