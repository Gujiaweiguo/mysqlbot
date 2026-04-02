from __future__ import annotations

from collections.abc import Generator
from concurrent.futures import Future
from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from prometheus_client import REGISTRY
from sqlmodel import Session, SQLModel

from apps.datasource.crud.sync_job import (
    create_sync_job,
    get_sync_job_by_id,
    submit_datasource_sync_job,
    update_sync_job_status,
)
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    SyncJobStatus,
)
from common.core.config import settings
from common.utils import sync_job_runtime


def _sample_value(name: str, labels: dict[str, str] | None = None) -> float:
    value = REGISTRY.get_sample_value(name, labels)
    if value is None:
        return 0.0
    return float(value)


@pytest.fixture
def sync_job_runtime_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [cast(Any, DatasourceSyncJob).__table__]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


class FakeSessionFactory:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.remove_calls = 0

    def __call__(self) -> Session:
        return self.session

    def remove(self) -> None:
        self.remove_calls += 1


def test_run_sync_job_transitions_pending_to_succeeded(
    sync_job_runtime_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runtime_tables
    job = create_sync_job(test_db, ds_id=7, oid=1, create_by=1, total_tables=20)
    session_factory = FakeSessionFactory(test_db)

    def fake_visibility_guard(
        status_session: Session,
        work_session: Session,
        job_obj: DatasourceSyncJob,
    ) -> None:
        _ = work_session
        update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.INTROSPECT,
        )
        update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.SUCCEEDED,
            phase=SyncJobPhase.FINALIZE,
        )

    monkeypatch.setattr(
        sync_job_runtime, "_run_sync_job_with_visibility_guard", fake_visibility_guard
    )

    sync_job_runtime.run_sync_job_with_session_factory(
        session_factory, cast(int, job.id)
    )

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.status == SyncJobStatus.SUCCEEDED
    assert loaded.phase == SyncJobPhase.FINALIZE
    assert loaded.start_time is not None
    assert loaded.finish_time is not None
    assert session_factory.remove_calls == 1


def test_run_sync_job_failure_transitions_to_failed(
    sync_job_runtime_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runtime_tables
    job = create_sync_job(test_db, ds_id=8, oid=1, create_by=1, total_tables=20)
    session_factory = FakeSessionFactory(test_db)

    def fake_visibility_guard(
        status_session: Session,
        work_session: Session,
        job_obj: DatasourceSyncJob,
    ) -> None:
        _ = status_session
        _ = work_session
        _ = job_obj
        raise RuntimeError("boom")

    monkeypatch.setattr(
        sync_job_runtime, "_run_sync_job_with_visibility_guard", fake_visibility_guard
    )

    sync_job_runtime.run_sync_job_with_session_factory(
        session_factory, cast(int, job.id)
    )

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.status == SyncJobStatus.FAILED
    assert loaded.error_summary == "boom"
    assert session_factory.remove_calls == 1


def test_dispatch_sync_job_submits_runner_with_shared_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submissions: list[tuple[object, object, int]] = []
    future: Future[None] = Future()

    class FakeExecutor:
        def submit(
            self, fn: object, session_factory: object, job_id: int
        ) -> Future[None]:
            submissions.append((fn, session_factory, job_id))
            return future

    monkeypatch.setattr(sync_job_runtime, "sync_job_executor", FakeExecutor())

    result = sync_job_runtime.dispatch_sync_job(42)

    assert result is future
    assert submissions == [
        (
            sync_job_runtime.run_sync_job_with_session_factory,
            sync_job_runtime.sync_job_session_maker,
            42,
        )
    ]


def test_second_submit_for_same_datasource_reuses_active_job(
    sync_job_runtime_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_runtime_tables
    first = submit_datasource_sync_job(
        test_db,
        ds_id=10,
        oid=1,
        create_by=1,
        total_tables=100,
    )
    second = submit_datasource_sync_job(
        test_db,
        ds_id=10,
        oid=1,
        create_by=1,
        total_tables=200,
    )

    assert first.reused_active_job is False
    assert second.reused_active_job is True
    assert second.job_id == first.job_id


def test_submit_metrics_count_new_and_reused_jobs(
    sync_job_runtime_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_runtime_tables
    before_new = _sample_value(
        "sqlbot_sync_jobs_submitted_total", {"reused_active": "false"}
    )
    before_reused = _sample_value(
        "sqlbot_sync_jobs_submitted_total", {"reused_active": "true"}
    )

    _ = submit_datasource_sync_job(
        test_db,
        ds_id=21,
        oid=1,
        create_by=1,
        total_tables=10,
    )
    _ = submit_datasource_sync_job(
        test_db,
        ds_id=21,
        oid=1,
        create_by=1,
        total_tables=10,
    )

    after_new = _sample_value(
        "sqlbot_sync_jobs_submitted_total", {"reused_active": "false"}
    )
    after_reused = _sample_value(
        "sqlbot_sync_jobs_submitted_total", {"reused_active": "true"}
    )

    assert after_new - before_new == 1.0
    assert after_reused - before_reused == 1.0


def test_status_transition_metric_increments(
    sync_job_runtime_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_runtime_tables
    before_running = _sample_value(
        "sqlbot_sync_job_status_transitions_total", {"status": "running"}
    )
    before_succeeded = _sample_value(
        "sqlbot_sync_job_status_transitions_total", {"status": "succeeded"}
    )
    job = create_sync_job(test_db, ds_id=22, oid=1, create_by=1)

    update_sync_job_status(
        test_db,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
    )
    update_sync_job_status(
        test_db,
        job=job,
        status=SyncJobStatus.SUCCEEDED,
        phase=SyncJobPhase.FINALIZE,
    )

    after_running = _sample_value(
        "sqlbot_sync_job_status_transitions_total", {"status": "running"}
    )
    after_succeeded = _sample_value(
        "sqlbot_sync_job_status_transitions_total", {"status": "succeeded"}
    )

    assert after_running - before_running == 1.0
    assert after_succeeded - before_succeeded == 1.0


def test_recover_stale_sync_jobs_marks_old_running_as_failed(
    sync_job_runtime_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_runtime_tables
    old_job = create_sync_job(test_db, ds_id=11, oid=1, create_by=1, total_tables=10)
    update_sync_job_status(
        test_db,
        job=old_job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
    )
    old_job.update_time = datetime.now() - timedelta(
        seconds=settings.DATASOURCE_SYNC_JOB_STALE_TIMEOUT_SECONDS + 10
    )
    test_db.add(old_job)
    test_db.commit()
    session_factory = FakeSessionFactory(test_db)

    recovered = sync_job_runtime.recover_stale_sync_jobs(session_factory)

    loaded = get_sync_job_by_id(test_db, cast(int, old_job.id))
    assert recovered == [cast(int, old_job.id)]
    assert loaded is not None
    assert loaded.status == SyncJobStatus.FAILED
    assert loaded.error_summary == "sync job marked failed after stale timeout"


def test_recover_stale_sync_jobs_ignores_recent_and_terminal_jobs(
    sync_job_runtime_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_runtime_tables
    recent = create_sync_job(test_db, ds_id=12, oid=1, create_by=1)
    update_sync_job_status(
        test_db,
        job=recent,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
    )
    terminal = create_sync_job(test_db, ds_id=13, oid=1, create_by=1)
    update_sync_job_status(
        test_db,
        job=terminal,
        status=SyncJobStatus.SUCCEEDED,
        phase=SyncJobPhase.FINALIZE,
    )
    recent_id = cast(int, recent.id)
    terminal_id = cast(int, terminal.id)
    session_factory = FakeSessionFactory(test_db)

    recovered = sync_job_runtime.recover_stale_sync_jobs(session_factory)

    recent_loaded = get_sync_job_by_id(test_db, recent_id)
    terminal_loaded = get_sync_job_by_id(test_db, terminal_id)
    assert recovered == []
    assert recent_loaded is not None
    assert recent_loaded.status == SyncJobStatus.RUNNING
    assert terminal_loaded is not None
    assert terminal_loaded.status == SyncJobStatus.SUCCEEDED


def test_sync_job_executor_has_bounded_workers() -> None:
    assert (
        sync_job_runtime.sync_job_executor._max_workers
        == settings.DATASOURCE_SYNC_JOB_MAX_WORKERS
    )


def test_successful_embedding_dispatch_marks_followup_dispatched(
    sync_job_runtime_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runtime_tables
    job = create_sync_job(test_db, ds_id=15, oid=1, create_by=1, total_tables=1)
    job_id = cast(int, job.id)
    session_factory = FakeSessionFactory(test_db)

    def fake_visibility_guard(
        status_session: Session,
        work_session: Session,
        job_obj: DatasourceSyncJob,
    ) -> None:
        _ = work_session
        update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.SUCCEEDED,
            phase=SyncJobPhase.POST_PROCESS,
        )
        job_obj.embedding_followup_status = "dispatched"
        status_session.add(job_obj)
        status_session.commit()

    monkeypatch.setattr(
        sync_job_runtime, "_run_sync_job_with_visibility_guard", fake_visibility_guard
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    loaded = get_sync_job_by_id(test_db, job_id)
    assert loaded is not None
    assert loaded.status == SyncJobStatus.SUCCEEDED
    assert loaded.phase == SyncJobPhase.POST_PROCESS
    assert loaded.embedding_followup_status == "dispatched"


def test_embedding_dispatch_failure_marks_followup_failed(
    sync_job_runtime_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runtime_tables
    job = create_sync_job(test_db, ds_id=16, oid=1, create_by=1, total_tables=1)
    job_id = cast(int, job.id)
    session_factory = FakeSessionFactory(test_db)

    def fake_visibility_guard(
        status_session: Session,
        work_session: Session,
        job_obj: DatasourceSyncJob,
    ) -> None:
        _ = work_session
        update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.SUCCEEDED,
            phase=SyncJobPhase.POST_PROCESS,
        )
        job_obj.embedding_followup_status = "failed"
        status_session.add(job_obj)
        status_session.commit()

    monkeypatch.setattr(
        sync_job_runtime, "_run_sync_job_with_visibility_guard", fake_visibility_guard
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    loaded = get_sync_job_by_id(test_db, job_id)
    assert loaded is not None
    assert loaded.status == SyncJobStatus.SUCCEEDED
    assert loaded.phase == SyncJobPhase.POST_PROCESS
    assert loaded.embedding_followup_status == "failed"


def test_partial_status_when_some_tables_fail_introspection(
    sync_job_runtime_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runtime_tables
    job = create_sync_job(test_db, ds_id=30, oid=1, create_by=1, total_tables=3)
    session_factory = FakeSessionFactory(test_db)

    call_count = 0

    def fake_visibility_guard(
        status_session: Session,
        work_session: Session,
        job_obj: DatasourceSyncJob,
    ) -> None:
        nonlocal call_count
        _ = work_session
        call_count += 1
        update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.PARTIAL,
            phase=SyncJobPhase.POST_PROCESS,
            completed_tables=2,
            failed_tables=1,
            error_summary="1 of 3 tables failed during sync",
        )

    monkeypatch.setattr(
        sync_job_runtime, "_run_sync_job_with_visibility_guard", fake_visibility_guard
    )

    sync_job_runtime.run_sync_job_with_session_factory(
        session_factory, cast(int, job.id)
    )

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.status == SyncJobStatus.PARTIAL
    assert loaded.failed_tables == 1
    assert loaded.completed_tables == 2
    assert loaded.error_summary == "1 of 3 tables failed during sync"
    assert loaded.finish_time is not None
    assert call_count == 1


def test_partial_status_does_not_publish(
    sync_job_runtime_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_runtime_tables
    job = create_sync_job(test_db, ds_id=31, oid=1, create_by=1, total_tables=2)
    update_sync_job_status(
        test_db,
        job=job,
        status=SyncJobStatus.PARTIAL,
        phase=SyncJobPhase.POST_PROCESS,
    )

    from apps.datasource.models.sync_job import should_publish_datasource_sync_result

    assert should_publish_datasource_sync_result(job.status) is False


def test_partial_status_is_terminal(
    sync_job_runtime_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_runtime_tables
    job = create_sync_job(test_db, ds_id=32, oid=1, create_by=1, total_tables=2)
    update_sync_job_status(
        test_db,
        job=job,
        status=SyncJobStatus.PARTIAL,
        phase=SyncJobPhase.POST_PROCESS,
    )

    from apps.datasource.models.sync_job import TERMINAL_DATASOURCE_SYNC_JOB_STATUSES

    assert job.status in TERMINAL_DATASOURCE_SYNC_JOB_STATUSES
