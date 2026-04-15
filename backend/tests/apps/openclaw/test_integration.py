from typing import cast

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import apps.openclaw.router as openclaw_router_module
from apps.chat.models.chat_model import ChatQuestion
from apps.openclaw.contract import OpenClawSessionBindRequest
from apps.system.schemas.system_schema import UserInfoDTO


def _openclaw_headers() -> dict[str, str]:
    return {"X-SQLBOT-ASK-TOKEN": "sk test-token"}


def _binding(
    bind_request: OpenClawSessionBindRequest,
    auth_user: UserInfoDTO,
    *,
    chat_id: int,
) -> object:
    return type(
        "Binding",
        (),
        {
            "conversation_id": bind_request.conversation_id,
            "chat_id": chat_id,
            "reused": bind_request.chat_id is not None,
            "user_id": auth_user.id,
            "workspace_id": auth_user.oid,
            "datasource_id": bind_request.datasource_id,
        },
    )()


class TestOpenClawIntegrationFlows:
    def test_bind_then_question_flow_returns_stable_success_envelopes(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
            _ = session
            assert ask_token == "sk test-token"
            return auth_user

        def fake_bind(
            session: object,
            current_user: UserInfoDTO,
            bind_request: OpenClawSessionBindRequest,
        ) -> object:
            _ = session
            _ = current_user
            return _binding(bind_request, auth_user, chat_id=701)

        async def fake_question_answer_inner(**kwargs: object) -> JSONResponse:
            request_question = cast(ChatQuestion, kwargs["request_question"])
            assert request_question.chat_id == 701
            assert request_question.question == "show monthly sales"
            return JSONResponse(
                {
                    "record_id": 801,
                    "summary": "monthly sales ready",
                    "source": "mysqlbot",
                }
            )

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)
        monkeypatch.setattr(
            openclaw_router_module, "question_answer_inner", fake_question_answer_inner
        )

        bind_response = test_app.post(
            "/api/v1/openclaw/session/bind",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-q", "datasource_id": 12},
        )

        assert bind_response.status_code == 200
        bind_payload = cast(dict[str, object], bind_response.json())
        assert bind_payload == {
            "version": "v1",
            "status": "success",
            "operation": "session.bind",
            "data": {
                "conversation_id": "conv-q",
                "chat_id": 701,
                "reused": False,
                "user_id": auth_user.id,
                "workspace_id": auth_user.oid,
                "datasource_id": 12,
            },
        }

        question_response = test_app.post(
            "/api/v1/openclaw/question",
            headers=_openclaw_headers(),
            json={
                "conversation_id": "conv-q",
                "chat_id": cast(dict[str, object], bind_payload["data"])["chat_id"],
                "datasource_id": 12,
                "question": "show monthly sales",
            },
        )

        assert question_response.status_code == 200
        assert question_response.json() == {
            "version": "v1",
            "status": "success",
            "operation": "question.execute",
            "data": {
                "conversation_id": "conv-q",
                "chat_id": 701,
                "result": {
                    "record_id": 801,
                    "summary": "monthly sales ready",
                    "source": "mysqlbot",
                },
            },
        }

    def test_bind_then_analysis_flow_returns_stable_success_envelopes(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
            _ = session
            assert ask_token == "sk test-token"
            return auth_user

        def fake_bind(
            session: object,
            current_user: UserInfoDTO,
            bind_request: OpenClawSessionBindRequest,
        ) -> object:
            _ = session
            _ = current_user
            return _binding(bind_request, auth_user, chat_id=702)

        async def fake_analysis_or_predict(**kwargs: object) -> JSONResponse:
            assert kwargs["chat_record_id"] == 901
            assert kwargs["action_type"] == "analysis"
            return JSONResponse(
                {"analysis": "sales trend summarized", "source": "mysqlbot"}
            )

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)
        monkeypatch.setattr(
            openclaw_router_module, "analysis_or_predict", fake_analysis_or_predict
        )

        bind_response = test_app.post(
            "/api/v1/openclaw/session/bind",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-a"},
        )

        assert bind_response.status_code == 200
        bind_payload = cast(dict[str, object], bind_response.json())
        assert cast(dict[str, object], bind_payload["data"])["chat_id"] == 702

        analysis_response = test_app.post(
            "/api/v1/openclaw/analysis",
            headers=_openclaw_headers(),
            json={
                "conversation_id": "conv-a",
                "chat_id": cast(dict[str, object], bind_payload["data"])["chat_id"],
                "record_id": 901,
                "action_type": "analysis",
            },
        )

        assert analysis_response.status_code == 200
        assert analysis_response.json() == {
            "version": "v1",
            "status": "success",
            "operation": "analysis.execute",
            "data": {
                "conversation_id": "conv-a",
                "chat_id": 702,
                "record_id": 901,
                "action_type": "analysis",
                "result": {
                    "analysis": "sales trend summarized",
                    "source": "mysqlbot",
                },
            },
        }
