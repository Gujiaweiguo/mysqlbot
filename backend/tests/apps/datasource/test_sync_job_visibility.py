from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false

from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, col, create_engine, select

from apps.datasource.crud.sync_job import (
    create_sync_job,
    get_sync_job_by_id,
    update_sync_job_status,
)
from apps.datasource.models.datasource import (
    ColumnSchema,
    CoreDatasource,
    CoreField,
    CoreTable,
    SelectedTablePayload,
)
from apps.datasource.models.sync_job import DatasourceSyncJob, SyncJobStatus, dump_selected_tables_payload
from apps.datasource.models.sync_job import SyncJobPhase
from apps.datasource.services.sync_engine import (
    IntrospectedTableSchema,
    PostProcessResult,
    finalize_sync as actual_finalize_sync,
)
from common.utils import sync_job_runtime


class EngineSessionFactory:
    def __init__(self, db_engine: Engine) -> None:
        self._db_engine: Engine = db_engine
        self.remove_calls: int = 0

    def __call__(self) -> Session:
        return Session(self._db_engine)

    def remove(self) -> None:
        self.remove_calls += 1


def _create_visibility_engine(tmp_path: Path) -> Engine:
    db_path = tmp_path / 'sync-job-visibility.db'
    engine = create_engine(f'sqlite:///{db_path}')
    tables = [
        cast(Any, CoreTable).__table__,
        cast(Any, CoreField).__table__,
        cast(Any, DatasourceSyncJob).__table__,
    ]
    SQLModel.metadata.create_all(engine, tables=tables)
    return engine


def _seed_existing_schema(session: Session) -> None:
    session.add(
        CoreTable(
            id=1,
            ds_id=1,
            checked=True,
            table_name='orders',
            table_comment='old orders',
            custom_comment='old orders',
            embedding=None,
        )
    )
    session.add(
        CoreField(
            id=1,
            ds_id=1,
            table_id=1,
            checked=True,
            field_name='legacy_id',
            field_type='bigint',
            field_comment='legacy',
            custom_comment='legacy',
            field_index=0,
        )
    )
    session.commit()


def _create_job(session: Session, *, tables: list[SelectedTablePayload]) -> int:
    job = create_sync_job(session, ds_id=1, oid=1, create_by=1, total_tables=len(tables))
    job.requested_tables = dump_selected_tables_payload(tables)
    session.add(job)
    session.commit()
    session.refresh(job)
    return cast(int, job.id)


def _patch_fake_datasource(monkeypatch: pytest.MonkeyPatch) -> None:
    original_session_get = Session.get
    fake_datasource = CoreDatasource(
        id=1,
        name='ds',
        description=None,
        type='mysql',
        type_name='mysql',
        configuration='{}',
        create_time=None,
        create_by=1,
        status='Success',
        num='0/1',
        oid=1,
        table_relation=[],
        embedding=None,
        recommended_config=1,
    )

    def fake_session_get(self: Session, entity: Any, ident: Any) -> Any:
        if entity is CoreDatasource and ident == 1:
            return fake_datasource
        return original_session_get(self, entity, ident)

    monkeypatch.setattr(Session, 'get', fake_session_get)


def _patch_sync_job_context(monkeypatch: pytest.MonkeyPatch) -> None:
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

    monkeypatch.setattr(
        sync_job_runtime.SyncJobContext,
        'from_job',
        classmethod(fake_from_job),
    )


def _fake_introspect(
    _context: object,
    *,
    tables: list[SelectedTablePayload] | None = None,
) -> list[IntrospectedTableSchema]:
    assert tables is not None
    return [
        IntrospectedTableSchema(
            table=table,
            fields=[ColumnSchema('legacy_id', 'bigint', f'{table.table_name} id')],
        )
        for table in tables
    ]


def test_visibility_guard_keeps_previous_schema_visible_until_finalize(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job_id = _create_job(
            setup_session,
            tables=[SelectedTablePayload(table_name='orders', table_comment='new orders')],
        )

    session_factory = EngineSessionFactory(engine)
    events: list[str] = []

    def finalize_with_visibility_check(
        session: Session,
        context: object,
        *,
        staged_table_ids: list[int],
    ) -> object:
        with Session(engine) as visible_session:
            visible_table = visible_session.exec(select(CoreTable)).first()
            visible_field = visible_session.exec(select(CoreField)).first()
            assert visible_table is not None
            assert visible_table.table_comment == 'old orders'
            assert visible_field is not None
            assert visible_field.field_comment == 'legacy'
        events.append('finalize')
        return actual_finalize_sync(
            session,
            cast(Any, context),
            staged_table_ids=staged_table_ids,
        )

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
        events.append('post_process')
        return PostProcessResult(
            phase=SyncJobPhase.POST_PROCESS,
            dispatched_table_ids=table_ids,
            chunk_count=1,
        )

    monkeypatch.setattr(sync_job_runtime, 'engine', engine)
    _patch_fake_datasource(monkeypatch)
    _patch_sync_job_context(monkeypatch)
    monkeypatch.setattr(sync_job_runtime, 'introspect_remote_metadata', _fake_introspect)
    monkeypatch.setattr(sync_job_runtime, 'finalize_sync', finalize_with_visibility_check)
    monkeypatch.setattr(sync_job_runtime, 'post_process_embeddings', fake_post_process)

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    with Session(engine) as assert_session:
        loaded_job = get_sync_job_by_id(assert_session, job_id)
        visible_table = assert_session.exec(select(CoreTable)).first()
        visible_fields = list(assert_session.exec(select(CoreField)).all())
        assert loaded_job is not None
        assert loaded_job.status == SyncJobStatus.SUCCEEDED
        assert visible_table is not None
        assert visible_table.table_comment == 'new orders'
        assert [field.field_name for field in visible_fields] == ['legacy_id']
        assert visible_fields[0].field_comment == 'orders id'
        assert events == ['finalize', 'post_process']


def test_visibility_guard_rolls_back_and_preserves_previous_schema_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job_id = _create_job(
            setup_session,
            tables=[SelectedTablePayload(table_name='orders', table_comment='new orders')],
        )

    session_factory = EngineSessionFactory(engine)

    monkeypatch.setattr(sync_job_runtime, 'engine', engine)
    _patch_fake_datasource(monkeypatch)
    _patch_sync_job_context(monkeypatch)
    monkeypatch.setattr(sync_job_runtime, 'introspect_remote_metadata', _fake_introspect)
    monkeypatch.setattr(
        sync_job_runtime,
        '_probe_stage_batch',
        lambda **_: (_ for _ in ()).throw(RuntimeError('boom')),
    )
    monkeypatch.setattr(
        sync_job_runtime,
        'finalize_sync',
        lambda *args, **kwargs: pytest.fail('finalize should not run'),
    )
    monkeypatch.setattr(
        sync_job_runtime,
        'post_process_embeddings',
        lambda *args, **kwargs: pytest.fail('post-process should not run'),
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    with Session(engine) as assert_session:
        loaded_job = get_sync_job_by_id(assert_session, job_id)
        visible_table = assert_session.exec(select(CoreTable)).first()
        visible_fields = list(
            assert_session.exec(
                select(CoreField).order_by(col(CoreField.field_index).asc())
            ).all()
        )
        assert loaded_job is not None
        assert loaded_job.status == SyncJobStatus.FAILED
        assert loaded_job.error_summary == '1 of 1 tables failed during sync'
        assert visible_table is not None
        assert visible_table.table_comment == 'old orders'
        assert [field.field_name for field in visible_fields] == ['legacy_id']


def test_visibility_guard_preserves_previous_schema_on_partial_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job_id = _create_job(
            setup_session,
            tables=[
                SelectedTablePayload(table_name='orders', table_comment='new orders'),
                SelectedTablePayload(table_name='payments', table_comment='payments'),
            ],
        )

    session_factory = EngineSessionFactory(engine)

    def probe_with_one_failure(*, introspected_batch: list[IntrospectedTableSchema], **_: object) -> None:
        table_names = {item.table.table_name for item in introspected_batch}
        if 'payments' in table_names:
            raise RuntimeError('payments boom')

    monkeypatch.setattr(sync_job_runtime, 'engine', engine)
    _patch_fake_datasource(monkeypatch)
    _patch_sync_job_context(monkeypatch)
    monkeypatch.setattr(sync_job_runtime, 'introspect_remote_metadata', _fake_introspect)
    monkeypatch.setattr(sync_job_runtime, '_probe_stage_batch', probe_with_one_failure)
    monkeypatch.setattr(
        sync_job_runtime,
        'finalize_sync',
        lambda *args, **kwargs: pytest.fail('finalize should not run'),
    )
    monkeypatch.setattr(
        sync_job_runtime,
        'post_process_embeddings',
        lambda *args, **kwargs: pytest.fail('post-process should not run'),
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    with Session(engine) as assert_session:
        loaded_job = get_sync_job_by_id(assert_session, job_id)
        visible_tables = list(
            assert_session.exec(select(CoreTable).order_by(col(CoreTable.id).asc())).all()
        )
        visible_fields = list(
            assert_session.exec(select(CoreField).order_by(col(CoreField.field_index).asc())).all()
        )
        assert loaded_job is not None
        assert loaded_job.status == SyncJobStatus.PARTIAL
        assert loaded_job.completed_tables == 1
        assert loaded_job.failed_tables == 1
        assert loaded_job.error_summary == '1 of 2 tables failed during sync'
        assert [table.table_name for table in visible_tables] == ['orders']
        assert visible_tables[0].table_comment == 'old orders'
        assert [field.field_name for field in visible_fields] == ['legacy_id']


def test_embedding_dispatch_occurs_only_after_finalize_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job_id = _create_job(
            setup_session,
            tables=[SelectedTablePayload(table_name='orders', table_comment='new orders')],
        )

    session_factory = EngineSessionFactory(engine)
    embedding_calls: list[list[int]] = []

    def finalize_then_fail(session: Session, context: object, *, staged_table_ids: list[int]) -> object:
        _ = session
        _ = context
        _ = staged_table_ids
        assert embedding_calls == []
        raise RuntimeError('finalize boom')

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
        embedding_calls.append(table_ids)
        return PostProcessResult(
            phase=SyncJobPhase.POST_PROCESS,
            dispatched_table_ids=table_ids,
            chunk_count=1,
        )

    monkeypatch.setattr(sync_job_runtime, 'engine', engine)
    _patch_fake_datasource(monkeypatch)
    _patch_sync_job_context(monkeypatch)
    monkeypatch.setattr(sync_job_runtime, 'introspect_remote_metadata', _fake_introspect)
    monkeypatch.setattr(sync_job_runtime, 'finalize_sync', finalize_then_fail)
    monkeypatch.setattr(sync_job_runtime, 'post_process_embeddings', fake_post_process)

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    with Session(engine) as assert_session:
        loaded_job = get_sync_job_by_id(assert_session, job_id)
        visible_table = assert_session.exec(select(CoreTable)).first()
        visible_field = assert_session.exec(select(CoreField)).first()
        assert loaded_job is not None
        assert loaded_job.status == SyncJobStatus.FAILED
        assert loaded_job.error_summary == 'finalize boom'
        assert embedding_calls == []
        assert visible_table is not None
        assert visible_table.table_comment == 'old orders'
        assert visible_field is not None
        assert visible_field.field_comment == 'legacy'


def test_visibility_guard_preserves_previous_schema_on_cancellation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job_id = _create_job(
            setup_session,
            tables=[SelectedTablePayload(table_name='orders', table_comment='new orders')],
        )

    session_factory = EngineSessionFactory(engine)
    should_cancel = False
    cancellation_persisted = False

    def probe_then_request_cancel(**_: object) -> None:
        nonlocal should_cancel
        should_cancel = True

    def fake_job_is_cancelled(status_session: Session, job: DatasourceSyncJob) -> bool:
        nonlocal should_cancel, cancellation_persisted
        if should_cancel and not cancellation_persisted:
            cancellation_persisted = True
            should_cancel = False
            _ = update_sync_job_status(
                status_session,
                job=job,
                status=SyncJobStatus.CANCELLED,
                phase=job.phase,
                error_summary='sync job cancelled by operator',
            )
            return True
        status_session.refresh(job)
        return job.status == SyncJobStatus.CANCELLED

    monkeypatch.setattr(sync_job_runtime, 'engine', engine)
    _patch_fake_datasource(monkeypatch)
    _patch_sync_job_context(monkeypatch)
    monkeypatch.setattr(sync_job_runtime, 'introspect_remote_metadata', _fake_introspect)
    monkeypatch.setattr(sync_job_runtime, '_probe_stage_batch', probe_then_request_cancel)
    monkeypatch.setattr(sync_job_runtime, '_job_is_cancelled', fake_job_is_cancelled)
    monkeypatch.setattr(
        sync_job_runtime,
        'finalize_sync',
        lambda *args, **kwargs: pytest.fail('finalize should not run'),
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    with Session(engine) as assert_session:
        loaded_job = get_sync_job_by_id(assert_session, job_id)
        visible_tables = list(assert_session.exec(select(CoreTable)).all())
        visible_fields = list(assert_session.exec(select(CoreField)).all())
        assert loaded_job is not None
        assert loaded_job.status == SyncJobStatus.CANCELLED
        assert loaded_job.error_summary == 'sync job cancelled by operator'
        assert [table.table_name for table in visible_tables] == ['orders']
        assert visible_tables[0].table_comment == 'old orders'
        assert [field.field_name for field in visible_fields] == ['legacy_id']
