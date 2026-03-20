import json
from typing import ClassVar, Protocol, cast

from sqlalchemy import and_
from sqlmodel import col, select

from apps.datasource.crud.row_permission import transFilterTree
from apps.datasource.crud.permission_provider import (
    get_ds_permission_model,
    get_ds_rules_model,
    trans_record_to_dto,
)
from apps.datasource.models.datasource import CoreDatasource, CoreField, CoreTable
from common.core.deps import CurrentUser, SessionDep


class DsPermissionModelProtocol(Protocol):
    table_id: ClassVar[object]
    type: ClassVar[object]


class DsPermissionRecordProtocol(Protocol):
    id: int
    permissions: str


class DsRulesRecordProtocol(Protocol):
    permission_list: str
    user_list: str


def _parse_json_list(raw_json: str) -> list[object]:
    parsed = cast(object, json.loads(raw_json))
    return cast(list[object], parsed) if isinstance(parsed, list) else []


def _parse_json_object_list(raw_json: str) -> list[dict[str, object]]:
    return [
        cast(dict[str, object], item)
        for item in _parse_json_list(raw_json)
        if isinstance(item, dict)
    ]


def get_row_permission_filters(
    session: SessionDep,
    current_user: CurrentUser,
    ds: CoreDatasource,
    tables: list[str] | None = None,
    single_table: CoreTable | None = None,
) -> list[dict[str, str]]:
    ds_rules_model = cast(type[object], get_ds_rules_model())
    ds_permission_model = cast(
        type[DsPermissionModelProtocol], get_ds_permission_model()
    )
    if single_table:
        current = session.get(CoreTable, single_table.id)
        table_list = [current] if current is not None else []
    else:
        if not tables:
            return []
        table_list = list(
            session.exec(
                select(CoreTable).where(
                    and_(
                        col(CoreTable.ds_id) == ds.id,
                        col(CoreTable.table_name).in_(tables),
                    )
                )
            )
        )

    filters: list[dict[str, str]] = []
    if is_normal_user(current_user):
        contain_rules = cast(
            list[DsRulesRecordProtocol],
            list(session.exec(select(ds_rules_model)).all()),
        )
        for table in table_list:
            row_permissions = cast(
                list[DsPermissionRecordProtocol],
                list(
                    session.exec(
                        select(ds_permission_model).where(
                            and_(
                                col(ds_permission_model.table_id) == table.id,
                                col(ds_permission_model.type) == "row",
                            )
                        )
                    )
                ),
            )
            res: list[object] = []
            for permission in row_permissions:
                flag = False
                for rule in contain_rules:
                    p_list = _parse_json_list(rule.permission_list)
                    u_list = _parse_json_list(rule.user_list)
                    if permission.id in p_list and (
                        current_user.id in u_list or f"{current_user.id}" in u_list
                    ):
                        flag = True
                        break
                if flag:
                    res.append(trans_record_to_dto(session, cast(object, permission)))
            where_str = transFilterTree(session, current_user, res, ds)
            if where_str:
                filters.append({"table": table.table_name, "filter": str(where_str)})
    return filters


def get_column_permission_fields(
    session: SessionDep,
    current_user: CurrentUser,
    table: CoreTable,
    fields: list[CoreField],
    contain_rules: list[DsRulesRecordProtocol],
) -> list[CoreField]:
    ds_permission_model = cast(
        type[DsPermissionModelProtocol], get_ds_permission_model()
    )
    if is_normal_user(current_user):
        column_permissions = cast(
            list[DsPermissionRecordProtocol],
            list(
                session.exec(
                    select(ds_permission_model).where(
                        and_(
                            col(ds_permission_model.table_id) == table.id,
                            col(ds_permission_model.type) == "column",
                        )
                    )
                )
            ),
        )
        for permission in column_permissions:
            flag = False
            for rule in contain_rules:
                p_list = _parse_json_list(rule.permission_list)
                u_list = _parse_json_list(rule.user_list)
                if permission.id in p_list and (
                    current_user.id in u_list or f"{current_user.id}" in u_list
                ):
                    flag = True
                    break
            if flag:
                permission_list = _parse_json_object_list(permission.permissions)
                fields = filter_list(fields, permission_list)
    return fields


def is_normal_user(current_user: CurrentUser) -> bool:
    return current_user.id != 1


def filter_list(
    list_a: list[CoreField],
    list_b: list[dict[str, object]],
) -> list[CoreField]:
    id_to_invalid: dict[int, bool] = {}
    for b in list_b:
        field_id = b.get("field_id")
        if b.get("enable") is False and isinstance(field_id, int):
            id_to_invalid[field_id] = True

    return [a for a in list_a if not id_to_invalid.get(a.id, False)]
