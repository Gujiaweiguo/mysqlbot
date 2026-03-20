import json
from typing import Any, cast

from fastapi import APIRouter, Path
from pydantic import BaseModel
from sqlmodel import col, select

from apps.system.api.authentication import (
    _get_auth_model,
    _parse_config,
)
from apps.system.models.system_model import UserWsModel
from apps.system.models.user import UserModel, UserPlatformModel
from common.core.deps import CurrentUser, SessionDep
from common.core.security import default_md5_pwd

PLATFORM_TYPES = [6, 7, 8, 9]


class PlatformCardSchema(BaseModel):
    id: int | None = None
    type: int
    name: str
    config: str
    enable: bool = False
    valid: bool = False


class PlatformOrgNode(BaseModel):
    id: str
    name: str
    children: list["PlatformOrgNode"] = []
    options: dict[str, Any] = {}


class PlatformSyncPayload(BaseModel):
    user_list: list[dict[str, Any]]
    origin: int
    cover: bool = False


class PlatformSyncResult(BaseModel):
    successCount: int
    errorCount: int
    dataKey: str = ""


router = APIRouter(tags=["system/platform"], prefix="/system/platform")


def _platform_name(type_id: int) -> str:
    mapping = {
        6: "wecom",
        7: "dingtalk",
        8: "lark",
        9: "larksuite",
    }
    return mapping[type_id]


def _parameter_defaults(session: SessionDep) -> dict[str, str]:
    from apps.system.models.sys_arg_model import SysArgModel

    rows = session.exec(
        select(SysArgModel).where(
            col(SysArgModel.pkey).in_(
                ["platform.auto_create", "platform.oid", "platform.rid"]
            )
        )
    ).all()
    return {row.pkey: row.pval or "" for row in rows}


@router.get("")
async def list_platforms(session: SessionDep) -> list[PlatformCardSchema]:
    result: list[PlatformCardSchema] = []
    for type_id in PLATFORM_TYPES:
        db_model = _get_auth_model(session, type_id)
        if db_model is None:
            result.append(
                PlatformCardSchema(
                    id=None,
                    type=type_id,
                    name=_platform_name(type_id),
                    config="{}",
                    enable=False,
                    valid=False,
                )
            )
            continue
        result.append(
            PlatformCardSchema(
                id=type_id,
                type=type_id,
                name=db_model.name,
                config=db_model.config or "{}",
                enable=bool(db_model.enable and db_model.valid),
                valid=bool(db_model.valid),
            )
        )
    return result


@router.get("/client/{origin}")
async def get_platform_client(
    session: SessionDep,
    origin: int = Path(..., description="platform origin"),
) -> dict[str, Any]:
    db_model = _get_auth_model(session, origin)
    if db_model is None:
        return {}
    return _parse_config(db_model.config)


@router.get("/org/{origin}")
async def get_platform_org_tree(
    origin: int, session: SessionDep, _current_user: CurrentUser
) -> dict[str, Any]:
    _ = session
    root_name = {
        6: "企业微信",
        7: "钉钉",
        8: "飞书",
        9: "飞书套件",
    }.get(origin, "第三方平台")
    return {
        "tree": [
            PlatformOrgNode(
                id=f"platform-{origin}",
                name=root_name,
                children=[],
                options={"is_user": False},
            ).model_dump()
        ]
    }


@router.post("/user/sync")
async def sync_platform_users(
    payload: PlatformSyncPayload,
    session: SessionDep,
    _current_user: CurrentUser,
) -> PlatformSyncResult:
    defaults = _parameter_defaults(session)
    auto_create = defaults.get("platform.auto_create", "false").lower() == "true"
    default_oid = int(defaults.get("platform.oid") or 1)
    default_rid = int(defaults.get("platform.rid") or 0)

    success_count = 0
    error_count = 0

    for item in payload.user_list:
        platform_uid = str(item.get("id") or "")
        if not platform_uid:
            error_count += 1
            continue

        existing_platform = session.exec(
            select(UserPlatformModel).where(
                col(UserPlatformModel.origin) == payload.origin,
                col(UserPlatformModel.platform_uid) == platform_uid,
            )
        ).first()

        user = (
            session.get(UserModel, existing_platform.uid) if existing_platform else None
        )

        if user is None and not auto_create:
            error_count += 1
            continue

        if user is None:
            account = f"platform_{payload.origin}_{platform_uid}"
            email = str(item.get("email") or f"{account}@sqlbot.local")
            name = str(item.get("name") or account)
            user = UserModel(
                account=account,
                oid=default_oid,
                name=name,
                password=default_md5_pwd(),
                email=email,
                status=1,
                origin=payload.origin,
                language="zh-CN",
            )
            session.add(user)
            session.flush()
            assert user.id is not None
            user_id = user.id
            session.add(
                UserPlatformModel(
                    uid=cast(int, user_id),
                    origin=payload.origin,
                    platform_uid=platform_uid,
                )
            )
            session.add(
                UserWsModel(uid=cast(int, user_id), oid=default_oid, weight=default_rid)
            )
            success_count += 1
            continue

        if payload.cover:
            assert user.id is not None
            user_id = user.id
            user.name = str(item.get("name") or user.name)
            if item.get("email"):
                user.email = str(item.get("email"))
            user.origin = payload.origin
            user.oid = default_oid
            session.add(user)
            existing_uws = session.exec(
                select(UserWsModel).where(
                    col(UserWsModel.uid) == user_id,
                    col(UserWsModel.oid) == default_oid,
                )
            ).first()
            if existing_uws is None:
                session.add(
                    UserWsModel(
                        uid=cast(int, user_id), oid=default_oid, weight=default_rid
                    )
                )
            else:
                existing_uws.weight = default_rid
                session.add(existing_uws)
        success_count += 1

    session.commit()
    return PlatformSyncResult(
        successCount=success_count,
        errorCount=error_count,
        dataKey="",
    )
