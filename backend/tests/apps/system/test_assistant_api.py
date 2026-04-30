from __future__ import annotations

import json
from typing import cast

import pytest
from sqlmodel import Session

from apps.datasource.models.datasource import CoreDatasource
from apps.system.api.assistant import _normalize_and_validate_configuration
from apps.system.crud.assistant import get_assistant_ds
from apps.system.models.system_model import WorkspaceModel
from apps.system.schemas.system_schema import AssistantHeader, UserInfoDTO


class FakeExecResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def all(self) -> list[object]:
        return list(self._items)


class FakeSession:
    def __init__(
        self,
        workspaces: dict[int, WorkspaceModel] | None = None,
        datasources: dict[int, CoreDatasource] | None = None,
    ) -> None:
        self.workspaces = workspaces or {}
        self.datasources = datasources or {}

    def get(self, model: type[object], key: int) -> object | None:
        if model is WorkspaceModel:
            return self.workspaces.get(key)
        if model is CoreDatasource:
            return self.datasources.get(key)
        return None

    def exec(self, statement: object) -> FakeExecResult:
        _ = statement
        return FakeExecResult(list(self.datasources.values()))


class FakeLLMService:
    def __init__(self, assistant: AssistantHeader) -> None:
        self.current_assistant = assistant
        self.out_ds_instance = None


def _build_workspace(workspace_id: int, name: str) -> WorkspaceModel:
    return WorkspaceModel(id=workspace_id, name=name, create_time=1)


def _build_datasource(ds_id: int, oid: int, name: str) -> CoreDatasource:
    return CoreDatasource(
        id=ds_id,
        name=name,
        description='demo',
        type='pg',
        type_name='PostgreSQL',
        configuration='{}',
        create_by=1,
        status='Success',
        num='0/0',
        oid=oid,
        table_relation=[],
        embedding=None,
        recommended_config=1,
    )


@pytest.fixture
def admin_user() -> UserInfoDTO:
    return UserInfoDTO(
        id=1,
        account='admin',
        oid=1,
        name='Admin',
        email='admin@example.com',
        status=1,
        origin=0,
        oid_list=[1, 2],
        system_variables=[],
        language='en',
        weight=1,
        isAdmin=True,
    )


def test_normalize_configuration_persists_multi_workspace_selection(
    admin_user: UserInfoDTO,
) -> None:
    session = FakeSession(
        workspaces={1: _build_workspace(1, 'Default'), 2: _build_workspace(2, 'Sales')},
        datasources={
            11: _build_datasource(11, 1, 'Orders'),
            22: _build_datasource(22, 2, 'CRM'),
        },
    )

    normalized = _normalize_and_validate_configuration(
        session=cast(Session, cast(object, session)),
        current_user=admin_user,
        assistant_type=0,
        configuration=json.dumps({'workspace_ids': [1, 2], 'datasource_ids': [11, 22]}),
    )

    assert normalized is not None
    config = json.loads(normalized)
    assert config['workspace_ids'] == [1, 2]
    assert config['datasource_ids'] == [11, 22]
    assert config['oid'] == 1
    assert config['public_list'] == [11, 22]


def test_normalize_configuration_rejects_datasource_outside_workspace_scope(
    admin_user: UserInfoDTO,
) -> None:
    session = FakeSession(
        workspaces={1: _build_workspace(1, 'Default'), 2: _build_workspace(2, 'Sales')},
        datasources={22: _build_datasource(22, 2, 'CRM')},
    )

    with pytest.raises(Exception, match='outside the selected workspace scope'):
        _normalize_and_validate_configuration(
            session=cast(Session, cast(object, session)),
            current_user=admin_user,
            assistant_type=0,
            configuration=json.dumps({'workspace_ids': [1], 'datasource_ids': [22]}),
        )


def test_get_assistant_ds_prefers_workspace_ids_and_datasource_ids() -> None:
    datasources = {
        11: _build_datasource(11, 1, 'Orders'),
        22: _build_datasource(22, 2, 'CRM'),
    }
    session = FakeSession(datasources=datasources)
    assistant = AssistantHeader(
        id=10,
        name='Assistant',
        domain='http://example.com',
        type=0,
        description='demo',
        oid=1,
        configuration=json.dumps(
            {'workspace_ids': [1, 2], 'datasource_ids': [11, 22], 'public_list': [33]}
        ),
        online=False,
    )

    ds_list = get_assistant_ds(
        session=cast(Session, cast(object, session)),
        llm_service=FakeLLMService(assistant),
    )

    assert [item['id'] for item in ds_list] == [11, 22]
