import re
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from inspect import signature
from typing import Any, TypeVar, cast

from fastapi import HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select
from starlette.middleware.base import BaseHTTPMiddleware

from apps.chat.models.chat_model import Chat
from apps.datasource.crud.datasource import get_ws_ds
from apps.system.schemas.system_schema import UserInfoDTO
from common.core.db import engine
from common.utils.locale import I18n

i18n = I18n()

F = TypeVar("F", bound=Callable[..., Any])


class SqlbotPermission(BaseModel):
    role: list[str] | None = None
    type: str | None = None
    keyExpression: str | None = None


async def get_ws_resource(oid: int, type: str) -> list[Any]:
    with Session(engine) as session:
        stmt = None
        if type == "ds" or type == "datasource":
            return list(await get_ws_ds(session, oid))
        if type == "chat":
            stmt = select(Chat.id).where(Chat.oid == oid)
        if stmt is not None:
            db_list = session.exec(stmt).all()
            return list(db_list)
        return []


async def check_ws_permission(oid: int, type: str, resource: Any) -> bool:
    if not resource or (isinstance(resource, list) and len(resource) == 0):
        return True

    resource_id_list = await get_ws_resource(oid, type)
    if not resource_id_list:
        return False
    if isinstance(resource, list):
        return set(resource).issubset(set(resource_id_list))
    return resource in resource_id_list


def require_permissions(permission: SqlbotPermission) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = RequestContext.get_request()

            current_user = cast(
                UserInfoDTO | None, getattr(request.state, "current_user", None)
            )
            if not current_user:
                raise HTTPException(status_code=401, detail="用户未认证")
            current_oid = current_user.oid

            trans = i18n(request)

            if current_user.isAdmin and not permission.type:
                return await func(*args, **kwargs)
            role_list = permission.role
            keyExpression = permission.keyExpression
            resource_type = permission.type

            if role_list:
                if "admin" in role_list and not current_user.isAdmin:
                    # raise Exception('no permission to execute, only for admin')
                    raise Exception(trans("i18n_permission.only_admin"))
                if (
                    "ws_admin" in role_list
                    and current_user.weight == 0
                    and not current_user.isAdmin
                ):
                    # raise Exception('no permission to execute, only for workspace admin')
                    raise Exception(trans("i18n_permission.only_ws_admin"))
            if not resource_type:
                return await func(*args, **kwargs)
            if keyExpression:
                sig = signature(func)
                bound_args = sig.bind_partial(*args, **kwargs)
                bound_args.apply_defaults()

                if keyExpression.startswith("args["):
                    if match := re.match(r"args\[(\d+)\]", keyExpression):
                        index = int(match.group(1))
                        value = bound_args.args[index]
                        if await check_ws_permission(current_oid, resource_type, value):
                            return await func(*args, **kwargs)
                        # raise Exception('no permission to execute or resource do not exist!')
                        raise Exception(
                            trans("i18n_permission.permission_resource_limit")
                        )

                parts = keyExpression.split(".")
                if not bound_args.arguments.get(parts[0]):
                    return await func(*args, **kwargs)
                value = bound_args.arguments[parts[0]]
                for part in parts[1:]:
                    value = getattr(value, part)
                if await check_ws_permission(current_oid, resource_type, value):
                    return await func(*args, **kwargs)
                raise Exception(trans("i18n_permission.permission_resource_limit"))

            return await func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


class RequestContext:
    _current_request: ContextVar[Request] = ContextVar("_current_request")

    @classmethod
    def set_request(cls, request: Request) -> Any:
        return cls._current_request.set(request)

    @classmethod
    def get_request(cls) -> Request:
        try:
            return cls._current_request.get()
        except LookupError:
            raise RuntimeError(
                "No request context found. "
                "Make sure RequestContextMiddleware is installed."
            )

    @classmethod
    def reset(cls, token: Any) -> None:
        cls._current_request.reset(token)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Any:
        token = RequestContext.set_request(request)
        try:
            response = await call_next(request)
            return response
        finally:
            RequestContext.reset(token)
