from collections.abc import Callable
from datetime import timedelta
from importlib import import_module
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

from apps.system.schemas.logout_schema import LogoutSchema
from apps.system.schemas.system_schema import BaseUserDTO
from common.audit.models.log_model import OperationModules, OperationType
from common.audit.schemas.logger_decorator import LogConfig, system_log
from common.core.config import settings
from common.core.deps import SessionDep, Trans
from common.core.schemas import Token
from common.core.security import create_access_token
from common.utils.crypto import sqlbot_decrypt

from ..crud.user import authenticate

router = APIRouter(tags=["login"], prefix="/login")

typed_system_log = cast(Callable[[LogConfig], Callable[..., Any]], system_log)


async def _xpack_logout(
    session: SessionDep, request: Request, dto: LogoutSchema
) -> Any:
    module = import_module("sqlbot_xpack.authentication.manage")
    logout = module.logout
    return await logout(session, request, dto)


@router.post("/access-token")
@typed_system_log(
    LogConfig(
        operation_type=OperationType.LOGIN,
        module=OperationModules.USER,
        result_id_expr="id",
    )
)
async def local_login(
    session: SessionDep,
    trans: Trans,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    origin_account = await sqlbot_decrypt(form_data.username)
    origin_pwd = await sqlbot_decrypt(form_data.password)
    user = authenticate(session=session, account=origin_account, password=origin_pwd)
    if not user:
        raise HTTPException(
            status_code=400, detail=trans("i18n_login.account_pwd_error")
        )
    user_dto = BaseUserDTO.model_validate(user)
    if not user_dto.oid or user_dto.oid == 0:
        raise HTTPException(
            status_code=400,
            detail=trans("i18n_login.no_associated_ws", msg=trans("i18n_concat_admin")),
        )
    if user_dto.status != 1:
        raise HTTPException(
            status_code=400,
            detail=trans("i18n_login.user_disable", msg=trans("i18n_concat_admin")),
        )
    if user_dto.origin is not None and user_dto.origin != 0:
        raise HTTPException(status_code=400, detail=trans("i18n_login.origin_error"))
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_dict = user_dto.to_dict()
    return Token(
        access_token=create_access_token(user_dict, expires_delta=access_token_expires)
    )


@router.post("/logout")
async def logout(session: SessionDep, request: Request, dto: LogoutSchema) -> None:
    if dto.origin != 0:
        await _xpack_logout(session, request, dto)
