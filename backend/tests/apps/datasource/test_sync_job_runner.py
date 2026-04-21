from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnannotatedClassAttribute=false, reportUnusedParameter=false, reportUnusedCallResult=false, reportPrivateUsage=false

from collections.abc import Generator
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Event, Lock, Semaphore
from time import sleep
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel

from apps.datasource.constants.sync import SYNC_JOB_MAX_WORKERS
from apps.datasource.crud.sync_job import create_sync_job, get_sync_job_by_id, update_sync_job_status
from apps.datasource.models.datasource import CoreDatasource, SelectedTablePayload
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    SyncJobStatus,
    dump_selected_tables_payload,
)
from apps.datasource.services.sync_engine import (
    IntrospectedTableSchema,
    PostProcessResult,
    StageBatchResult,
)
from common.utils import sync_job_runtime


@pytest.fixture
def sync_job_runner_tables(test_db_engine: Any) -> Generator[None, None, None]:
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


def _create_job(
    session: Session,
    *,
    ds_id: int,
    tables: list[SelectedTablePayload],
) -> DatasourceSyncJob:
    job = create_sync_job(session, ds_id=ds_id, oid=1, create_by=1, total_tables=len(tables))
    job.requested_tables = dump_selected_tables_payload(tables)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_run_sync_job_full_lifecycle_marks_succeeded(
    sync_job_runner_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runner_tables
    job = _create_job(
        test_db,
        ds_id=1,
        tables=[
            SelectedTablePayload(table_name="orders", table_comment="Orders"),
            SelectedTablePayload(table_name="customers", table_comment="Customers"),
        ],
    )
    session_factory = FakeSessionFactory(test_db)
    def fake_visibility_guard(
        status_session: Session,
        work_session: Session,
        job_obj: DatasourceSyncJob,
    ) -> None:
        _ = work_session
        _ = update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.INTROSPECT,
            total_tables=2,
        )
        _ = update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.FINALIZING,
            phase=SyncJobPhase.FINALIZE,
            completed_tables=2,
            total_fields=2,
            completed_fields=2,
        )
        _ = update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.SUCCEEDED,
            phase=SyncJobPhase.POST_PROCESS,
            completed_tables=2,
            total_fields=2,
            completed_fields=2,
        )

    monkeypatch.setattr(
        sync_job_runtime,
        "_run_sync_job_with_visibility_guard",
        fake_visibility_guard,
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, cast(int, job.id))

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.status == SyncJobStatus.SUCCEEDED
    assert loaded.phase == SyncJobPhase.POST_PROCESS
    assert loaded.completed_tables == 2
    assert loaded.failed_tables == 0
    assert loaded.total_fields == 2
    assert loaded.completed_fields == 2
    assert loaded.start_time is not None
    assert loaded.finish_time is not None
    assert session_factory.remove_calls == 1


@pytest.mark.parametrize(
    ("stage_name", "expected_phase", "expected_error"),
    [
        ("snapshot", SyncJobPhase.SUBMIT, "snapshot boom"),
        ("introspect", SyncJobPhase.STAGE, "introspect:orders:introspect boom"),
        ("stage", SyncJobPhase.STAGE, "stage:orders:stage boom"),
        ("finalize", SyncJobPhase.FINALIZE, "finalize boom"),
        ("post_process", SyncJobPhase.FINALIZE, "post process boom"),
    ],
)
def test_stage_failures_mark_job_failed(
    stage_name: str,
    expected_phase: SyncJobPhase,
    expected_error: str,
    sync_job_runner_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runner_tables
    job = _create_job(
        test_db,
        ds_id=1,
        tables=[SelectedTablePayload(table_name="orders", table_comment="Orders")],
    )
    session_factory = FakeSessionFactory(test_db)

    def fake_visibility_guard(
        status_session: Session,
        work_session: Session,
        job_obj: DatasourceSyncJob,
    ) -> None:
        _ = work_session
        if stage_name == "snapshot":
            raise RuntimeError("snapshot boom")
        if stage_name == "introspect":
            _ = update_sync_job_status(
                status_session,
                job=job_obj,
                status=SyncJobStatus.RUNNING,
                phase=SyncJobPhase.STAGE,
            )
            raise RuntimeError("introspect:orders:introspect boom")
        if stage_name == "stage":
            _ = update_sync_job_status(
                status_session,
                job=job_obj,
                status=SyncJobStatus.RUNNING,
                phase=SyncJobPhase.STAGE,
            )
            raise RuntimeError("stage:orders:stage boom")
        if stage_name == "finalize":
            _ = update_sync_job_status(
                status_session,
                job=job_obj,
                status=SyncJobStatus.FINALIZING,
                phase=SyncJobPhase.FINALIZE,
            )
            raise RuntimeError("finalize boom")
        _ = update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.FINALIZING,
            phase=SyncJobPhase.FINALIZE,
        )
        raise RuntimeError("post process boom")

    monkeypatch.setattr(
        sync_job_runtime,
        "_run_sync_job_with_visibility_guard",
        fake_visibility_guard,
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, cast(int, job.id))

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.status == SyncJobStatus.FAILED
    assert loaded.phase == expected_phase
    assert loaded.error_summary == expected_error
    assert loaded.finish_time is not None


def test_partial_status_when_some_tables_fail(
    sync_job_runner_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runner_tables
    job = _create_job(
        test_db,
        ds_id=1,
        tables=[
            SelectedTablePayload(table_name="orders", table_comment="Orders"),
            SelectedTablePayload(table_name="customers", table_comment="Customers"),
        ],
    )
    session_factory = FakeSessionFactory(test_db)

    def fake_visibility_guard(
        status_session: Session,
        work_session: Session,
        job_obj: DatasourceSyncJob,
    ) -> None:
        _ = work_session
        _ = update_sync_job_status(
            status_session,
            job=job_obj,
            status=SyncJobStatus.PARTIAL,
            phase=SyncJobPhase.POST_PROCESS,
            total_tables=2,
            completed_tables=1,
            failed_tables=1,
            total_fields=1,
            completed_fields=1,
            error_summary="1 of 2 tables failed during sync",
        )

    monkeypatch.setattr(
        sync_job_runtime,
        "_run_sync_job_with_visibility_guard",
        fake_visibility_guard,
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, cast(int, job.id))

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.status == SyncJobStatus.PARTIAL
    assert loaded.phase == SyncJobPhase.POST_PROCESS
    assert loaded.completed_tables == 1
    assert loaded.failed_tables == 1
    assert loaded.total_fields == 1
    assert loaded.completed_fields == 1
    assert loaded.error_summary == "1 of 2 tables failed during sync"


def test_visibility_guard_uses_service_pipeline_and_defers_post_process(
    sync_job_runner_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runner_tables
    job = _create_job(
        test_db,
        ds_id=1,
        tables=[
            SelectedTablePayload(table_name="orders", table_comment="Orders"),
            SelectedTablePayload(table_name="customers", table_comment="Customers"),
        ],
    )
    events: list[str] = []
    original_session_get = Session.get

    fake_datasource = CoreDatasource(
        id=1,
        name="ds",
        description=None,
        type="mysql",
        type_name="mysql",
        configuration="{}",
        create_time=None,
        create_by=1,
        status="Success",
        num="0/1",
        oid=1,
        table_relation=[],
        embedding=None,
        recommended_config=1,
    )

    def fake_session_get(self: Session, entity: Any, ident: Any) -> Any:
        if entity is CoreDatasource and ident == 1:
            return fake_datasource
        return original_session_get(self, entity, ident)

    def fake_from_job(
        cls: type[object],
        *,
        ds: CoreDatasource,
        job: DatasourceSyncJob,
        requested_tables: list[SelectedTablePayload],
        metadata_context: object | None = None,
    ) -> object:
        _ = cls
        return sync_job_runtime.SyncJobContext(
            ds=ds,
            job=job,
            requested_tables=requested_tables,
            metadata_context=cast(Any, metadata_context or object()),
        )

    def fake_snapshot(session: Session, context: object) -> object:
        _ = session
        _ = context
        events.append("snapshot")
        return object()

    def fake_introspect(
        context: object,
        *,
        tables: list[SelectedTablePayload] | None = None,
    ) -> list[IntrospectedTableSchema]:
        _ = context
        assert tables is not None
        events.append(f"introspect:{','.join(table.table_name for table in tables)}")
        return [
            IntrospectedTableSchema(table=table, fields=[])
            for table in tables
        ]

    def fake_probe_stage_batch(*, introspected_batch: list[IntrospectedTableSchema], **_: object) -> None:
        events.append(
            f"probe:{','.join(item.table.table_name for item in introspected_batch)}"
        )

    def fake_stage_batch(
        session: Session,
        context: object,
        introspected_tables: list[IntrospectedTableSchema],
        *,
        batch_size: int,
        field_batch_size: int,
    ) -> StageBatchResult:
        _ = session
        _ = context
        _ = batch_size
        _ = field_batch_size
        events.append(
            f"publish:{','.join(item.table.table_name for item in introspected_tables)}"
        )
        return StageBatchResult(
            phase=SyncJobPhase.STAGE,
            table_ids=[index + 1 for index, _ in enumerate(introspected_tables)],
            total_fields=0,
            completed_tables=len(introspected_tables),
            completed_fields=0,
            commit_count=1,
        )

    def fake_finalize(session: Session, context: object, *, staged_table_ids: list[int]) -> SyncJobPhase:
        _ = session
        _ = context
        events.append(f"finalize:{staged_table_ids}")
        return SyncJobPhase.FINALIZE

    def fake_commit_work_session(session: Session) -> None:
        _ = session
        events.append("commit")

    def fake_post_process(
        session: Session,
        context: object,
        *,
        table_ids: list[int],
        chunk_size: int,
    ) -> PostProcessResult:
        _ = session
        _ = context
        _ = chunk_size
        events.append(f"post_process:{table_ids}")
        return PostProcessResult(
            phase=SyncJobPhase.POST_PROCESS,
            dispatched_table_ids=table_ids,
            chunk_count=1,
        )

    monkeypatch.setattr(Session, "get", fake_session_get)
    monkeypatch.setattr(
        sync_job_runtime.SyncJobContext,
        "from_job",
        classmethod(fake_from_job),
    )
    monkeypatch.setattr(sync_job_runtime, "snapshot_requested_tables", fake_snapshot)
    monkeypatch.setattr(sync_job_runtime, "introspect_remote_metadata", fake_introspect)
    monkeypatch.setattr(sync_job_runtime, "_probe_stage_batch", fake_probe_stage_batch)
    monkeypatch.setattr(sync_job_runtime, "stage_table_batch", fake_stage_batch)
    monkeypatch.setattr(sync_job_runtime, "finalize_sync", fake_finalize)
    monkeypatch.setattr(sync_job_runtime, "_commit_work_session", fake_commit_work_session)
    monkeypatch.setattr(sync_job_runtime, "post_process_embeddings", fake_post_process)

    sync_job_runtime._run_sync_job_with_visibility_guard(test_db, test_db, job)

    loaded = get_sync_job_by_id(test_db, cast(int, job.id))
    assert loaded is not None
    assert loaded.status == SyncJobStatus.SUCCEEDED
    assert loaded.phase == SyncJobPhase.POST_PROCESS
    assert events == [
        "snapshot",
        "introspect:orders,customers",
        "probe:orders,customers",
        "publish:orders,customers",
        "finalize:[1, 2]",
        "commit",
        "post_process:[1, 2]",
    ]


def test_single_active_job_enforcement_marks_pending_duplicate_failed(
    sync_job_runner_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_job_runner_tables
    active_job = _create_job(
        test_db,
        ds_id=1,
        tables=[SelectedTablePayload(table_name="orders", table_comment="Orders")],
    )
    pending_job = _create_job(
        test_db,
        ds_id=1,
        tables=[SelectedTablePayload(table_name="customers", table_comment="Customers")],
    )
    update_sync_job_status(
        test_db,
        job=active_job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
    )
    active_job_id = cast(int, active_job.id)
    pending_job_id = cast(int, pending_job.id)
    session_factory = FakeSessionFactory(test_db)
    primitive_calls = 0

    def fail_if_called(*args: Any, **kwargs: Any) -> None:
        nonlocal primitive_calls
        primitive_calls += 1

    monkeypatch.setattr(sync_job_runtime, "snapshot_requested_tables", fail_if_called)

    sync_job_runtime.run_sync_job_with_session_factory(
        session_factory,
        pending_job_id,
    )

    loaded_active = get_sync_job_by_id(test_db, active_job_id)
    loaded_pending = get_sync_job_by_id(test_db, pending_job_id)
    assert loaded_active is not None
    assert loaded_pending is not None
    assert loaded_active.status == SyncJobStatus.RUNNING
    assert loaded_pending.status == SyncJobStatus.FAILED
    assert (
        loaded_pending.error_summary
        == "another active sync job is already running for this datasource"
    )
    assert primitive_calls == 0


def test_recover_stale_sync_jobs_marks_old_active_jobs_failed(
    sync_job_runner_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_runner_tables
    stale_running = _create_job(
        test_db,
        ds_id=1,
        tables=[SelectedTablePayload(table_name="orders", table_comment="Orders")],
    )
    fresh_running = _create_job(
        test_db,
        ds_id=1,
        tables=[SelectedTablePayload(table_name="customers", table_comment="Customers")],
    )
    update_sync_job_status(
        test_db,
        job=stale_running,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
    )
    update_sync_job_status(
        test_db,
        job=fresh_running,
        status=SyncJobStatus.FINALIZING,
        phase=SyncJobPhase.FINALIZE,
    )
    stale_job_id = cast(int, stale_running.id)
    fresh_job_id = cast(int, fresh_running.id)
    stale_running.update_time = datetime.now() - timedelta(hours=2)
    fresh_running.update_time = datetime.now()
    test_db.add(stale_running)
    test_db.add(fresh_running)
    test_db.commit()
    session_factory = FakeSessionFactory(test_db)

    recovered = sync_job_runtime.recover_stale_sync_jobs(session_factory)

    loaded_stale = get_sync_job_by_id(test_db, stale_job_id)
    loaded_fresh = get_sync_job_by_id(test_db, fresh_job_id)
    assert recovered == [stale_job_id]
    assert loaded_stale is not None
    assert loaded_stale.status == SyncJobStatus.FAILED
    assert loaded_stale.error_summary == "sync job marked failed after stale timeout"
    assert loaded_fresh is not None
    assert loaded_fresh.status == SyncJobStatus.FINALIZING


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


def test_worker_concurrency_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySession:
        def close(self) -> None:
            return None

    class DummySessionFactory:
        def __init__(self) -> None:
            self.remove_calls = 0

        def __call__(self) -> Session:
            return cast(Any, DummySession())

        def remove(self) -> None:
            self.remove_calls += 1

    class TrackingLimiter:
        def __init__(self, capacity: int) -> None:
            self._semaphore = Semaphore(capacity)
            self._lock = Lock()
            self.current = 0
            self.max_seen = 0

        def acquire(self) -> bool:
            acquired = self._semaphore.acquire()
            with self._lock:
                self.current += 1
                self.max_seen = max(self.max_seen, self.current)
            return acquired

        def release(self) -> None:
            with self._lock:
                self.current -= 1
            self._semaphore.release()

    limiter = TrackingLimiter(capacity=2)
    started = Event()
    release = Event()
    start_count = 0
    start_lock = Lock()

    def fake_run_with_lock(session: object, work_session: object, job_id: int) -> None:
        nonlocal start_count
        _ = session
        _ = work_session
        _ = job_id
        with start_lock:
            start_count += 1
            if start_count == 2:
                started.set()
        assert started.wait(timeout=1)
        assert release.wait(timeout=1)

    monkeypatch.setattr(sync_job_runtime, "sync_job_worker_limiter", limiter)
    monkeypatch.setattr(sync_job_runtime, "_run_job_with_datasource_lock", fake_run_with_lock)
    monkeypatch.setattr(sync_job_runtime, "get_sync_job_by_id", lambda session, job_id: None)

    session_factory = DummySessionFactory()
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(
                sync_job_runtime.run_sync_job_with_session_factory,
                cast(Any, session_factory),
                job_id,
            )
            for job_id in (1, 2, 3)
        ]
        assert started.wait(timeout=1)
        sleep(0.05)
        release.set()
        for future in futures:
            future.result(timeout=1)

    assert limiter.max_seen == 2
    assert session_factory.remove_calls == 3
    assert sync_job_runtime.sync_job_executor._max_workers == SYNC_JOB_MAX_WORKERS
