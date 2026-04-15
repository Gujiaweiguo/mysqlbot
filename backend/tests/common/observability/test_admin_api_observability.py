from __future__ import annotations

import json
from typing import Any

import pytest

import apps.system.api.authentication as authentication_api
from apps.openclaw.contract import OpenClawSessionBindRequest
from common.observability.admin_api_observability import classify_admin_api_group
from common.utils.utils import SQLBotLogUtil


def test_classify_admin_api_group_matches_critical_paths() -> None:
    assert classify_admin_api_group("/api/v1/system/authentication") == "auth"
    assert classify_admin_api_group("/api/v1/system/platform/client/6") == "platform"
    assert classify_admin_api_group("/api/v1/system/audit/page/1/10") == "audit"
    assert (
        classify_admin_api_group("/api/v1/system/custom_prompt/GENERATE_SQL/page/1/10")
        == "custom_prompt"
    )
    assert classify_admin_api_group("/api/v1/system/appearance") == "appearance"
    assert classify_admin_api_group("/api/v1/system/aimodel/status") == "aimodel"
    assert classify_admin_api_group("/api/v1/ds_permission/list") == "permission"
    assert classify_admin_api_group("/api/v1/openclaw/question") == "openclaw"
    assert classify_admin_api_group("/api/v1/workspace") is None


def test_observability_logs_success_for_monitored_admin_endpoint(
    test_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[dict[str, Any]] = []

    monkeypatch.setattr(
        SQLBotLogUtil,
        "info",
        staticmethod(lambda msg, *args, **kwargs: captured.append(json.loads(msg))),
    )
    monkeypatch.setattr(
        SQLBotLogUtil, "warning", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(
        SQLBotLogUtil, "error", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(authentication_api, "_get_auth_model", lambda *_args: None)

    response = test_app.get("/api/v1/system/authentication/platform/status")

    assert response.status_code == 200
    assert captured
    assert captured[-1]["group"] == "auth"
    assert captured[-1]["status_code"] == 200
    assert captured[-1]["severity"] == "info"


def test_observability_logs_warning_for_failed_admin_endpoint(
    test_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[dict[str, Any]] = []

    monkeypatch.setattr(
        SQLBotLogUtil, "info", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(
        SQLBotLogUtil,
        "warning",
        staticmethod(lambda msg, *args, **kwargs: captured.append(json.loads(msg))),
    )
    monkeypatch.setattr(
        SQLBotLogUtil, "error", staticmethod(lambda *args, **kwargs: None)
    )

    response = test_app.get("/api/v1/system/platform")

    assert response.status_code == 401
    assert captured
    assert captured[-1]["group"] == "platform"
    assert captured[-1]["status_code"] == 401
    assert captured[-1]["severity"] == "warning"


def test_observability_logs_openclaw_request_with_operation_and_error_code(
    test_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import apps.openclaw.router as openclaw_router_module
    from apps.system.schemas.system_schema import UserInfoDTO

    captured: list[dict[str, Any]] = []

    auth_user = UserInfoDTO(
        id=1,
        account="test-admin",
        oid=1,
        name="Test Admin",
        email="test-admin@example.com",
        status=1,
        origin=0,
        oid_list=[1],
        system_variables=[],
        language="en",
        weight=1,
        isAdmin=True,
    )

    async def fake_authenticate(session: object, ask_token: str | None) -> UserInfoDTO:
        _ = session
        _ = ask_token
        return auth_user

    def fake_bind(
        session: object,
        current_user: UserInfoDTO,
        bind_request: OpenClawSessionBindRequest,
    ) -> object:
        _ = session
        _ = current_user
        return type(
            "Binding",
            (),
            {
                "conversation_id": bind_request.conversation_id,
                "chat_id": 101,
                "reused": False,
                "user_id": auth_user.id,
                "workspace_id": auth_user.oid,
                "datasource_id": bind_request.datasource_id,
            },
        )()

    monkeypatch.setattr(
        SQLBotLogUtil,
        "info",
        staticmethod(lambda msg, *args, **kwargs: captured.append(json.loads(msg))),
    )
    monkeypatch.setattr(
        SQLBotLogUtil, "warning", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(
        SQLBotLogUtil, "error", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(
        openclaw_router_module, "authenticate_openclaw_service_token", fake_authenticate
    )
    monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)

    response = test_app.post(
        "/api/v1/openclaw/session/bind",
        headers={"X-SQLBOT-ASK-TOKEN": "sk test-token"},
        json={"conversation_id": "conv-observe"},
    )

    assert response.status_code == 200
    assert captured
    assert captured[-1]["event"] == "openclaw_api_observability"
    assert captured[-1]["group"] == "openclaw"
    assert captured[-1]["operation"] == "session.bind"
    assert captured[-1]["error_code"] == "none"
