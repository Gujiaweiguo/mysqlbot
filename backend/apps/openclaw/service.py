from dataclasses import dataclass
from typing import cast

import jwt
from fastapi.security.utils import get_authorization_scheme_param

from apps.chat.crud.chat import create_chat, get_chat
from apps.chat.models.chat_model import CreateChat
from apps.openclaw.contract import (
    AUTH_HEADER,
    AUTH_SCHEME,
    OpenClawErrorCode,
    OpenClawSessionBindRequest,
)
from apps.system.crud.apikey_manage import get_api_key
from apps.system.crud.user import get_user_info
from apps.system.models.system_model import ApiKeyModel
from apps.system.schemas.system_schema import UserInfoDTO
from common.core import security
from common.core.deps import SessionDep


@dataclass(slots=True)
class OpenClawServiceError(Exception):
    error_code: str
    message: str
    detail: dict[str, object] | None = None


@dataclass(slots=True)
class OpenClawSessionBinding:
    chat_id: int
    conversation_id: str
    reused: bool
    user_id: int
    workspace_id: int
    datasource_id: int | None


def _normalize_api_key(
    raw_api_key: ApiKeyModel | dict[str, object] | None,
) -> ApiKeyModel | None:
    if raw_api_key is None:
        return None
    if isinstance(raw_api_key, ApiKeyModel):
        return raw_api_key
    return ApiKeyModel.model_validate(raw_api_key)


def _normalize_service_user(
    raw_user: UserInfoDTO | dict[str, object] | None,
) -> UserInfoDTO | None:
    if raw_user is None:
        return None
    if isinstance(raw_user, UserInfoDTO):
        return raw_user
    return UserInfoDTO.model_validate(raw_user)


async def authenticate_openclaw_service_token(
    session: SessionDep, ask_token: str | None
) -> UserInfoDTO:
    if not ask_token:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_INVALID,
            message=f"Missing service credential in {AUTH_HEADER}",
            detail={"header": AUTH_HEADER},
        )

    schema, token = get_authorization_scheme_param(ask_token)
    if schema.lower() != AUTH_SCHEME:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_INVALID,
            message="Token schema error",
            detail={"expected_scheme": AUTH_SCHEME},
        )

    try:
        unsigned_payload = cast(
            dict[str, object],
            jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=[security.ALGORITHM],
            ),
        )
    except Exception as exc:  # pragma: no cover - library exception mapping
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_INVALID,
            message="Invalid service credential",
        ) from exc

    access_key = unsigned_payload.get("access_key")
    if not isinstance(access_key, str) or access_key == "":
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_INVALID,
            message="Missing access_key payload",
        )

    api_key = _normalize_api_key(
        cast(
            ApiKeyModel | dict[str, object] | None,
            await get_api_key(session, access_key),
        )
    )
    if api_key is None:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_INVALID,
            message="Invalid access_key",
        )
    if not api_key.status:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_DISABLED,
            message="Disabled access_key",
        )

    try:
        _ = jwt.decode(token, api_key.secret_key, algorithms=[security.ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_EXPIRED,
            message="Service credential expired",
        ) from exc
    except Exception as exc:  # pragma: no cover - library exception mapping
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_INVALID,
            message="Invalid service credential signature",
        ) from exc

    session_user = _normalize_service_user(
        cast(
            UserInfoDTO | dict[str, object] | None,
            await get_user_info(session=session, user_id=api_key.uid),
        )
    )
    if session_user is None:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_INVALID,
            message="User not found for service credential",
        )
    if session_user.status != 1:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_DISABLED,
            message="Inactive user",
        )
    if not session_user.oid or session_user.oid == 0:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.AUTH_INVALID,
            message="No associated workspace",
        )
    return session_user


def bind_openclaw_session(
    session: SessionDep,
    current_user: UserInfoDTO,
    bind_request: OpenClawSessionBindRequest,
) -> OpenClawSessionBinding:
    if bind_request.chat_id is not None:
        existing_chat = get_chat(session, bind_request.chat_id)
        if existing_chat is None:
            raise OpenClawServiceError(
                error_code=OpenClawErrorCode.SESSION_INVALID,
                message="Chat session not found",
                detail={"chat_id": bind_request.chat_id},
            )
        if (
            existing_chat.create_by != current_user.id
            or existing_chat.oid != current_user.oid
        ):
            raise OpenClawServiceError(
                error_code=OpenClawErrorCode.SESSION_INVALID,
                message="Chat session does not belong to authenticated caller scope",
                detail={"chat_id": bind_request.chat_id},
            )
        if (
            bind_request.datasource_id is not None
            and existing_chat.datasource is not None
            and bind_request.datasource_id != existing_chat.datasource
        ):
            raise OpenClawServiceError(
                error_code=OpenClawErrorCode.SESSION_INVALID,
                message="Chat session datasource does not match requested datasource",
                detail={
                    "chat_id": bind_request.chat_id,
                    "requested_datasource_id": bind_request.datasource_id,
                    "existing_datasource_id": existing_chat.datasource,
                },
            )
        chat_id = existing_chat.id
        if chat_id is None:
            raise OpenClawServiceError(
                error_code=OpenClawErrorCode.SESSION_INVALID,
                message="Chat session is missing an identifier",
            )
        return OpenClawSessionBinding(
            chat_id=chat_id,
            conversation_id=bind_request.conversation_id,
            reused=True,
            user_id=current_user.id,
            workspace_id=current_user.oid,
            datasource_id=existing_chat.datasource,
        )

    chat_info = create_chat(
        session=session,
        current_user=current_user,
        create_chat_obj=CreateChat(
            question=bind_request.conversation_id,
            datasource=bind_request.datasource_id,
            origin=1,
        ),
        require_datasource=False,
    )
    if chat_info.id is None:
        raise OpenClawServiceError(
            error_code=OpenClawErrorCode.INTERNAL_ERROR,
            message="Failed to create chat session",
        )

    return OpenClawSessionBinding(
        chat_id=chat_info.id,
        conversation_id=bind_request.conversation_id,
        reused=False,
        user_id=current_user.id,
        workspace_id=current_user.oid,
        datasource_id=chat_info.datasource,
    )
