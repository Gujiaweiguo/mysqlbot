from typing import cast

from sqlmodel import Session

from apps.datasource.crud.datasource import chooseTables, update_ds
from apps.datasource.models.datasource import (
    CoreDatasource,
    CoreTable,
    SelectedTablePayload,
    UpdateDatasource,
)
from apps.system.schemas.system_schema import UserInfoDTO
from common.core.deps import Trans


class FakeExecResult:
    def __init__(
        self, first_value: object = None, iterable: list[object] | None = None
    ) -> None:
        self._first_value = first_value
        self._iterable = iterable or []

    def first(self) -> object:
        return self._first_value

    def __iter__(self):
        return iter(self._iterable)


class FakeDatasourceSession:
    def __init__(self, exec_results: list[FakeExecResult]) -> None:
        self._exec_results = exec_results
        self.added_objects: list[object] = []
        self._next_id = 100

    def exec(self, statement: object) -> FakeExecResult:
        _ = statement
        if self._exec_results:
            return self._exec_results.pop(0)
        return FakeExecResult()

    def add(self, obj: object) -> None:
        assert hasattr(obj, "_sa_instance_state")
        if getattr(obj, "id", None) is None:
            setattr(obj, "id", self._next_id)
            self._next_id += 1
        self.added_objects.append(obj)

    def flush(self) -> None:
        return None

    def refresh(self, obj: object) -> None:
        _ = obj
        return None

    def commit(self) -> None:
        return None


def _fake_trans(key: str) -> str:
    return key


class TestDatasourceCrud:
    def test_choose_tables_accepts_payload_models(
        self, monkeypatch, auth_user: UserInfoDTO
    ) -> None:
        _ = auth_user
        ds = CoreDatasource(
            id=1,
            name="mallcre",
            description="",
            type="pg",
            type_name="PostgreSQL",
            configuration="{}",
            create_by=1,
            status="Success",
            num="0/0",
            oid=1,
            table_relation=[],
            recommended_config=1,
        )
        session = FakeDatasourceSession(
            [
                FakeExecResult(first_value=ds),
                FakeExecResult(first_value=None),
                FakeExecResult(),
                FakeExecResult(),
            ]
        )

        monkeypatch.setattr(
            "apps.datasource.crud.datasource.check_status",
            lambda session, trans, ds, checked=False: True,
        )
        monkeypatch.setattr(
            "apps.datasource.crud.datasource.getFieldsByDs",
            lambda session, ds, table_name: [],
        )
        monkeypatch.setattr(
            "apps.datasource.crud.datasource.run_save_table_embeddings",
            lambda ids: None,
        )
        monkeypatch.setattr(
            "apps.datasource.crud.datasource.run_save_ds_embeddings",
            lambda ids: None,
        )
        monkeypatch.setattr(
            "apps.datasource.crud.datasource.updateNum",
            lambda session, ds: None,
        )

        chooseTables(
            cast(Session, cast(object, session)),
            cast(Trans, cast(object, _fake_trans)),
            1,
            [SelectedTablePayload(table_name="demo_table", table_comment="Demo table")],
        )

        saved_tables = [
            obj for obj in session.added_objects if isinstance(obj, CoreTable)
        ]
        assert len(saved_tables) == 1
        assert saved_tables[0].table_name == "demo_table"

    def test_update_ds_accepts_request_dto(
        self, monkeypatch, auth_user: UserInfoDTO
    ) -> None:
        ds = CoreDatasource(
            id=1,
            name="old-name",
            description="old",
            type="pg",
            type_name="PostgreSQL",
            configuration="{}",
            create_by=1,
            status="Success",
            num="0/0",
            oid=1,
            table_relation=[],
            recommended_config=1,
        )
        session = FakeDatasourceSession(
            [
                FakeExecResult(iterable=[]),
                FakeExecResult(first_value=ds),
            ]
        )
        monkeypatch.setattr(
            "apps.datasource.crud.datasource.run_save_ds_embeddings",
            lambda ids: None,
        )

        updated = update_ds(
            cast(Session, cast(object, session)),
            cast(Trans, cast(object, _fake_trans)),
            auth_user,
            UpdateDatasource(
                id=1,
                name="new-name",
                description="new",
                type="pg",
                type_name="PostgreSQL",
                configuration="{}",
                create_by=1,
                status="Success",
                num="0/0",
                oid=1,
                table_relation=[],
                recommended_config=1,
            ),
        )

        assert updated.name == "new-name"
        assert ds.name == "new-name"
