from __future__ import annotations

import json
from collections.abc import Generator
from datetime import datetime
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel

from apps.datasource.models.permission import DsPermission, DsRules


@pytest.fixture
def permission_api_tables(test_db: Session) -> Generator[None, None, None]:
    tables = [cast(Any, DsPermission).__table__, cast(Any, DsRules).__table__]
    bind = test_db.get_bind()
    SQLModel.metadata.drop_all(bind, tables=tables)
    SQLModel.metadata.create_all(bind, tables=tables)
    yield
    SQLModel.metadata.drop_all(bind, tables=tables)


def test_save_permission_group_rejects_cross_workspace_rule_update(
    permission_api_tables: None,
    test_app: Any,
    test_db: Session,
    auth_headers: dict[str, str],
) -> None:
    _ = permission_api_tables
    rule = DsRules(
        enable=True,
        name="foreign-rule",
        description=None,
        permission_list="[]",
        user_list="[]",
        white_list_user=None,
        create_time=datetime.now(),
        oid=999,
    )
    test_db.add(rule)
    test_db.commit()
    test_db.refresh(rule)

    response = test_app.post(
        "/api/v1/ds_permission/save",
        headers=auth_headers,
        json={"id": rule.id, "name": "updated", "permissions": [], "users": []},
    )

    assert response.status_code == 500
    assert "No permission to modify this permission group" in response.text


def test_delete_permission_group_rejects_cross_workspace_rule_delete(
    permission_api_tables: None,
    test_app: Any,
    test_db: Session,
    auth_headers: dict[str, str],
) -> None:
    _ = permission_api_tables
    permission = DsPermission(
        id=101,
        enable=True,
        name="foreign-permission",
        auth_target_type=None,
        auth_target_id=None,
        type="row",
        ds_id=1,
        table_id=1,
        expression_tree=json.dumps({}),
        permissions=json.dumps([]),
        white_list_user=None,
        create_time=datetime.now(),
    )
    test_db.add(permission)
    test_db.commit()
    test_db.refresh(permission)
    rule = DsRules(
        enable=True,
        name="foreign-rule",
        description=None,
        permission_list=json.dumps([permission.id]),
        user_list="[]",
        white_list_user=None,
        create_time=datetime.now(),
        oid=999,
    )
    test_db.add(rule)
    test_db.commit()
    test_db.refresh(rule)

    response = test_app.post(
        f"/api/v1/ds_permission/delete/{rule.id}",
        headers=auth_headers,
    )

    assert response.status_code == 500
    assert "No permission to delete this permission group" in response.text
