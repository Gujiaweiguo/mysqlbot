import json
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Path
from pydantic import BaseModel
from sqlmodel import col, select

from apps.datasource.models.datasource import CoreDatasource, CoreTable
from apps.datasource.models.permission import DsPermission, DsRules
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import CurrentUser, SessionDep

router = APIRouter(tags=["Permission"], prefix="/ds_permission")


class PermissionItemPayload(BaseModel):
    id: int | None = None
    name: str
    ds_id: int
    table_id: int
    type: str
    permissions: str | None = None
    expression_tree: str | None = None


class PermissionGroupPayload(BaseModel):
    id: int | None = None
    name: str
    permissions: list[PermissionItemPayload]
    users: list[int]


def _parse_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _permission_to_dict(
    session: SessionDep, permission: DsPermission
) -> dict[str, Any]:
    datasource = (
        session.get(CoreDatasource, permission.ds_id) if permission.ds_id else None
    )
    table = session.get(CoreTable, permission.table_id) if permission.table_id else None
    tree: Any = permission.expression_tree
    if permission.expression_tree:
        try:
            tree = json.loads(permission.expression_tree)
        except json.JSONDecodeError:
            tree = permission.expression_tree
    permission_list: Any = permission.permissions
    if permission.permissions:
        try:
            permission_list = json.loads(permission.permissions)
        except json.JSONDecodeError:
            permission_list = permission.permissions
    return {
        "id": permission.id,
        "name": permission.name or "",
        "ds_id": permission.ds_id or 0,
        "table_id": permission.table_id or 0,
        "type": permission.type,
        "ds_name": datasource.name if datasource else "",
        "table_name": table.table_name if table else "",
        "tree": tree,
        "expression_tree": tree,
        "permission_list": permission_list,
        "permissions": permission_list,
    }


def _parse_int_json_list(raw: str | None) -> list[int]:
    return [
        int(item)
        for item in _parse_json_list(raw)
        if isinstance(item, (int, str)) and str(item).isdigit()
    ]


@router.post("/list")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def permission_list(
    session: SessionDep, user: CurrentUser
) -> list[dict[str, Any]]:
    rules = list(
        session.exec(
            select(DsRules)
            .where(col(DsRules.oid) == user.oid)
            .order_by(col(DsRules.id).desc())
        )
    )
    result: list[dict[str, Any]] = []
    for rule in rules:
        permission_ids = _parse_int_json_list(rule.permission_list)
        users = _parse_int_json_list(rule.user_list)
        permissions: list[dict[str, Any]] = []
        for permission_id in permission_ids:
            permission = session.get(DsPermission, permission_id)
            if permission is not None:
                permissions.append(_permission_to_dict(session, permission))
        result.append(
            {
                "id": rule.id,
                "name": rule.name,
                "users": users,
                "permissions": permissions,
            }
        )
    return result


@router.post("/save")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def save_permission_group(
    payload: PermissionGroupPayload, session: SessionDep, user: CurrentUser
) -> bool:
    rule = session.get(DsRules, payload.id) if payload.id else None
    existing_permission_ids: list[int] = []
    if rule is None:
        rule = DsRules(
            enable=True,
            name=payload.name,
            description=None,
            permission_list="[]",
            user_list="[]",
            white_list_user=None,
            create_time=datetime.now(),
            oid=user.oid,
        )
        session.add(rule)
        session.flush()
    else:
        if rule.oid != user.oid:
            raise PermissionError("No permission to modify this permission group")
        existing_permission_ids = _parse_int_json_list(rule.permission_list)
        rule.name = payload.name

    new_permission_ids: list[int] = []
    kept_existing_ids: set[int] = set()
    existing_permission_id_set = set(existing_permission_ids)
    for item in payload.permissions:
        permission = session.get(DsPermission, item.id) if item.id else None
        if permission is None:
            permission = DsPermission(
                enable=True,
                name=item.name,
                auth_target_type=None,
                auth_target_id=None,
                type=item.type,
                ds_id=item.ds_id,
                table_id=item.table_id,
                expression_tree=item.expression_tree,
                permissions=item.permissions,
                white_list_user=None,
                create_time=datetime.now(),
            )
        else:
            if rule is None or permission.id not in existing_permission_id_set:
                raise PermissionError("No permission to modify this permission item")
            permission.enable = True
            permission.name = item.name
            permission.type = item.type
            permission.ds_id = item.ds_id
            permission.table_id = item.table_id
            permission.expression_tree = item.expression_tree
            permission.permissions = item.permissions
            kept_existing_ids.add(cast(int, permission.id))
        session.add(permission)
        session.flush()
        if permission.id is not None:
            new_permission_ids.append(permission.id)

    for stale_id in existing_permission_ids:
        if stale_id not in kept_existing_ids and stale_id not in new_permission_ids:
            stale_permission = session.get(DsPermission, stale_id)
            if stale_permission is not None:
                session.delete(stale_permission)

    rule.permission_list = json.dumps(new_permission_ids)
    rule.user_list = json.dumps(payload.users)
    rule.oid = user.oid
    session.add(rule)
    session.commit()
    return True


@router.post("/delete/{id}")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def delete_permission_group(
    session: SessionDep,
    user: CurrentUser,
    id: int = Path(..., description="permission group id"),
) -> bool:
    rule = session.get(DsRules, id)
    if rule is None:
        return True
    if rule.oid != user.oid:
        raise PermissionError("No permission to delete this permission group")
    permission_ids = _parse_int_json_list(rule.permission_list)
    for permission_id in permission_ids:
        permission = session.get(DsPermission, permission_id)
        if permission is not None:
            session.delete(permission)
    session.delete(rule)
    session.commit()
    return True
