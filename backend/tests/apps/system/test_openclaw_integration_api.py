from typing import Any

import pytest

from apps.system.schemas.system_schema import UserInfoDTO


class TestOpenClawIntegrationApi:
    def test_openclaw_mcp_config_contains_required_runtime_fields(
        self,
        test_app: Any,
        auth_headers: dict[str, str],
    ) -> None:
        response = test_app.get(
            "/api/v1/system/openclaw/mcp-config",
            headers=auth_headers,
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert set(payload) >= {
            "status",
            "service",
            "ready",
            "setup_enabled",
            "server_name",
            "bind_host",
            "port",
            "path",
            "base_url",
            "endpoint",
            "health_url",
            "auth_header",
            "auth_scheme",
            "operations",
            "tool_names",
            "issues",
        }

    def test_openclaw_mcp_config_returns_runtime_contract(
        self,
        test_app: Any,
        auth_headers: dict[str, str],
    ) -> None:
        response = test_app.get(
            "/api/v1/system/openclaw/mcp-config",
            headers=auth_headers,
        )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["service"] == "mcp"
        assert payload["server_name"] == "mysqlbot"
        assert payload["endpoint"] == "http://localhost:8001/mcp"
        assert payload["health_url"] == "http://localhost:8001/health"
        assert payload["auth_header"] == "X-SQLBOT-ASK-TOKEN"
        assert payload["auth_scheme"] == "sk"
        assert payload["operations"] == [
            "openclaw_session_bind",
            "openclaw_question_execute",
            "openclaw_analysis_execute",
            "openclaw_datasource_list",
        ]
        assert payload["tool_names"] == [
            "mysqlbot__openclaw_session_bind",
            "mysqlbot__openclaw_question_execute",
            "mysqlbot__openclaw_analysis_execute",
            "mysqlbot__openclaw_datasource_list",
        ]
        assert payload["ready"] is False
        assert payload["issues"] == ["MCP setup is disabled via SKIP_MCP_SETUP"]

    def test_openclaw_mcp_config_requires_admin_role(
        self,
        test_app: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from apps.system.middleware.auth import TokenMiddleware
        from apps.system.schemas import permission as permission_module
        from common.core.config import settings

        non_admin = UserInfoDTO(
            id=9,
            account="space-user",
            oid=1,
            name="Space User",
            email="space-user@example.com",
            status=1,
            origin=0,
            oid_list=[1],
            system_variables=[],
            language="en",
            weight=1,
            isAdmin=False,
        )

        async def fake_validate_token(
            self: TokenMiddleware, token: str | None, trans: object
        ) -> tuple[bool, UserInfoDTO]:
            _ = self
            _ = trans
            assert token == "Bearer test-token"
            return True, non_admin

        async def fake_get_ws_resource(oid: int, type: str) -> list[int]:
            _ = oid
            _ = type
            return list(range(1, 1000))

        monkeypatch.setattr(TokenMiddleware, "validateToken", fake_validate_token)
        monkeypatch.setattr(permission_module, "get_ws_resource", fake_get_ws_resource)

        response = test_app.get(
            "/api/v1/system/openclaw/mcp-config",
            headers={settings.TOKEN_KEY: "Bearer test-token"},
        )

        assert response.status_code == 500
        assert "Only administrators are allowed to call" in response.text


@pytest.mark.usefixtures("auth_headers")
def test_openclaw_mcp_config_reports_ready_when_mcp_setup_is_enabled(
    test_app: Any,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKIP_MCP_SETUP", raising=False)

    response = test_app.get(
        "/api/v1/system/openclaw/mcp-config",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["ready"] is True
    assert payload["issues"] == []
