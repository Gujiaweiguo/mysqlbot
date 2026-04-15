import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import apps.mcp.mcp as mcp_module
from apps.chat.models.chat_model import (
    ChatFinishStep,
    ChatMcp,
    ChatQuestion,
    CreateChat,
)
from apps.system.schemas.system_schema import AssistantHeader, UserInfoDTO


class _FakeDatasource:
    _payload: dict[str, object]

    def __init__(self, **payload: object) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return dict(self._payload)


class _FakeUser:
    id: int
    account: str
    oid: int

    def __init__(self, *, user_id: int, account: str, oid: int) -> None:
        self.id = user_id
        self.account = account
        self.oid = oid


class TestMcpRouter:
    def test_mcp_start_returns_access_token_and_chat_id(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        def fake_authenticate(
            session: object, account: str, password: str
        ) -> _FakeUser:
            _ = session
            assert account == "demo-user"
            assert password == "demo-pass"
            return _FakeUser(user_id=auth_user.id, account=account, oid=auth_user.oid)

        def fake_get_user(session: object, token: str) -> UserInfoDTO:
            _ = session
            assert token == "signed-token"
            return auth_user

        def fake_create_access_token(*_args: object, **_kwargs: object) -> str:
            return "signed-token"

        def fake_create_chat(
            session: object,
            current_user: UserInfoDTO,
            create_chat_request: CreateChat,
            commit: bool,
        ) -> object:
            _ = session
            assert current_user.id == auth_user.id
            assert create_chat_request.origin == 1
            assert commit is False
            return type("Chat", (), {"id": 701})()

        monkeypatch.setattr(mcp_module, "authenticate", fake_authenticate)
        monkeypatch.setattr(mcp_module, "create_access_token", fake_create_access_token)
        monkeypatch.setattr(mcp_module, "get_user", fake_get_user)
        monkeypatch.setattr(mcp_module, "create_chat", fake_create_chat)

        response = test_app.post(
            "/api/v1/mcp/mcp_start",
            json={"username": "demo-user", "password": "demo-pass"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "code": 0,
            "data": {"access_token": "signed-token", "chat_id": 701},
            "msg": None,
        }

    def test_mcp_start_rejects_user_without_workspace(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fake_authenticate(
            session: object, account: str, password: str
        ) -> _FakeUser:
            _ = session
            _ = password
            return _FakeUser(user_id=8, account=account, oid=0)

        monkeypatch.setattr(mcp_module, "authenticate", fake_authenticate)

        response = test_app.post(
            "/api/v1/mcp/mcp_start",
            json={"username": "no-ws", "password": "demo-pass"},
        )

        assert response.status_code == 400
        assert (
            response.json()
            == "No associated workspace, Please contact the administrator"
        )

    def test_mcp_question_delegates_to_question_answer_inner(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        def fake_get_user(session: object, token: str) -> UserInfoDTO:
            _ = session
            assert token == "jwt-token"
            return auth_user

        async def fake_question_answer_inner(**kwargs: object) -> JSONResponse:
            request_question = kwargs["request_question"]
            assert isinstance(request_question, ChatMcp)
            assert request_question.chat_id == 31
            assert request_question.question == "show sales"
            assert request_question.datasource_id == 42
            assert request_question.token == "jwt-token"
            assert kwargs["current_user"] == auth_user
            assert kwargs["in_chat"] is False
            assert kwargs["stream"] is False
            return JSONResponse({"record_id": 99, "summary": "ok"})

        monkeypatch.setattr(mcp_module, "get_user", fake_get_user)
        monkeypatch.setattr(
            mcp_module, "question_answer_inner", fake_question_answer_inner
        )

        response = test_app.post(
            "/api/v1/mcp/mcp_question",
            json={
                "question": "show sales",
                "chat_id": 31,
                "token": "jwt-token",
                "stream": False,
                "datasource_id": "42",
            },
        )

        assert response.status_code == 200
        assert response.json() == {"record_id": 99, "summary": "ok"}

    def test_mcp_question_rejects_invalid_datasource_id(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        def fake_get_user(session: object, token: str) -> UserInfoDTO:
            _ = session
            _ = token
            return auth_user

        monkeypatch.setattr(mcp_module, "get_user", fake_get_user)

        response = test_app.post(
            "/api/v1/mcp/mcp_question",
            json={
                "question": "show sales",
                "chat_id": 31,
                "token": "jwt-token",
                "datasource_id": "forty-two",
            },
        )

        assert response.status_code == 400
        assert response.json() == "Invalid datasource ID"

    def test_mcp_datasource_list_filters_sensitive_fields(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        def fake_get_user(session: object, token: str) -> UserInfoDTO:
            _ = session
            assert token == "jwt-token"
            return auth_user

        def fake_get_datasource_list(
            session: object, user: UserInfoDTO
        ) -> list[_FakeDatasource]:
            _ = session
            assert user == auth_user
            return [
                _FakeDatasource(
                    id=1,
                    name="Sales DB",
                    type="pg",
                    embedding="secret",
                    table_relation=[{"a": 1}],
                    recommended_config={"top_k": 1},
                    configuration={"password": "sensitive"},
                )
            ]

        monkeypatch.setattr(mcp_module, "get_user", fake_get_user)
        monkeypatch.setattr(mcp_module, "get_datasource_list", fake_get_datasource_list)

        response = test_app.post(
            "/api/v1/mcp/mcp_ds_list", params={"token": "jwt-token"}
        )

        assert response.status_code == 200
        assert response.json() == {
            "code": 0,
            "data": [{"id": 1, "name": "Sales DB", "type": "pg"}],
            "msg": None,
        }

    def test_mcp_assistant_creates_chat_and_delegates(
        self,
        test_app: TestClient,
        monkeypatch: pytest.MonkeyPatch,
        auth_user: UserInfoDTO,
    ) -> None:
        def fake_get_assistant_user(id: int) -> UserInfoDTO:
            assert id == -1
            return auth_user

        def fake_create_chat(
            session: object,
            current_user: UserInfoDTO,
            create_chat_request: CreateChat,
            commit: bool,
        ) -> object:
            _ = session
            assert current_user == auth_user
            assert create_chat_request.origin == 1
            assert commit is False
            return type("Chat", (), {"id": 88})()

        async def fake_question_answer_inner(**kwargs: object) -> JSONResponse:
            request_question = kwargs["request_question"]
            current_assistant = kwargs["current_assistant"]
            assert isinstance(request_question, ChatQuestion)
            assert request_question.chat_id == 88
            assert request_question.question == "summarize orders"
            assert isinstance(current_assistant, AssistantHeader)
            assert current_assistant.certificate == "Bearer upstream"
            assert kwargs["current_user"] == auth_user
            assert kwargs["in_chat"] is False
            assert kwargs["stream"] is False
            assert kwargs["finish_step"] == ChatFinishStep.QUERY_DATA
            return JSONResponse({"summary": "assistant ok"})

        monkeypatch.setattr(mcp_module, "get_assistant_user", fake_get_assistant_user)
        monkeypatch.setattr(mcp_module, "create_chat", fake_create_chat)
        monkeypatch.setattr(
            mcp_module, "question_answer_inner", fake_question_answer_inner
        )

        response = test_app.post(
            "/api/v1/mcp/mcp_assistant",
            json={
                "question": "summarize orders",
                "url": "https://assistant.example.com/query",
                "authorization": "Bearer upstream",
                "stream": False,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"summary": "assistant ok"}
