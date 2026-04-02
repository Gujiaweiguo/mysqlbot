from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, col, create_engine, select

from apps.datasource.crud.datasource import (
    _finalize_sync_table_prune,
    _reconcile_single_table,
)
from apps.datasource.crud.sync_job import create_sync_job, get_sync_job_by_id
from apps.datasource.models.datasource import (
    ColumnSchema,
    CoreDatasource,
    CoreField,
    CoreTable,
    SelectedTablePayload,
)
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobStatus,
    dump_selected_tables_payload,
)
from common.utils import sync_job_runtime


class EngineSessionFactory:
    def __init__(self, db_engine: Engine) -> None:
        self._db_engine = db_engine
        self.remove_calls = 0

    def __call__(self) -> Session:
        return Session(self._db_engine)

    def remove(self) -> None:
        self.remove_calls += 1


def _create_visibility_engine(tmp_path: Path) -> Engine:
    db_path = tmp_path / "sync-job-visibility.db"
    engine = create_engine(f"sqlite:///{db_path}")
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
            table_name="orders",
            table_comment="old orders",
            custom_comment="old orders",
            embedding=None,
        )
    )
    session.add(
        CoreField(
            id=1,
            ds_id=1,
            table_id=1,
            checked=True,
            field_name="legacy_id",
            field_type="bigint",
            field_comment="legacy",
            custom_comment="legacy",
            field_index=0,
        )
    )
    session.commit()


def test_visibility_guard_keeps_previous_schema_visible_until_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job = create_sync_job(
            setup_session, ds_id=1, oid=1, create_by=1, total_tables=1
        )
        job.requested_tables = dump_selected_tables_payload(
            [SelectedTablePayload(table_name="orders", table_comment="new orders")]
        )
        setup_session.add(job)
        setup_session.commit()
        setup_session.refresh(job)
        job_id = cast(int, job.id)

    session_factory = EngineSessionFactory(engine)
    original_session_get = Session.get

    class FakeDatasource:
        id = 1

    def fake_session_get(self: Session, entity: Any, ident: Any) -> Any:
        if entity is CoreDatasource and ident == 1:
            return FakeDatasource()
        return original_session_get(self, entity, ident)

    def fake_build_metadata_context(ds: object) -> object:
        _ = ds
        return object()

    def fake_get_fields_from_context(
        ds: object, context: object, table_name: str | None = None
    ) -> list[ColumnSchema]:
        _ = ds
        _ = context
        _ = table_name
        return [ColumnSchema("legacy_id", "bigint", "new id")]

    def finalize_with_visibility_check(
        session: Session,
        ds: CoreDatasource,
        id_list: list[int],
        *,
        auto_commit: bool,
    ) -> None:
        _finalize_sync_table_prune(session, ds, id_list, auto_commit=auto_commit)
        with Session(engine) as visible_session:
            visible_table = visible_session.exec(select(CoreTable)).first()
            visible_field = visible_session.exec(select(CoreField)).first()
            assert visible_table is not None
            assert visible_table.table_comment == "old orders"
            assert visible_field is not None
            assert visible_field.field_name == "legacy_id"

    monkeypatch.setattr(sync_job_runtime, "engine", engine)
    monkeypatch.setattr(Session, "get", fake_session_get)
    monkeypatch.setattr(
        sync_job_runtime, "build_metadata_context", fake_build_metadata_context
    )
    monkeypatch.setattr(
        sync_job_runtime, "get_fields_from_context", fake_get_fields_from_context
    )
    monkeypatch.setattr(
        sync_job_runtime, "_run_sync_table_embeddings", lambda ds, ids: None
    )
    monkeypatch.setattr(
        "common.utils.sync_job_runtime._finalize_sync_table_prune",
        finalize_with_visibility_check,
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    with Session(engine) as assert_session:
        loaded_job = get_sync_job_by_id(assert_session, job_id)
        visible_table = assert_session.exec(select(CoreTable)).first()
        visible_fields = list(assert_session.exec(select(CoreField)).all())
        assert loaded_job is not None
        assert loaded_job.status == SyncJobStatus.SUCCEEDED
        assert visible_table is not None
        assert visible_table.table_comment == "new orders"
        assert [field.field_name for field in visible_fields] == ["legacy_id"]
        assert visible_fields[0].field_comment == "new id"


def test_visibility_guard_rolls_back_and_preserves_previous_schema_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job = create_sync_job(
            setup_session, ds_id=1, oid=1, create_by=1, total_tables=1
        )
        job.requested_tables = dump_selected_tables_payload(
            [SelectedTablePayload(table_name="orders", table_comment="new orders")]
        )
        setup_session.add(job)
        setup_session.commit()
        setup_session.refresh(job)
        job_id = cast(int, job.id)

    session_factory = EngineSessionFactory(engine)
    original_session_get = Session.get

    class FakeDatasource:
        id = 1

    def fake_session_get(self: Session, entity: Any, ident: Any) -> Any:
        if entity is CoreDatasource and ident == 1:
            return FakeDatasource()
        return original_session_get(self, entity, ident)

    def fake_build_metadata_context(ds: object) -> object:
        _ = ds
        return object()

    def fake_get_fields_from_context(
        ds: object, context: object, table_name: str | None = None
    ) -> list[ColumnSchema]:
        _ = ds
        _ = context
        _ = table_name
        return [ColumnSchema("legacy_id", "bigint", "new id")]

    def reconcile_then_fail(
        session: Session,
        ds: CoreDatasource,
        item: SelectedTablePayload,
        metadata_context: object,
        *,
        fields: list[ColumnSchema] | None = None,
        auto_commit: bool,
    ) -> CoreTable:
        _ = _reconcile_single_table(
            session=session,
            ds=ds,
            item=item,
            metadata_context=cast(Any, metadata_context),
            fields=fields,
            auto_commit=auto_commit,
        )
        raise RuntimeError("boom")

    monkeypatch.setattr(sync_job_runtime, "engine", engine)
    monkeypatch.setattr(Session, "get", fake_session_get)
    monkeypatch.setattr(
        sync_job_runtime, "build_metadata_context", fake_build_metadata_context
    )
    monkeypatch.setattr(
        sync_job_runtime, "get_fields_from_context", fake_get_fields_from_context
    )
    monkeypatch.setattr(
        "common.utils.sync_job_runtime._reconcile_single_table",
        reconcile_then_fail,
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
        assert loaded_job.error_summary == "1 of 1 tables failed during sync"
        assert visible_table is not None
        assert visible_table.table_comment == "old orders"
        assert [field.field_name for field in visible_fields] == ["legacy_id"]


def test_visibility_guard_preserves_previous_schema_on_partial_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job = create_sync_job(
            setup_session, ds_id=1, oid=1, create_by=1, total_tables=2
        )
        job.requested_tables = dump_selected_tables_payload(
            [
                SelectedTablePayload(table_name="orders", table_comment="new orders"),
                SelectedTablePayload(table_name="payments", table_comment="payments"),
            ]
        )
        setup_session.add(job)
        setup_session.commit()
        setup_session.refresh(job)
        job_id = cast(int, job.id)

    session_factory = EngineSessionFactory(engine)
    original_session_get = Session.get
    original_reconcile = _reconcile_single_table

    class FakeDatasource:
        id = 1

    def fake_session_get(self: Session, entity: Any, ident: Any) -> Any:
        if entity is CoreDatasource and ident == 1:
            return FakeDatasource()
        return original_session_get(self, entity, ident)

    def fake_build_metadata_context(ds: object) -> object:
        _ = ds
        return object()

    def fake_get_fields_from_context(
        ds: object, context: object, table_name: str | None = None
    ) -> list[ColumnSchema]:
        _ = ds
        _ = context
        return [ColumnSchema("legacy_id", "bigint", f"{table_name} id")]

    def reconcile_with_one_failure(
        session: Session,
        ds: CoreDatasource,
        item: SelectedTablePayload,
        metadata_context: object,
        *,
        fields: list[ColumnSchema] | None = None,
        auto_commit: bool,
    ) -> CoreTable:
        if item.table_name == "payments":
            raise RuntimeError("payments boom")
        return original_reconcile(
            session=session,
            ds=ds,
            item=item,
            metadata_context=cast(Any, metadata_context),
            fields=fields,
            auto_commit=auto_commit,
        )

    monkeypatch.setattr(sync_job_runtime, "engine", engine)
    monkeypatch.setattr(Session, "get", fake_session_get)
    monkeypatch.setattr(
        sync_job_runtime, "build_metadata_context", fake_build_metadata_context
    )
    monkeypatch.setattr(
        sync_job_runtime, "get_fields_from_context", fake_get_fields_from_context
    )
    monkeypatch.setattr(
        "common.utils.sync_job_runtime._reconcile_single_table",
        reconcile_with_one_failure,
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    with Session(engine) as assert_session:
        loaded_job = get_sync_job_by_id(assert_session, job_id)
        visible_tables = list(
            assert_session.exec(
                select(CoreTable).order_by(col(CoreTable.id).asc())
            ).all()
        )
        visible_fields = list(
            assert_session.exec(
                select(CoreField).order_by(col(CoreField.field_index).asc())
            ).all()
        )
        assert loaded_job is not None
        assert loaded_job.status == SyncJobStatus.PARTIAL
        assert loaded_job.completed_tables == 1
        assert loaded_job.failed_tables == 1
        assert loaded_job.error_summary == "1 of 2 tables failed during sync"
        assert [table.table_name for table in visible_tables] == ["orders"]
        assert visible_tables[0].table_comment == "old orders"
        assert [field.field_name for field in visible_fields] == ["legacy_id"]


def test_visibility_guard_preserves_previous_schema_when_all_introspection_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _create_visibility_engine(tmp_path)
    with Session(engine) as setup_session:
        _seed_existing_schema(setup_session)
        job = create_sync_job(
            setup_session, ds_id=1, oid=1, create_by=1, total_tables=1
        )
        job.requested_tables = dump_selected_tables_payload(
            [SelectedTablePayload(table_name="orders", table_comment="new orders")]
        )
        setup_session.add(job)
        setup_session.commit()
        setup_session.refresh(job)
        job_id = cast(int, job.id)

    session_factory = EngineSessionFactory(engine)
    original_session_get = Session.get

    class FakeDatasource:
        id = 1

    def fake_session_get(self: Session, entity: Any, ident: Any) -> Any:
        if entity is CoreDatasource and ident == 1:
            return FakeDatasource()
        return original_session_get(self, entity, ident)

    def fake_build_metadata_context(ds: object) -> object:
        _ = ds
        return object()

    def fail_get_fields_from_context(
        ds: object, context: object, table_name: str | None = None
    ) -> list[ColumnSchema]:
        _ = ds
        _ = context
        raise RuntimeError(f"introspect failed for {table_name}")

    monkeypatch.setattr(sync_job_runtime, "engine", engine)
    monkeypatch.setattr(Session, "get", fake_session_get)
    monkeypatch.setattr(
        sync_job_runtime, "build_metadata_context", fake_build_metadata_context
    )
    monkeypatch.setattr(
        sync_job_runtime, "get_fields_from_context", fail_get_fields_from_context
    )

    sync_job_runtime.run_sync_job_with_session_factory(session_factory, job_id)

    with Session(engine) as assert_session:
        loaded_job = get_sync_job_by_id(assert_session, job_id)
        visible_tables = list(assert_session.exec(select(CoreTable)).all())
        visible_fields = list(assert_session.exec(select(CoreField)).all())
        assert loaded_job is not None
        assert loaded_job.status == SyncJobStatus.FAILED
        assert loaded_job.failed_tables == 1
        assert loaded_job.completed_tables == 0
        assert loaded_job.error_summary == "1 of 1 tables failed during sync"
        assert [table.table_name for table in visible_tables] == ["orders"]
        assert [field.field_name for field in visible_fields] == ["legacy_id"]
