from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import cast

import pytest
from sqlmodel import Session

import apps.chat.api.chat as chat_api
from apps.chat.models.chat_model import ChatInfo, CreateChat
from apps.system.schemas.system_schema import AssistantHeader, UserInfoDTO
from common.audit.schemas.request_context import RequestContext


def _build_user() -> UserInfoDTO:
    return UserInfoDTO(
        id=1,
        account="assistant-user",
        oid=1,
        name="Assistant User",
        email="assistant@example.com",
        status=1,
        origin=0,
        oid_list=[1],
        system_variables=[],
        language="en",
        weight=1,
        isAdmin=True,
    )


def _build_assistant(configuration: dict[str, object]) -> AssistantHeader:
    return AssistantHeader(
        id=77,
        name="Assistant",
        domain="http://example.com",
        type=0,
        description="demo",
        oid=1,
        configuration=json.dumps(configuration),
        online=False,
    )


@pytest.mark.asyncio
async def test_assistant_start_chat_uses_default_datasource_from_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(RequestContext, "get_request", staticmethod(lambda: None))

    def fake_create_chat(
        session: Session,
        current_user: UserInfoDTO,
        create_chat_obj: CreateChat,
        require_datasource: bool = True,
        current_assistant: AssistantHeader | None = None,
    ) -> ChatInfo:
        captured["session"] = session
        captured["current_user"] = current_user
        captured["datasource"] = create_chat_obj.datasource
        captured["require_datasource"] = require_datasource
        captured["current_assistant"] = current_assistant
        return ChatInfo(
            id=9001,
            datasource=create_chat_obj.datasource,
            datasource_name="Orders Demo",
        )

    monkeypatch.setattr(chat_api, "create_chat", fake_create_chat)

    assistant_start_chat = cast(
        Callable[..., Awaitable[ChatInfo]],
        chat_api.assistant_start_chat,
    )

    response = await assistant_start_chat(
        session=cast(Session, object()),
        current_user=_build_user(),
        current_assistant=_build_assistant(
            {
                "auto_ds": True,
                "default_datasource_id": 101,
                "datasource_ids": [101],
                "workspace_ids": [1],
            }
        ),
        create_chat_obj=CreateChat(origin=2),
    )

    assert response.datasource == 101
    assert captured["datasource"] == 101
    assert captured["require_datasource"] is True


@pytest.mark.asyncio
async def test_assistant_start_chat_preserves_explicit_datasource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(RequestContext, "get_request", staticmethod(lambda: None))

    def fake_create_chat(
        _session: Session,
        _current_user: UserInfoDTO,
        create_chat_obj: CreateChat,
        require_datasource: bool = True,
        _current_assistant: AssistantHeader | None = None,
    ) -> ChatInfo:
        captured["datasource"] = create_chat_obj.datasource
        captured["require_datasource"] = require_datasource
        return ChatInfo(
            id=9002, datasource=create_chat_obj.datasource, datasource_name="CRM Demo"
        )

    monkeypatch.setattr(chat_api, "create_chat", fake_create_chat)

    assistant_start_chat = cast(
        Callable[..., Awaitable[ChatInfo]],
        chat_api.assistant_start_chat,
    )

    response = await assistant_start_chat(
        session=cast(Session, object()),
        current_user=_build_user(),
        current_assistant=_build_assistant(
            {
                "auto_ds": True,
                "default_datasource_id": 101,
                "datasource_ids": [101, 202],
                "workspace_ids": [1],
            }
        ),
        create_chat_obj=CreateChat(origin=2, datasource=202),
    )

    assert response.datasource == 202
    assert captured["datasource"] == 202
    assert captured["require_datasource"] is True
