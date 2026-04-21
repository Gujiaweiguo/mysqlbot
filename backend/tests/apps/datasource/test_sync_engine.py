from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnannotatedClassAttribute=false

from datetime import datetime
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel, col, select

from apps.datasource.constants.sync import SYNC_BATCH_SIZE, SYNC_FIELD_BATCH_SIZE
from apps.datasource.models.datasource import (
    ColumnSchema,
    CoreDatasource,
    CoreField,
    CoreTable,
    DatasourceConf,
    SelectedTablePayload,
)
from apps.datasource.models.sync_job import DatasourceSyncJob, SyncJobPhase, SyncJobStatus
from apps.datasource.services.sync_engine import (
    IntrospectedTableSchema,
    SyncJobContext,
    finalize_sync,
    introspect_remote_metadata,
    post_process_embeddings,
    snapshot_requested_tables,
    stage_table_batch,
)
from apps.db.constant import ConnectType
from apps.db.db import DatasourceMetadataContext


def _build_datasource() -> CoreDatasource:
    return CoreDatasource(
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


def _build_job() -> DatasourceSyncJob:
    return DatasourceSyncJob(
        id=1,
        ds_id=1,
        oid=1,
        create_by=1,
        status=SyncJobStatus.PENDING,
        phase=SyncJobPhase.SUBMIT,
        total_tables=0,
        completed_tables=0,
        failed_tables=0,
        skipped_tables=0,
        total_fields=0,
        completed_fields=0,
        current_table_name=None,
        requested_tables="[]",
        embedding_followup_status=None,
        error_summary=None,
        create_time=datetime.now(),
        update_time=datetime.now(),
        start_time=None,
        finish_time=None,
    )


@pytest.fixture
def sync_engine_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [
        cast(Any, CoreTable).__table__,
        cast(Any, CoreField).__table__,
        cast(Any, DatasourceSyncJob).__table__,
    ]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


def _persist_context(test_db: Session) -> SyncJobContext:
    ds = _build_datasource()
    job = _build_job()
    test_db.add(job)
    test_db.commit()
    metadata_context = DatasourceMetadataContext(
        ds_type="mysql",
        conf=DatasourceConf(),
        connect_type=ConnectType.sqlalchemy,
    )
    return SyncJobContext.from_job(
        ds=ds,
        job=job,
        requested_tables=[],
        metadata_context=metadata_context,
    )


def test_snapshot_requested_tables_persists_request_payload(
    sync_engine_tables: None,
    test_db: Session,
) -> None:
    _ = sync_engine_tables
    context = _persist_context(test_db)
    context.requested_tables = [
        SelectedTablePayload(table_name="orders", table_comment="Orders"),
        SelectedTablePayload(table_name="customers", table_comment="Customers"),
    ]

    result = snapshot_requested_tables(test_db, context)

    loaded_job = test_db.get(DatasourceSyncJob, 1)
    assert loaded_job is not None
    assert result.phase == SyncJobPhase.SUBMIT
    assert result.requested_table_count == 2
    assert loaded_job.phase == SyncJobPhase.SUBMIT
    assert '"table_name": "orders"' in loaded_job.requested_tables


def test_introspect_remote_metadata_reuses_single_remote_session() -> None:
    ds = _build_datasource()
    session_open_count = 0
    execute_calls: list[str] = []

    class FakeResult:
        def __init__(self, rows: list[tuple[str, str, str]]) -> None:
            self._rows = rows

        def __enter__(self) -> "FakeResult":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            _ = exc_type
            _ = exc
            _ = tb

        def fetchall(self) -> list[tuple[str, str, str]]:
            return self._rows

    class FakeRemoteSession:
        def execute(self, statement: Any, params: dict[str, object]) -> FakeResult:
            _ = statement
            table_name = cast(str, params["param2"])
            execute_calls.append(table_name)
            return FakeResult([(f"{table_name}_id", "bigint", "pk")])

    @contextmanager
    def fake_session_factory() -> Generator[FakeRemoteSession, None, None]:
        nonlocal session_open_count
        session_open_count += 1
        yield FakeRemoteSession()

    context = SyncJobContext.from_job(
        ds=ds,
        job=_build_job(),
        requested_tables=[
            SelectedTablePayload(table_name="orders", table_comment="Orders"),
            SelectedTablePayload(table_name="customers", table_comment="Customers"),
        ],
        metadata_context=DatasourceMetadataContext(
            ds_type="mysql",
            conf=DatasourceConf(),
            connect_type=ConnectType.sqlalchemy,
            session_factory=cast(Any, fake_session_factory),
        ),
    )

    result = introspect_remote_metadata(context)

    assert session_open_count == 1
    assert execute_calls == ["orders", "customers"]
    assert [item.table.table_name for item in result] == ["orders", "customers"]
    assert [item.fields[0].fieldName for item in result] == ["orders_id", "customers_id"]


def test_stage_table_batch_commits_once_per_table_batch(
    sync_engine_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_engine_tables
    context = _persist_context(test_db)
    commit_count = 0
    original_commit = test_db.commit

    def counting_commit() -> None:
        nonlocal commit_count
        commit_count += 1
        original_commit()

    monkeypatch.setattr(test_db, "commit", counting_commit)

    result = stage_table_batch(
        test_db,
        context,
        introspected_tables=[
            IntrospectedTableSchema(
                table=SelectedTablePayload(table_name="orders", table_comment="Orders"),
                fields=[
                    ColumnSchema("id", "bigint", "pk"),
                    ColumnSchema("amount", "decimal", "Amount"),
                ],
            ),
            IntrospectedTableSchema(
                table=SelectedTablePayload(table_name="customers", table_comment="Customers"),
                fields=[ColumnSchema("id", "bigint", "pk")],
            ),
            IntrospectedTableSchema(
                table=SelectedTablePayload(table_name="invoices", table_comment="Invoices"),
                fields=[ColumnSchema("id", "bigint", "pk")],
            ),
        ],
        batch_size=2,
        field_batch_size=2,
    )

    tables = list(test_db.exec(select(CoreTable).order_by(col(CoreTable.table_name))).all())
    assert commit_count == 2
    assert result.commit_count == 2
    assert result.completed_tables == 3
    assert result.completed_fields == 4
    assert [table.table_name for table in tables] == ["customers", "invoices", "orders"]


def test_finalize_and_post_process_expose_phase_boundaries(
    sync_engine_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_engine_tables
    context = _persist_context(test_db)
    keep_table = CoreTable(
        id=10,
        ds_id=1,
        checked=True,
        table_name="orders",
        table_comment="Orders",
        custom_comment="Orders",
        embedding=None,
    )
    stale_table = CoreTable(
        id=20,
        ds_id=1,
        checked=True,
        table_name="legacy",
        table_comment="Legacy",
        custom_comment="Legacy",
        embedding=None,
    )
    keep_field = CoreField(
        id=100,
        ds_id=1,
        table_id=10,
        checked=True,
        field_name="id",
        field_type="bigint",
        field_comment="pk",
        custom_comment="pk",
        field_index=0,
    )
    stale_field = CoreField(
        id=200,
        ds_id=1,
        table_id=20,
        checked=True,
        field_name="legacy_id",
        field_type="bigint",
        field_comment="pk",
        custom_comment="pk",
        field_index=0,
    )
    test_db.add(keep_table)
    test_db.add(stale_table)
    test_db.add(keep_field)
    test_db.add(stale_field)
    test_db.commit()

    table_embedding_calls: list[list[int]] = []
    ds_embedding_calls: list[list[int]] = []
    monkeypatch.setattr(
        "apps.datasource.services.sync_engine.run_save_table_embeddings",
        lambda ids: table_embedding_calls.append(ids),
    )
    monkeypatch.setattr(
        "apps.datasource.services.sync_engine.run_save_ds_embeddings",
        lambda ids: ds_embedding_calls.append(ids),
    )

    phase = finalize_sync(test_db, context, staged_table_ids=[10])
    post_result = post_process_embeddings(test_db, context, table_ids=[10, 11], chunk_size=1)

    remaining_tables = list(test_db.exec(select(CoreTable).order_by(col(CoreTable.id))).all())
    remaining_fields = list(test_db.exec(select(CoreField).order_by(col(CoreField.id))).all())
    loaded_job = test_db.get(DatasourceSyncJob, 1)

    assert phase == SyncJobPhase.FINALIZE
    assert loaded_job is not None
    assert loaded_job.phase == SyncJobPhase.POST_PROCESS
    assert loaded_job.embedding_followup_status == "dispatched"
    assert [table.id for table in remaining_tables] == [10]
    assert [field.id for field in remaining_fields] == [100]
    assert table_embedding_calls == [[10], [11]]
    assert ds_embedding_calls == [[1]]
    assert post_result.phase == SyncJobPhase.POST_PROCESS
    assert post_result.chunk_count == 2


def test_sync_batch_constants_locked() -> None:
    assert SYNC_BATCH_SIZE == 50
    assert SYNC_FIELD_BATCH_SIZE == 200
