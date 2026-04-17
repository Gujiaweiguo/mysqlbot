import os

from apps.openclaw.contract import AUTH_HEADER, AUTH_SCHEME
from common.core.config import settings

OPENCLAW_MCP_SERVER_NAME = "mysqlbot"
OPENCLAW_MCP_OPERATION_IDS = (
    "openclaw_session_bind",
    "openclaw_question_execute",
    "openclaw_analysis_execute",
    "openclaw_datasource_list",
)


def openclaw_mcp_setup_enabled() -> bool:
    return os.getenv("SKIP_MCP_SETUP", "false").lower() not in {"1", "true", "yes"}


def build_openclaw_mcp_tool_names(
    server_name: str = OPENCLAW_MCP_SERVER_NAME,
) -> tuple[str, ...]:
    return tuple(
        f"{server_name}__{operation_id}" for operation_id in OPENCLAW_MCP_OPERATION_IDS
    )


def build_openclaw_mcp_issues() -> list[str]:
    issues: list[str] = []
    if not openclaw_mcp_setup_enabled():
        issues.append("MCP setup is disabled via SKIP_MCP_SETUP")
    if not settings.MCP_BASE_URL:
        issues.append("MCP base URL is empty")
    if not settings.MCP_ENDPOINT:
        issues.append("MCP endpoint is empty")
    return issues


def build_openclaw_mcp_runtime_contract() -> dict[str, object]:
    issues = build_openclaw_mcp_issues()
    setup_enabled = openclaw_mcp_setup_enabled()
    return {
        "status": "ok" if not issues else "degraded",
        "service": "mcp",
        "ready": not issues,
        "setup_enabled": setup_enabled,
        "server_name": OPENCLAW_MCP_SERVER_NAME,
        "bind_host": settings.MCP_BIND_HOST,
        "port": settings.MCP_PORT,
        "path": settings.MCP_PATH,
        "base_url": settings.MCP_BASE_URL,
        "endpoint": settings.MCP_ENDPOINT,
        "health_url": settings.MCP_HEALTH_URL,
        "auth_header": AUTH_HEADER,
        "auth_scheme": AUTH_SCHEME,
        "operations": list(OPENCLAW_MCP_OPERATION_IDS),
        "tool_names": list(build_openclaw_mcp_tool_names()),
        "issues": issues,
    }
