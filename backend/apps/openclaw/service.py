from dataclasses import dataclass
from typing import cast

import jwt
from fastapi.security.utils import get_authorization_scheme_param
from sqlmodel import Session

from apps.chat.crud.chat import create_chat, get_chat, get_chat_by_external_session_key
from apps.chat.models.chat_model import Chat, CreateChat
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


def build_openclaw_external_session_key(conversation_id: str) -> str:
    return f"openclaw:{conversation_id.strip()}"


def _lookup_chat_by_external_session_key(
    session: SessionDep,
    *,
    user_id: int,
    workspace_id: int,
    external_session_key: str,
) -> Chat | None:
    custom_lookup = getattr(session, "find_chat_by_external_session_key", None)
    if callable(custom_lookup):
        return cast(
            Chat | None,
            custom_lookup(
                user_id=user_id,
                workspace_id=workspace_id,
                external_session_key=external_session_key,
            ),
        )

    return get_chat_by_external_session_key(
        cast(Session, session),
        user_id=user_id,
        workspace_id=workspace_id,
        external_session_key=external_session_key,
    )


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
    external_session_key = build_openclaw_external_session_key(
        bind_request.conversation_id
    )

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
        if existing_chat.origin != 1:
            raise OpenClawServiceError(
                error_code=OpenClawErrorCode.SESSION_INVALID,
                message="Chat session is not managed by the OpenClaw integration",
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
        if (
            existing_chat.external_session_key is not None
            and existing_chat.external_session_key != external_session_key
        ):
            raise OpenClawServiceError(
                error_code=OpenClawErrorCode.SESSION_INVALID,
                message="Chat session does not belong to the requested external session scope",
                detail={
                    "chat_id": bind_request.chat_id,
                    "requested_external_session_key": external_session_key,
                    "existing_external_session_key": existing_chat.external_session_key,
                },
            )
        if not existing_chat.external_session_key:
            existing_chat.external_session_key = external_session_key
            session.add(existing_chat)
            session.flush()
            session.commit()
        return OpenClawSessionBinding(
            chat_id=chat_id,
            conversation_id=bind_request.conversation_id,
            reused=True,
            user_id=current_user.id,
            workspace_id=current_user.oid,
            datasource_id=existing_chat.datasource,
        )

    existing_chat = _lookup_chat_by_external_session_key(
        session,
        user_id=current_user.id,
        workspace_id=current_user.oid,
        external_session_key=external_session_key,
    )
    if existing_chat is not None:
        if (
            bind_request.datasource_id is not None
            and existing_chat.datasource is not None
            and bind_request.datasource_id != existing_chat.datasource
        ):
            raise OpenClawServiceError(
                error_code=OpenClawErrorCode.SESSION_INVALID,
                message="External session datasource does not match requested datasource",
                detail={
                    "external_session_key": external_session_key,
                    "requested_datasource_id": bind_request.datasource_id,
                    "existing_datasource_id": existing_chat.datasource,
                },
            )
        if existing_chat.id is None:
            raise OpenClawServiceError(
                error_code=OpenClawErrorCode.SESSION_INVALID,
                message="Resolved external session is missing an identifier",
            )
        return OpenClawSessionBinding(
            chat_id=existing_chat.id,
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
            external_session_key=external_session_key,
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
