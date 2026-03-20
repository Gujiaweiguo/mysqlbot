import json
import time
from typing import Any, cast

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import col, select

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.models.system_model import AuthenticationModel
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import CurrentUser, SessionDep

AUTH_PROVIDER_NAMES: dict[int, str] = {
    1: "cas",
    2: "oidc",
    3: "ldap",
    4: "oauth2",
    5: "saml2",
    6: "wecom",
    7: "dingtalk",
    8: "lark",
    9: "larksuite",
}

REQUIRED_CONFIG_FIELDS: dict[int, list[str]] = {
    1: ["idpUri", "casCallbackDomain"],
    2: ["client_id", "client_secret", "metadata_url", "redirect_uri", "scope"],
    3: ["server_address", "bind_dn", "bind_pwd", "ou", "user_filter"],
    4: [
        "authorize_url",
        "token_url",
        "userinfo_url",
        "client_id",
        "client_secret",
        "redirect_url",
    ],
    5: ["idpMetaUrl"],
    6: ["corpid", "agent_id", "corpsecret"],
    7: ["corpid", "agent_id", "client_id", "client_secret"],
    8: ["client_id", "client_secret"],
    9: ["client_id", "client_secret"],
}


class AuthenticationStatusSchema(BaseModel):
    id: int
    name: str
    valid: bool
    enable: bool


class AuthenticationConfigSchema(BaseModel):
    id: int
    type: int
    name: str
    config: str | None = None
    valid: bool = False
    enable: bool = False


class AuthenticationMutationSchema(BaseModel):
    id: int
    type: int
    name: str
    config: str


class AuthenticationEnableSchema(BaseModel):
    id: int
    enable: bool


class AuthenticationValidateSchema(BaseModel):
    type: int
    name: str = ""
    config: str = ""


router = APIRouter(tags=["system/authentication"], prefix="/system/authentication")


def _provider_name(type_id: int) -> str:
    return AUTH_PROVIDER_NAMES.get(type_id, f"provider-{type_id}")


def _default_auth_payload(type_id: int) -> AuthenticationConfigSchema:
    return AuthenticationConfigSchema(
        id=type_id,
        type=type_id,
        name=_provider_name(type_id),
        config=None,
        valid=False,
        enable=False,
    )


def _parse_config(config: str | None) -> dict[str, Any]:
    if not config:
        return {}
    try:
        parsed = json.loads(config)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_config_valid(type_id: int, config: str | None) -> bool:
    parsed = _parse_config(config)
    required_fields = REQUIRED_CONFIG_FIELDS.get(type_id, [])
    if not required_fields:
        return False
    return all(bool(parsed.get(field)) for field in required_fields)


def _get_auth_model(session: SessionDep, type_id: int) -> AuthenticationModel | None:
    return session.exec(
        select(AuthenticationModel).where(col(AuthenticationModel.type) == type_id)
    ).first()


def _upsert_auth_model(
    session: SessionDep,
    type_id: int,
    name: str,
    config: str,
) -> AuthenticationModel:
    db_model = _get_auth_model(session, type_id)
    if db_model is None:
        db_model = AuthenticationModel(
            name=name,
            type=type_id,
            config=config,
            create_time=int(time.time() * 1000),
            enable=False,
            valid=False,
        )
    else:
        db_model.name = name
        db_model.config = config
    db_model.valid = _is_config_valid(type_id, config)
    if not db_model.valid:
        db_model.enable = False
    session.add(db_model)
    session.commit()
    session.refresh(db_model)
    return db_model


def _to_status_schema(
    type_id: int, db_model: AuthenticationModel | None
) -> AuthenticationStatusSchema:
    if db_model is None:
        return AuthenticationStatusSchema(
            id=type_id,
            name=_provider_name(type_id),
            valid=False,
            enable=False,
        )
    return AuthenticationStatusSchema(
        id=type_id,
        name=db_model.name,
        valid=bool(db_model.valid),
        enable=bool(db_model.enable and db_model.valid),
    )


def _to_config_schema(
    type_id: int, db_model: AuthenticationModel | None
) -> AuthenticationConfigSchema:
    if db_model is None:
        return _default_auth_payload(type_id)
    return AuthenticationConfigSchema(
        id=type_id,
        type=type_id,
        name=db_model.name,
        config=db_model.config,
        valid=bool(db_model.valid),
        enable=bool(db_model.enable and db_model.valid),
    )


@router.get("")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def list_authentication(
    session: SessionDep, _current_user: CurrentUser
) -> list[AuthenticationStatusSchema]:
    return [
        _to_status_schema(type_id, _get_auth_model(session, type_id))
        for type_id in range(1, 6)
    ]


@router.get(
    "/platform/status",
    response_model=list[AuthenticationStatusSchema],
    summary=f"{PLACEHOLDER_PREFIX}authentication_platform_status",
    description=f"{PLACEHOLDER_PREFIX}authentication_platform_status",
)
async def platform_status(session: SessionDep) -> list[AuthenticationStatusSchema]:
    return [
        _to_status_schema(type_id, _get_auth_model(session, type_id))
        for type_id in range(1, 10)
    ]


@router.get("/{id}")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def get_authentication(
    id: int, session: SessionDep, _current_user: CurrentUser
) -> AuthenticationConfigSchema:
    return _to_config_schema(id, _get_auth_model(session, id))


@router.post("")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def create_authentication(
    payload: AuthenticationMutationSchema,
    session: SessionDep,
    _current_user: CurrentUser,
) -> AuthenticationConfigSchema:
    db_model = _upsert_auth_model(session, payload.type, payload.name, payload.config)
    return _to_config_schema(payload.type, db_model)


@router.put("")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def update_authentication(
    payload: AuthenticationMutationSchema,
    session: SessionDep,
    _current_user: CurrentUser,
) -> AuthenticationConfigSchema:
    db_model = _upsert_auth_model(session, payload.type, payload.name, payload.config)
    return _to_config_schema(payload.type, db_model)


@router.patch("/enable")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def enable_authentication(
    payload: AuthenticationEnableSchema,
    session: SessionDep,
    _current_user: CurrentUser,
) -> bool:
    db_model = _get_auth_model(session, payload.id)
    if db_model is None:
        return False
    db_model.valid = _is_config_valid(payload.id, db_model.config)
    db_model.enable = bool(payload.enable and db_model.valid)
    session.add(db_model)
    session.commit()
    return db_model.enable


@router.patch("/status")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def validate_authentication(
    payload: AuthenticationValidateSchema,
    session: SessionDep,
    _current_user: CurrentUser,
) -> bool:
    config = payload.config
    if not config:
        db_model = _get_auth_model(session, payload.type)
        if db_model is None:
            return False
        config = cast(str, db_model.config or "")
    valid = _is_config_valid(payload.type, config)
    db_model = _get_auth_model(session, payload.type)
    if db_model is not None:
        db_model.valid = valid
        if not valid:
            db_model.enable = False
        session.add(db_model)
        session.commit()
    return valid
