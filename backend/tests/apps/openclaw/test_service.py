from dataclasses import dataclass
from typing import cast

import jwt
import pytest
from sqlmodel import Session

from apps.chat.models.chat_model import Chat
from apps.openclaw.contract import AUTH_HEADER, OpenClawSessionBindRequest
from apps.openclaw.service import (
    OpenClawServiceError,
    authenticate_openclaw_service_token,
    bind_openclaw_session,
)
from apps.system.schemas.system_schema import UserInfoDTO


@dataclass
class _FakeApiKey:
    access_key: str
    secret_key: str
    uid: int
    status: bool


class _FakeSession:
    def __init__(self) -> None:
        self._storage: dict[tuple[type[object], int], object] = {}
        self._next_id: int = 1

    def add(self, obj: object) -> None:
        assert hasattr(obj, "_sa_instance_state")
        obj_id = getattr(obj, "id", None)
        if obj_id is None:
            assert isinstance(obj, Chat)
            obj.id = self._next_id
            obj_id = self._next_id
            self._next_id += 1
        self._storage[(type(obj), obj_id)] = obj

    def flush(self) -> None:
        return None

    def refresh(self, obj: object) -> None:
        _ = obj
        return None

    def commit(self) -> None:
        return None

    def get(self, model: type[object], obj_id: int | None) -> object | None:
        if obj_id is None:
            return None
        return self._storage.get((model, obj_id))


def _build_user() -> UserInfoDTO:
    return UserInfoDTO(
        id=7,
        account="openclaw-service",
        oid=9,
        name="OpenClaw Service",
        email="openclaw@example.com",
        status=1,
        origin=0,
        oid_list=[9],
        system_variables=[],
        language="zh-CN",
        weight=1,
        isAdmin=False,
    )


@pytest.mark.asyncio
async def test_authenticate_openclaw_service_token_accepts_valid_ask_token(
    monkeypatch: pytest.MonkeyPatch,
    test_db: object,
) -> None:
    token = jwt.encode(
        {"access_key": "ak-1"},
        "secret-1-secret-1-secret-1-secret-1",
        algorithm="HS256",
    )

    async def fake_get_api_key(session: object, access_key: str) -> _FakeApiKey | None:
        _ = session
        return _FakeApiKey(
            access_key=access_key,
            secret_key="secret-1-secret-1-secret-1-secret-1",
            uid=7,
            status=True,
        )

    async def fake_get_user_info(
        *, session: object, user_id: int
    ) -> UserInfoDTO | None:
        _ = session
        _ = user_id
        return _build_user()

    monkeypatch.setattr("apps.openclaw.service.get_api_key", fake_get_api_key)
    monkeypatch.setattr("apps.openclaw.service.get_user_info", fake_get_user_info)

    user = await authenticate_openclaw_service_token(
        cast(Session, test_db),
        f"sk {token}",
    )

    assert user.account == "openclaw-service"
    assert user.oid == 9


@pytest.mark.asyncio
async def test_authenticate_openclaw_service_token_accepts_cached_dict_user(
    monkeypatch: pytest.MonkeyPatch,
    test_db: object,
) -> None:
    token = jwt.encode(
        {"access_key": "ak-cached"},
        "secret-cached-secret-cached-secret-cached",
        algorithm="HS256",
    )

    async def fake_get_api_key(session: object, access_key: str) -> _FakeApiKey | None:
        _ = session
        return _FakeApiKey(
            access_key=access_key,
            secret_key="secret-cached-secret-cached-secret-cached",
            uid=7,
            status=True,
        )

    async def fake_get_user_info(
        *, session: object, user_id: int
    ) -> dict[str, object] | None:
        _ = session
        _ = user_id
        return _build_user().model_dump()

    monkeypatch.setattr("apps.openclaw.service.get_api_key", fake_get_api_key)
    monkeypatch.setattr("apps.openclaw.service.get_user_info", fake_get_user_info)

    user = await authenticate_openclaw_service_token(
        cast(Session, test_db),
        f"sk {token}",
    )

    assert user.account == "openclaw-service"
    assert user.status == 1
    assert user.oid == 9


@pytest.mark.asyncio
async def test_authenticate_openclaw_service_token_rejects_disabled_key(
    monkeypatch: pytest.MonkeyPatch,
    test_db: object,
) -> None:
    token = jwt.encode(
        {"access_key": "ak-2"},
        "secret-2-secret-2-secret-2-secret-2",
        algorithm="HS256",
    )

    async def fake_get_api_key(session: object, access_key: str) -> _FakeApiKey | None:
        _ = session
        return _FakeApiKey(
            access_key=access_key,
            secret_key="secret-2-secret-2-secret-2-secret-2",
            uid=7,
            status=False,
        )

    monkeypatch.setattr("apps.openclaw.service.get_api_key", fake_get_api_key)

    with pytest.raises(OpenClawServiceError) as exc_info:
        _ = await authenticate_openclaw_service_token(
            cast(Session, test_db), f"sk {token}"
        )

    assert exc_info.value.error_code == "AUTH_DISABLED"


@pytest.mark.asyncio
async def test_authenticate_openclaw_service_token_rejects_missing_header(
    test_db: object,
) -> None:
    with pytest.raises(OpenClawServiceError) as exc_info:
        _ = await authenticate_openclaw_service_token(cast(Session, test_db), None)

    assert exc_info.value.error_code == "AUTH_INVALID"
    assert AUTH_HEADER in exc_info.value.message


def test_bind_openclaw_session_reuses_existing_chat() -> None:
    session = _FakeSession()
    user = _build_user()
    existing_chat = Chat(
        id=11,
        oid=user.oid,
        create_by=user.id,
        brief="existing",
        chat_type="chat",
        datasource=5,
        engine_type="",
        origin=1,
        brief_generate=False,
        recommended_question_answer=None,
        recommended_question=None,
        recommended_generate=False,
    )
    session.add(existing_chat)

    binding = bind_openclaw_session(
        cast(Session, cast(object, session)),
        user,
        OpenClawSessionBindRequest(
            conversation_id="conv-1",
            chat_id=11,
            datasource_id=5,
        ),
    )

    assert binding.reused is True
    assert binding.chat_id == 11
    assert binding.workspace_id == 9


def test_bind_openclaw_session_creates_new_chat_without_orphan_record() -> None:
    session = _FakeSession()
    user = _build_user()

    binding = bind_openclaw_session(
        cast(Session, cast(object, session)),
        user,
        OpenClawSessionBindRequest(conversation_id="conv-new"),
    )

    assert binding.reused is False
    assert binding.chat_id > 0
    stored_chat = cast(Chat | None, session.get(Chat, binding.chat_id))
    assert stored_chat is not None
    assert stored_chat.create_by == user.id
    assert stored_chat.oid == user.oid


def test_bind_openclaw_session_rejects_foreign_chat_scope() -> None:
    session = _FakeSession()
    user = _build_user()
    foreign_chat = Chat(
        id=12,
        oid=999,
        create_by=999,
        brief="foreign",
        chat_type="chat",
        datasource=None,
        engine_type="",
        origin=1,
        brief_generate=False,
        recommended_question_answer=None,
        recommended_question=None,
        recommended_generate=False,
    )
    session.add(foreign_chat)

    with pytest.raises(OpenClawServiceError) as exc_info:
        _ = bind_openclaw_session(
            cast(Session, cast(object, session)),
            user,
            OpenClawSessionBindRequest(conversation_id="conv-2", chat_id=12),
        )

    assert exc_info.value.error_code == "SESSION_INVALID"
