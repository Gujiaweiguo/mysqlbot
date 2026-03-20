from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any, cast

import pytest
from sqlmodel import SQLModel

from apps.datasource.crud.permission import (
    DsRulesRecordProtocol,
    get_column_permission_fields,
    get_row_permission_filters,
)
from apps.datasource.models.datasource import CoreDatasource, CoreField, CoreTable
from apps.datasource.models.permission import DsPermission, DsRules
from apps.system.schemas.system_schema import UserInfoDTO


@pytest.fixture
def datasource_permission_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [
        cast(Any, CoreTable).__table__,
        cast(Any, CoreField).__table__,
        cast(Any, DsPermission).__table__,
        cast(Any, DsRules).__table__,
    ]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


@pytest.fixture
def normal_user(auth_user: UserInfoDTO) -> UserInfoDTO:
    return auth_user.model_copy(update={"id": 2, "isAdmin": False})


def test_get_column_permission_fields_filters_disabled_columns(
    datasource_permission_tables: None,
    test_db: Any,
    normal_user: UserInfoDTO,
) -> None:
    datasource = CoreDatasource(
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
    table = CoreTable(
        id=10,
        ds_id=1,
        checked=True,
        table_name="orders",
        table_comment="orders",
        custom_comment="orders",
        embedding=None,
    )
    field_id = CoreField(
        id=101,
        ds_id=1,
        table_id=10,
        checked=True,
        field_name="id",
        field_type="bigint",
        field_comment="id",
        custom_comment="id",
        field_index=1,
    )
    field_region = CoreField(
        id=102,
        ds_id=1,
        table_id=10,
        checked=True,
        field_name="region",
        field_type="varchar",
        field_comment="region",
        custom_comment="region",
        field_index=2,
    )
    permission = DsPermission(
        id=201,
        enable=True,
        name="hide region",
        auth_target_type=None,
        auth_target_id=None,
        type="column",
        ds_id=1,
        table_id=10,
        expression_tree=None,
        permissions=json.dumps([{"field_id": 102, "enable": False}]),
        white_list_user=None,
        create_time=None,
    )
    rule = DsRules(
        id=301,
        enable=True,
        name="rule",
        description=None,
        permission_list="[201]",
        user_list="[2]",
        white_list_user=None,
        create_time=None,
        oid=1,
    )

    test_db.add(table)
    test_db.add(field_id)
    test_db.add(field_region)
    test_db.add(permission)
    test_db.add(rule)
    test_db.commit()

    fields = get_column_permission_fields(
        session=test_db,
        current_user=normal_user,
        table=table,
        fields=[field_id, field_region],
        contain_rules=cast(list[DsRulesRecordProtocol], [rule]),
    )

    assert [field.field_name for field in fields] == ["id"]


def test_get_row_permission_filters_returns_local_where_clause(
    datasource_permission_tables: None,
    test_db: Any,
    normal_user: UserInfoDTO,
) -> None:
    datasource = CoreDatasource(
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
    table = CoreTable(
        id=10,
        ds_id=1,
        checked=True,
        table_name="orders",
        table_comment="orders",
        custom_comment="orders",
        embedding=None,
    )
    field_region = CoreField(
        id=102,
        ds_id=1,
        table_id=10,
        checked=True,
        field_name="region",
        field_type="varchar",
        field_comment="region",
        custom_comment="region",
        field_index=1,
    )
    permission = DsPermission(
        id=202,
        enable=True,
        name="sales only",
        auth_target_type=None,
        auth_target_id=None,
        type="row",
        ds_id=1,
        table_id=10,
        expression_tree=json.dumps(
            {
                "logic": "AND",
                "items": [
                    {
                        "type": "item",
                        "field_id": 102,
                        "filter_type": "normal",
                        "term": "eq",
                        "value": "sales",
                    }
                ],
            }
        ),
        permissions=None,
        white_list_user=None,
        create_time=None,
    )
    rule = DsRules(
        id=302,
        enable=True,
        name="rule",
        description=None,
        permission_list="[202]",
        user_list="[2]",
        white_list_user=None,
        create_time=None,
        oid=1,
    )

    test_db.add(table)
    test_db.add(field_region)
    test_db.add(permission)
    test_db.add(rule)
    test_db.commit()

    filters = get_row_permission_filters(
        session=test_db,
        current_user=normal_user,
        ds=datasource,
        tables=["orders"],
    )

    assert filters == [{"table": "orders", "filter": "(`region` = 'sales')"}]
