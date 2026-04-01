from __future__ import annotations

from collections.abc import Generator
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel, col, select

from apps.datasource.crud import datasource as datasource_crud
from apps.datasource.models.datasource import (
    ColumnSchema,
    CoreDatasource,
    CoreField,
    CoreTable,
    DatasourceConf,
    SelectedTablePayload,
)
from apps.db.constant import ConnectType
from apps.db.db import DatasourceMetadataContext
from common.core.config import settings


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


@pytest.fixture
def sync_field_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [cast(Any, CoreField).__table__]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


def test_get_fields_by_ds_uses_supplied_metadata_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ds = _build_datasource()
    context = DatasourceMetadataContext(
        ds_type="mysql",
        conf=DatasourceConf(),
        connect_type=ConnectType.sqlalchemy,
    )
    calls: list[tuple[int, str]] = []

    def fake_get_fields_from_context(
        ds_obj: CoreDatasource,
        metadata_context: DatasourceMetadataContext,
        table_name: str | None = None,
    ) -> list[ColumnSchema]:
        assert metadata_context is context
        calls.append((cast(int, ds_obj.id), table_name or ""))
        return [ColumnSchema("id", "bigint", "primary key")]

    monkeypatch.setattr(
        datasource_crud, "get_fields_from_context", fake_get_fields_from_context
    )

    fields = datasource_crud.getFieldsByDs(
        Session(), ds, "orders", metadata_context=context
    )

    assert calls == [(1, "orders")]
    assert [field.fieldName for field in fields] == ["id"]


def test_sync_table_reconciles_then_prunes_then_embeds(
    monkeypatch: pytest.MonkeyPatch,
    test_db: Session,
) -> None:
    ds = _build_datasource()

    calls: list[str] = []

    def fake_build_metadata_context(_ds: CoreDatasource) -> DatasourceMetadataContext:
        calls.append("build_context")
        return DatasourceMetadataContext(
            ds_type="mysql",
            conf=DatasourceConf(),
            connect_type=ConnectType.sqlalchemy,
        )

    def fake_reconcile_single_table(
        session: Session,
        ds: CoreDatasource,
        item: SelectedTablePayload,
        metadata_context: DatasourceMetadataContext,
        *,
        fields: list[ColumnSchema] | None = None,
        auto_commit: bool,
    ) -> CoreTable:
        _ = session
        assert ds.id == 1
        assert metadata_context.ds_type == "mysql"
        assert fields is None
        assert auto_commit is True
        calls.append(f"reconcile:{item.table_name}")
        return CoreTable(
            id=10 if item.table_name == "orders" else 20,
            ds_id=1,
            checked=True,
            table_name=item.table_name,
            table_comment=item.table_comment,
            custom_comment=item.table_comment,
            embedding=None,
        )

    def fake_finalize_sync_table_prune(
        session: Session,
        ds_obj: CoreDatasource,
        id_list: list[int],
        *,
        auto_commit: bool,
    ) -> None:
        _ = session
        assert ds_obj.id == ds.id
        assert auto_commit is True
        calls.append(f"prune:{id_list}")

    def fake_run_sync_table_embeddings(
        ds_obj: CoreDatasource, id_list: list[int]
    ) -> None:
        assert ds_obj.id == ds.id
        calls.append(f"embed:{id_list}")

    monkeypatch.setattr(
        datasource_crud, "build_metadata_context", fake_build_metadata_context
    )
    monkeypatch.setattr(
        datasource_crud, "_reconcile_single_table", fake_reconcile_single_table
    )
    monkeypatch.setattr(
        datasource_crud, "_finalize_sync_table_prune", fake_finalize_sync_table_prune
    )
    monkeypatch.setattr(
        datasource_crud, "_run_sync_table_embeddings", fake_run_sync_table_embeddings
    )

    datasource_crud.sync_table(
        test_db,
        ds,
        [
            SelectedTablePayload(table_name="orders", table_comment="Orders"),
            SelectedTablePayload(table_name="customers", table_comment="Customers"),
        ],
    )

    assert calls == [
        "build_context",
        "reconcile:orders",
        "reconcile:customers",
        "prune:[10, 20]",
        "embed:[10, 20]",
    ]


def test_sync_fields_commits_once_per_table(
    sync_field_tables: None,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = sync_field_tables
    ds = _build_datasource()
    table = CoreTable(
        id=10,
        ds_id=1,
        checked=True,
        table_name="orders",
        table_comment="orders",
        custom_comment="orders",
        embedding=None,
    )
    existing = CoreField(
        id=101,
        ds_id=1,
        table_id=10,
        checked=True,
        field_name="id",
        field_type="bigint",
        field_comment="old",
        custom_comment="old",
        field_index=0,
    )
    amount = CoreField(
        id=102,
        ds_id=1,
        table_id=10,
        checked=True,
        field_name="amount",
        field_type="decimal",
        field_comment="old amount",
        custom_comment="old amount",
        field_index=1,
    )
    stale = CoreField(
        id=103,
        ds_id=1,
        table_id=10,
        checked=True,
        field_name="legacy",
        field_type="varchar",
        field_comment="legacy",
        custom_comment="legacy",
        field_index=2,
    )
    test_db.add(existing)
    test_db.add(amount)
    test_db.add(stale)
    test_db.commit()

    commit_count = 0
    original_commit = test_db.commit

    def counting_commit() -> None:
        nonlocal commit_count
        commit_count += 1
        original_commit()

    monkeypatch.setattr(test_db, "commit", counting_commit)

    datasource_crud.sync_fields(
        test_db,
        ds,
        table,
        [
            ColumnSchema("id", "bigint", "new id"),
            ColumnSchema("amount", "decimal", "amount"),
        ],
    )

    fields = list(
        test_db.exec(
            select(CoreField)
            .where(col(CoreField.table_id) == 10)
            .order_by(col(CoreField.field_index).asc())
        ).all()
    )

    assert commit_count == 1
    assert [field.field_name for field in fields] == ["id", "amount"]
    assert fields[0].field_comment == "new id"
    assert fields[1].field_comment == "amount"


def test_run_sync_table_embeddings_chunks_large_id_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ds = _build_datasource()
    ds.id = 1
    table_calls: list[list[int]] = []
    ds_calls: list[list[int]] = []

    monkeypatch.setattr(settings, "DATASOURCE_SYNC_EMBEDDING_CHUNK_SIZE", 2)
    monkeypatch.setattr(
        datasource_crud,
        "run_save_table_embeddings",
        lambda ids: table_calls.append(ids),
    )
    monkeypatch.setattr(
        datasource_crud, "run_save_ds_embeddings", lambda ids: ds_calls.append(ids)
    )

    datasource_crud._run_sync_table_embeddings(ds, [1, 2, 3, 4, 5])

    assert table_calls == [[1, 2], [3, 4], [5]]
    assert ds_calls == [[1]]
