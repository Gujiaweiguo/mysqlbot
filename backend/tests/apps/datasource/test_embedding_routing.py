from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from apps.datasource.crud import table as table_crud
from apps.datasource.embedding import table_embedding as table_embedding_module
from apps.datasource.models.datasource import CoreField, CoreTable


class _FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.query_calls: list[str] = []
        self.document_calls: list[list[str]] = []

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return [1.0, 0.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(texts)
        return [[1.0, 0.0] for _ in texts]


class _FlakyEmbeddingProvider(_FakeEmbeddingProvider):
    def __init__(self) -> None:
        super().__init__()
        self.fail_once = True

    def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("transient embedding error")
        return [1.0, 0.0]


@dataclass
class _FakeQuery:
    first_value: Any = None
    all_value: list[Any] | None = None

    def filter(self, *_args: object, **_kwargs: object) -> "_FakeQuery":
        return self

    def first(self) -> Any:
        return self.first_value

    def all(self) -> list[Any]:
        return self.all_value or []


class _FakeSession:
    def __init__(self) -> None:
        self.table = CoreTable(
            id=1,
            ds_id=1,
            checked=True,
            table_name="orders",
            table_comment="orders table",
            custom_comment="orders table",
            embedding=None,
        )
        self.fields = [
            CoreField(
                id=1,
                ds_id=1,
                table_id=1,
                checked=True,
                field_name="order_amount",
                field_type="numeric",
                field_comment="amount",
                custom_comment="amount",
                field_index=0,
            )
        ]
        self.executed_statements: list[object] = []
        self.commit_count = 0
        self.rollback_count = 0

    def query(self, model: object) -> _FakeQuery:
        if model is CoreTable:
            return _FakeQuery(first_value=self.table)
        if model is CoreField:
            return _FakeQuery(all_value=self.fields)
        return _FakeQuery()

    def execute(self, statement: object) -> None:
        self.executed_statements.append(statement)

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class _FakeBatchSession(_FakeSession):
    def __init__(self) -> None:
        super().__init__()
        self.table = None
        self.tables = {
            1: CoreTable(
                id=1,
                ds_id=1,
                checked=True,
                table_name="orders",
                table_comment="orders table",
                custom_comment="orders table",
                embedding=None,
            ),
            2: CoreTable(
                id=2,
                ds_id=1,
                checked=True,
                table_name="members",
                table_comment="members table",
                custom_comment="members table",
                embedding=None,
            ),
        }
        self.fields_map = {
            1: [
                CoreField(
                    id=1,
                    ds_id=1,
                    table_id=1,
                    checked=True,
                    field_name="order_amount",
                    field_type="numeric",
                    field_comment="amount",
                    custom_comment="amount",
                    field_index=0,
                )
            ],
            2: [
                CoreField(
                    id=2,
                    ds_id=1,
                    table_id=2,
                    checked=True,
                    field_name="nickname",
                    field_type="varchar",
                    field_comment="nickname",
                    custom_comment="nickname",
                    field_index=0,
                )
            ],
        }
        self.current_table_id = 1
        self._table_query_count = 0

    def query(self, model: object) -> _FakeQuery:
        if model is CoreTable:
            self._table_query_count += 1
            self.current_table_id = 1 if self._table_query_count == 1 else 2
            return _FakeQuery(first_value=self.tables[self.current_table_id])
        if model is CoreField:
            return _FakeQuery(all_value=self.fields_map[self.current_table_id])
        return _FakeQuery()

    def execute(self, statement: object) -> None:
        self.executed_statements.append(statement)


class _FakeSessionMaker:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session
        self.removed = False

    def __call__(self) -> _FakeSession:
        return self.session

    def remove(self) -> None:
        self.removed = True


def test_get_table_embedding_uses_provider_interface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeEmbeddingProvider()
    monkeypatch.setattr(
        table_embedding_module, "embedding_runtime_enabled", lambda: True
    )
    monkeypatch.setattr(
        table_embedding_module.EmbeddingModelCache,
        "get_model",
        staticmethod(lambda: provider),
    )

    result = table_embedding_module.get_table_embedding(
        [{"id": 1, "schema_table": "# Table: orders\n[(order_amount:numeric)]"}],
        "show order amount",
    )

    assert len(result) == 1
    assert provider.document_calls == [["# Table: orders\n[(order_amount:numeric)]"]]
    assert provider.query_calls == ["show order amount"]


def test_save_table_embedding_uses_provider_interface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeEmbeddingProvider()
    fake_session = _FakeSession()
    fake_session_maker = _FakeSessionMaker(fake_session)
    monkeypatch.setattr(table_crud.settings, "TABLE_EMBEDDING_ENABLED", True)
    monkeypatch.setattr(table_crud, "embedding_runtime_enabled", lambda: True)
    monkeypatch.setattr(
        table_crud.EmbeddingModelCache,
        "get_model",
        staticmethod(lambda: provider),
    )

    table_crud.save_table_embedding(fake_session_maker, [1])

    assert provider.query_calls == [
        "# Table: orders, orders table\n[\n(order_amount:numeric, amount)\n]\n"
    ]
    assert fake_session.commit_count == 1
    assert fake_session_maker.removed is True


def test_save_table_embedding_continues_after_single_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FlakyEmbeddingProvider()
    fake_session = _FakeBatchSession()
    fake_session_maker = _FakeSessionMaker(fake_session)
    monkeypatch.setattr(table_crud.settings, "TABLE_EMBEDDING_ENABLED", True)
    monkeypatch.setattr(table_crud, "embedding_runtime_enabled", lambda: True)
    monkeypatch.setattr(
        table_crud.EmbeddingModelCache,
        "get_model",
        staticmethod(lambda: provider),
    )

    table_crud.save_table_embedding(fake_session_maker, [1, 2])

    assert fake_session.rollback_count == 1
    assert fake_session.commit_count == 1
    assert provider.query_calls == [
        "# Table: orders, orders table\n[\n(order_amount:numeric, amount)\n]\n",
        "# Table: members, members table\n[\n(nickname:varchar, nickname)\n]\n",
    ]
    assert fake_session_maker.removed is True


def test_truncate_embedding_input_keeps_short_text() -> None:
    text = "# Table: orders\n[\n(order_amount:numeric, amount)\n]\n"

    assert table_crud._truncate_embedding_input(text) == text


def test_truncate_embedding_input_closes_structure() -> None:
    long_field = "x" * 250
    schema_table = "# Table: orders, orders table\n[\n" + ",\n".join(
        f"(field_{index}:varchar, {long_field})" for index in range(20)
    )
    schema_table += "\n]\n"

    truncated = table_crud._truncate_embedding_input(schema_table)

    assert len(truncated) <= table_crud.MAX_EMBEDDING_INPUT_CHARS + 3
    assert truncated.endswith("\n]\n")
    assert truncated != schema_table


def test_save_table_embedding_truncates_long_schema_before_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _FakeEmbeddingProvider()
    fake_session = _FakeSession()
    fake_session.fields = [
        CoreField(
            id=index,
            ds_id=1,
            table_id=1,
            checked=True,
            field_name=f"field_{index}",
            field_type="varchar",
            field_comment="",
            custom_comment="x" * 250,
            field_index=index,
        )
        for index in range(20)
    ]
    fake_session_maker = _FakeSessionMaker(fake_session)
    monkeypatch.setattr(table_crud.settings, "TABLE_EMBEDDING_ENABLED", True)
    monkeypatch.setattr(table_crud, "embedding_runtime_enabled", lambda: True)
    monkeypatch.setattr(
        table_crud.EmbeddingModelCache,
        "get_model",
        staticmethod(lambda: provider),
    )

    table_crud.save_table_embedding(fake_session_maker, [1])

    assert len(provider.query_calls) == 1
    assert len(provider.query_calls[0]) <= table_crud.MAX_EMBEDDING_INPUT_CHARS + 3
    assert provider.query_calls[0].endswith("\n]\n")
