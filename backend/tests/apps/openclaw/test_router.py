import asyncio

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from httpx import AsyncClient

import apps.openclaw.router as openclaw_router_module
from apps.chat.models.chat_model import ChatQuestion
from apps.openclaw.contract import OpenClawSessionBindRequest
from apps.system.schemas.system_schema import UserInfoDTO
from common.core.config import settings


def _openclaw_headers() -> dict[str, str]:
    return {"X-SQLBOT-ASK-TOKEN": "sk test-token"}


class _FakeDatasource:
    def __init__(self, **payload: object) -> None:
        self._payload: dict[str, object] = payload

    def model_dump(self) -> dict[str, object]:
        return dict(self._payload)


class TestOpenClawRouter:
    def test_bind_session_returns_contract_envelope(
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
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)

        response = test_app.post(
            "/api/v1/openclaw/session/bind",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-1", "datasource_id": 7},
        )

        assert response.status_code == 200
        assert response.json() == {
            "version": "v1",
            "status": "success",
            "operation": "session.bind",
            "data": {
                "conversation_id": "conv-1",
                "chat_id": 101,
                "reused": False,
                "user_id": auth_user.id,
                "workspace_id": auth_user.oid,
                "datasource_id": 7,
            },
        }

    def test_bind_session_returns_auth_error_envelope(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
            _ = session
            _ = ask_token
            from apps.openclaw.service import OpenClawServiceError

            raise OpenClawServiceError("AUTH_INVALID", "Invalid service credential")

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )

        response = test_app.post(
            "/api/v1/openclaw/session/bind",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-1"},
        )

        assert response.status_code == 401
        assert response.json()["error_code"] == "AUTH_INVALID"
        assert response.json()["operation"] == "session.bind"

    def test_question_route_delegates_and_wraps_result(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
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
                    "chat_id": 202,
                    "reused": True,
                    "user_id": auth_user.id,
                    "workspace_id": auth_user.oid,
                    "datasource_id": bind_request.datasource_id,
                },
            )()

        async def fake_question_answer_inner(**kwargs: object) -> JSONResponse:
            request_question = kwargs["request_question"]
            assert isinstance(request_question, ChatQuestion)
            assert request_question.chat_id == 202
            assert request_question.question == "show sales"
            return JSONResponse({"record_id": 303, "summary": "ok"})

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)
        monkeypatch.setattr(
            openclaw_router_module, "question_answer_inner", fake_question_answer_inner
        )

        response = test_app.post(
            "/api/v1/openclaw/question",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-2", "question": "show sales"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "version": "v1",
            "status": "success",
            "operation": "question.execute",
            "data": {
                "conversation_id": "conv-2",
                "chat_id": 202,
                "result": {"record_id": 303, "summary": "ok"},
            },
        }

    def test_analysis_route_delegates_and_wraps_result(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
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
                    "chat_id": bind_request.chat_id,
                    "reused": True,
                    "user_id": auth_user.id,
                    "workspace_id": auth_user.oid,
                    "datasource_id": None,
                },
            )()

        async def fake_analysis_or_predict(**kwargs: object) -> JSONResponse:
            assert kwargs["chat_record_id"] == 404
            assert kwargs["action_type"] == "analysis"
            return JSONResponse({"analysis": "done"})

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)
        monkeypatch.setattr(
            openclaw_router_module, "analysis_or_predict", fake_analysis_or_predict
        )

        response = test_app.post(
            "/api/v1/openclaw/analysis",
            headers=_openclaw_headers(),
            json={
                "conversation_id": "conv-3",
                "chat_id": 33,
                "record_id": 404,
                "action_type": "analysis",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "version": "v1",
            "status": "success",
            "operation": "analysis.execute",
            "data": {
                "conversation_id": "conv-3",
                "chat_id": 33,
                "record_id": 404,
                "action_type": "analysis",
                "result": {"analysis": "done"},
            },
        }

    def test_datasource_route_filters_sensitive_fields(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
            _ = session
            _ = ask_token
            return auth_user

        def fake_get_datasource_list(
            session: object, user: object
        ) -> list[_FakeDatasource]:
            _ = session
            _ = user
            return [
                _FakeDatasource(
                    id=1,
                    name="Sales DB",
                    type="pg",
                    embedding="secret",
                    table_relation=[{"a": 1}],
                    recommended_config=2,
                    configuration="sensitive",
                )
            ]

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(
            openclaw_router_module, "get_datasource_list", fake_get_datasource_list
        )

        response = test_app.post(
            "/api/v1/openclaw/datasources",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-4"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["operation"] == "datasource.list"
        item = payload["data"]["items"][0]
        assert item == {"id": 1, "name": "Sales DB", "type": "pg"}

    def test_question_route_timeout_returns_normalized_timeout_error(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
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
                    "chat_id": 222,
                    "reused": True,
                    "user_id": auth_user.id,
                    "workspace_id": auth_user.oid,
                    "datasource_id": bind_request.datasource_id,
                },
            )()

        async def fake_question_answer_inner(**kwargs: object) -> JSONResponse:
            _ = kwargs
            await asyncio.sleep(0.01)
            return JSONResponse({"late": True})

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)
        monkeypatch.setattr(
            openclaw_router_module, "question_answer_inner", fake_question_answer_inner
        )
        monkeypatch.setattr(settings, "OPENCLAW_REQUEST_TIMEOUT_SECONDS", 0.001)

        response = test_app.post(
            "/api/v1/openclaw/question",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-timeout", "question": "show sales"},
        )

        assert response.status_code == 504
        assert response.json() == {
            "version": "v1",
            "status": "error",
            "operation": "question.execute",
            "error_code": "EXECUTION_TIMEOUT",
            "message": "Operation exceeded 0.001 seconds",
            "detail": {"timeout_seconds": 0.001},
        }

    @pytest.mark.asyncio
    async def test_question_route_concurrency_limit_returns_normalized_error(
        self,
        async_client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        release = asyncio.Event()
        entered = asyncio.Event()

        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
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
                    "chat_id": 225,
                    "reused": True,
                    "user_id": auth_user.id,
                    "workspace_id": auth_user.oid,
                    "datasource_id": bind_request.datasource_id,
                },
            )()

        async def fake_question_answer_inner(**kwargs: object) -> JSONResponse:
            _ = kwargs
            entered.set()
            await release.wait()
            return JSONResponse({"record_id": 1})

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)
        monkeypatch.setattr(
            openclaw_router_module, "question_answer_inner", fake_question_answer_inner
        )
        monkeypatch.setattr(settings, "OPENCLAW_MAX_CONCURRENT_REQUESTS", 1)

        first_request = asyncio.create_task(
            async_client.post(
                "/api/v1/openclaw/question",
                headers=_openclaw_headers(),
                json={"conversation_id": "conv-a", "question": "show sales"},
            )
        )
        await entered.wait()

        second_response = await async_client.post(
            "/api/v1/openclaw/question",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-b", "question": "show profit"},
        )
        release.set()
        first_response = await first_request

        assert first_response.status_code == 200
        assert second_response.status_code == 429
        assert second_response.json() == {
            "version": "v1",
            "status": "error",
            "operation": "question.execute",
            "error_code": "CONCURRENCY_EXCEEDED",
            "message": "OpenClaw concurrency limit exceeded",
            "detail": {"max_concurrent_requests": 1},
        }

    def test_question_route_returns_disabled_error_when_feature_flag_off(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "OPENCLAW_ENABLED", False)

        response = test_app.post(
            "/api/v1/openclaw/question",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-off", "question": "show sales"},
        )

        assert response.status_code == 503
        assert response.json() == {
            "version": "v1",
            "status": "error",
            "operation": "question.execute",
            "error_code": "INTEGRATION_DISABLED",
            "message": "OpenClaw integration is disabled",
            "detail": None,
        }

    def test_question_route_unexpected_exception_returns_normalized_error(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
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
                    "chat_id": 223,
                    "reused": True,
                    "user_id": auth_user.id,
                    "workspace_id": auth_user.oid,
                    "datasource_id": bind_request.datasource_id,
                },
            )()

        async def fake_question_answer_inner(**kwargs: object) -> JSONResponse:
            _ = kwargs
            raise RuntimeError("OpenAI model unavailable")

        monkeypatch.setattr(
            openclaw_router_module,
            "authenticate_openclaw_service_token",
            fake_authenticate,
        )
        monkeypatch.setattr(openclaw_router_module, "bind_openclaw_session", fake_bind)
        monkeypatch.setattr(
            openclaw_router_module, "question_answer_inner", fake_question_answer_inner
        )

        response = test_app.post(
            "/api/v1/openclaw/question",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-llm", "question": "show sales"},
        )

        assert response.status_code == 500
        assert response.json() == {
            "version": "v1",
            "status": "error",
            "operation": "question.execute",
            "error_code": "LLM_FAILURE",
            "message": "OpenAI model unavailable",
            "detail": {"chat_id": None},
        }

    def test_question_route_upstream_error_response_is_machine_parseable(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        async def fake_authenticate(
            session: object, ask_token: str | None
        ) -> UserInfoDTO:
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
                    "chat_id": 224,
                    "reused": True,
                    "user_id": auth_user.id,
                    "workspace_id": auth_user.oid,
                    "datasource_id": bind_request.datasource_id,
                },
            )()

        async def fake_question_answer_inner(**kwargs: object) -> JSONResponse:
            _ = kwargs
            return JSONResponse(
                {"message": "Datasource not found", "source": "orchestrator"},
                status_code=404,
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

        response = test_app.post(
            "/api/v1/openclaw/question",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-ds", "question": "show sales"},
        )

        assert response.status_code == 404
        assert response.json() == {
            "version": "v1",
            "status": "error",
            "operation": "question.execute",
            "error_code": "DATASOURCE_NOT_FOUND",
            "message": "Datasource not found",
            "detail": {
                "upstream": {
                    "message": "Datasource not found",
                    "source": "orchestrator",
                },
                "chat_id": 224,
            },
        }

    def test_openclaw_validation_error_returns_openclaw_envelope(
        self,
        test_app: TestClient,
    ) -> None:
        response = test_app.post(
            "/api/v1/openclaw/question",
            headers=_openclaw_headers(),
            json={"conversation_id": "conv-invalid"},
        )

        assert response.status_code == 422
        payload = response.json()
        assert payload["version"] == "v1"
        assert payload["status"] == "error"
        assert payload["operation"] == "question.execute"
        assert payload["error_code"] == "VALIDATION_ERROR"
        assert payload["message"] == "Request validation failed"
        assert isinstance(payload["detail"]["errors"], list)
