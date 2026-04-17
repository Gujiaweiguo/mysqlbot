"""Tests for main application endpoints."""

from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

import apps.openclaw.router as openclaw_router_module
from apps.openclaw.contract import OpenClawSessionBindRequest
from common.core.config import settings
from apps.system.schemas.system_schema import UserInfoDTO


class TestHealthEndpoint:
    """Tests for application health checks."""

    def test_app_created(self, test_app: TestClient) -> None:
        """Test that FastAPI app is created successfully."""
        assert test_app is not None

    def test_openapi_endpoint(self, test_app: TestClient) -> None:
        """Test that OpenAPI schema is accessible."""
        response = test_app.get("/openapi.json")
        assert response.status_code == 200
        data = cast(dict[str, object], response.json())
        assert "openapi" in data
        assert "paths" in data

    def test_openclaw_operation_ids_are_published_in_openapi(
        self, test_app: TestClient
    ) -> None:
        response = test_app.get("/openapi.json")
        assert response.status_code == 200

        payload = cast(dict[str, object], response.json())
        paths = cast(dict[str, object], payload["paths"])
        assert (
            cast(
                dict[str, object],
                cast(dict[str, object], paths["/api/v1/openclaw/session/bind"])["post"],
            )["operationId"]
            == "openclaw_session_bind"
        )
        assert (
            cast(
                dict[str, object],
                cast(dict[str, object], paths["/api/v1/openclaw/question"])["post"],
            )["operationId"]
            == "openclaw_question_execute"
        )
        assert (
            cast(
                dict[str, object],
                cast(dict[str, object], paths["/api/v1/openclaw/analysis"])["post"],
            )["operationId"]
            == "openclaw_analysis_execute"
        )
        assert (
            cast(
                dict[str, object],
                cast(dict[str, object], paths["/api/v1/openclaw/datasources"])["post"],
            )["operationId"]
            == "openclaw_datasource_list"
        )

    def test_openclaw_skill_artifact_exists(self) -> None:
        skill_path = (
            Path(__file__).resolve().parents[2]
            / ".openclaw"
            / "skills"
            / "mysqlbot-openclaw"
            / "SKILL.md"
        )
        assert skill_path.exists()
        skill_text = skill_path.read_text(encoding="utf-8")
        assert "mysqlbot__openclaw_question_execute" in skill_text
        assert "When not to call mysqlbot" in skill_text

    def test_canonical_mcp_discovery_is_limited_to_openclaw_contract(self) -> None:
        from main import OPENCLAW_MCP_OPERATION_IDS

        assert OPENCLAW_MCP_OPERATION_IDS == (
            "openclaw_session_bind",
            "openclaw_question_execute",
            "openclaw_analysis_execute",
            "openclaw_datasource_list",
        )
        assert "mcp_start" not in OPENCLAW_MCP_OPERATION_IDS
        assert "mcp_question" not in OPENCLAW_MCP_OPERATION_IDS
        assert "mcp_datasource_list" not in OPENCLAW_MCP_OPERATION_IDS

    def test_health_endpoint(self, test_app: TestClient) -> None:
        response = test_app.get("/health")
        assert response.status_code == 200
        assert response.json() == {"code": 0, "data": {"status": "ok"}, "msg": None}

    def test_mcp_contract_defaults_are_published(self) -> None:
        assert settings.MCP_BIND_HOST == "0.0.0.0"
        assert settings.MCP_PORT == 8001
        assert settings.MCP_PATH == "/mcp"
        assert settings.MCP_HEALTH_PATH == "/health"
        assert settings.MCP_ENDPOINT == "http://localhost:8001/mcp"
        assert settings.MCP_HEALTH_URL == "http://localhost:8001/health"

    def test_metrics_endpoint(self, test_app: TestClient) -> None:
        response = test_app.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        body = response.text
        assert "sqlbot_sync_jobs_submitted_total" in body
        assert "sqlbot_sync_job_total_duration_seconds" in body

    def test_metrics_endpoint_exposes_openclaw_metrics(
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
                    "chat_id": 501,
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

        openclaw_response = test_app.post(
            "/api/v1/openclaw/session/bind",
            headers={"X-SQLBOT-ASK-TOKEN": "sk test-token"},
            json={"conversation_id": "conv-metrics"},
        )
        assert openclaw_response.status_code == 200

        response = test_app.get("/metrics")
        assert response.status_code == 200
        body = response.text
        assert "sqlbot_openclaw_requests_total" in body
        assert "sqlbot_openclaw_request_duration_seconds" in body
        assert "sqlbot_openclaw_mcp_requests_total" in body
        assert "sqlbot_openclaw_mcp_request_duration_seconds" in body
