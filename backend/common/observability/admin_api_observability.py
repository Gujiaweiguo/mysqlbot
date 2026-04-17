import json
import time
from collections.abc import Awaitable, Callable
from typing import Any, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from common.core.config import settings
from common.observability.openclaw_metrics import (
    OPENCLAW_MCP_REQUEST_DURATION,
    OPENCLAW_MCP_REQUESTS,
    OPENCLAW_REQUEST_DURATION,
    OPENCLAW_REQUESTS,
)
from common.utils.utils import SQLBotLogUtil

CRITICAL_ADMIN_PATHS: tuple[tuple[str, str], ...] = (
    ("auth", "/api/v1/system/authentication"),
    ("platform", "/api/v1/system/platform"),
    ("audit", "/api/v1/system/audit"),
    ("custom_prompt", "/api/v1/system/custom_prompt"),
    ("appearance", "/api/v1/system/appearance"),
    ("aimodel", "/api/v1/system/aimodel"),
    ("permission", "/api/v1/ds_permission"),
)

LATENCY_THRESHOLDS_MS: dict[str, int] = {
    "auth": 1200,
    "platform": 1200,
    "audit": 2000,
    "custom_prompt": 1200,
    "appearance": 1200,
    "aimodel": 2000,
    "permission": 1200,
    "openclaw": 5000,
}

OPENCLAW_PREFIX = f"{settings.API_V1_STR}/openclaw"


def classify_admin_api_group(path: str) -> str | None:
    if path.startswith(OPENCLAW_PREFIX):
        return "openclaw"
    for group, prefix in CRITICAL_ADMIN_PATHS:
        if path.startswith(prefix):
            return group
    return None


def _openclaw_latency_threshold_ms() -> int:
    return int(settings.OPENCLAW_REQUEST_TIMEOUT_SECONDS * 1000)


def _mcp_latency_threshold_ms(channel_path: str) -> int:
    if channel_path == "health":
        return 1000
    if channel_path == "mcp":
        return _openclaw_latency_threshold_ms()
    return 1500


def _openclaw_operation_for_path(path: str) -> str:
    if path.startswith(f"{OPENCLAW_PREFIX}/session/bind"):
        return "session.bind"
    if path.startswith(f"{OPENCLAW_PREFIX}/question"):
        return "question.execute"
    if path.startswith(f"{OPENCLAW_PREFIX}/analysis"):
        return "analysis.execute"
    if path.startswith(f"{OPENCLAW_PREFIX}/datasources"):
        return "datasource.list"
    return "unknown"


def _extract_openclaw_payload(response: Response) -> tuple[str, str] | None:
    if not hasattr(response, "body"):
        return None

    try:
        raw_payload = cast(object, json.loads(bytes(response.body).decode("utf-8")))
    except (TypeError, ValueError, AttributeError, UnicodeDecodeError):
        return None

    if not isinstance(raw_payload, dict):
        return None

    operation = raw_payload.get("operation")
    if not isinstance(operation, str):
        return None

    error_code = raw_payload.get("error_code")
    if not isinstance(error_code, str):
        error_code = "none"
    return operation, error_code


def classify_mcp_channel_path(path: str) -> str | None:
    if path == settings.MCP_HEALTH_PATH:
        return "health"
    if path == "/metrics":
        return "metrics"
    if path == settings.MCP_PATH or path.startswith(f"{settings.MCP_PATH}/"):
        return "mcp"
    return None


def _extract_json_payload(response: Response) -> dict[str, Any] | None:
    if not hasattr(response, "body"):
        return None

    try:
        raw_payload = cast(object, json.loads(bytes(response.body).decode("utf-8")))
    except (TypeError, ValueError, AttributeError, UnicodeDecodeError):
        return None

    if not isinstance(raw_payload, dict):
        return None
    return cast(dict[str, Any], raw_payload)


def _mcp_result_for_status(status_code: int) -> str:
    if status_code >= 500:
        return "server_error"
    if status_code >= 400:
        return "client_error"
    return "success"


def _mcp_severity_for(channel_path: str, status_code: int, latency_ms: int) -> str:
    threshold = _mcp_latency_threshold_ms(channel_path)
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "warning"
    if latency_ms >= threshold:
        return "warning"
    return "info"


def _severity_for(status_code: int, latency_ms: int, group: str) -> str:
    latency_threshold_ms = (
        _openclaw_latency_threshold_ms()
        if group == "openclaw"
        else LATENCY_THRESHOLDS_MS.get(group, 1500)
    )
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "warning"
    if latency_ms >= latency_threshold_ms:
        return "warning"
    return "info"


class AdminApiObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        group = classify_admin_api_group(request.url.path)
        if group is None:
            return await call_next(request)

        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - started) * 1000)
        current_user = getattr(request.state, "current_user", None)
        payload: dict[str, Any]
        latency_threshold_ms = (
            _openclaw_latency_threshold_ms()
            if group == "openclaw"
            else LATENCY_THRESHOLDS_MS.get(group, 1500)
        )
        if group == "openclaw":
            openclaw_payload = _extract_openclaw_payload(response)
            operation = _openclaw_operation_for_path(request.url.path)
            error_code = "none"
            if openclaw_payload is not None:
                operation, error_code = openclaw_payload
            OPENCLAW_REQUESTS.labels(
                operation=operation,
                status_code=str(response.status_code),
                error_code=error_code,
            ).inc()
            OPENCLAW_REQUEST_DURATION.labels(operation=operation).observe(
                latency_ms / 1000
            )
            payload = {
                "event": "openclaw_api_observability",
                "group": group,
                "operation": operation,
                "error_code": error_code,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "severity": _severity_for(response.status_code, latency_ms, group),
                "alert_candidate": response.status_code >= 400
                or latency_ms >= latency_threshold_ms,
                "user_id": getattr(current_user, "id", None),
                "user_name": getattr(current_user, "name", None),
                "oid": getattr(current_user, "oid", None),
            }
        else:
            payload = {
                "event": "admin_api_observability",
                "group": group,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "severity": _severity_for(response.status_code, latency_ms, group),
                "alert_candidate": response.status_code >= 400
                or latency_ms >= latency_threshold_ms,
                "user_id": getattr(current_user, "id", None),
                "user_name": getattr(current_user, "name", None),
                "oid": getattr(current_user, "oid", None),
            }
        log_line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if payload["severity"] == "error":
            SQLBotLogUtil.error(log_line, exc_info=False)
        elif payload["severity"] == "warning":
            SQLBotLogUtil.warning(log_line)
        else:
            SQLBotLogUtil.info(log_line)
        return response


class McpObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        channel_path = classify_mcp_channel_path(request.url.path)
        if channel_path is None:
            return await call_next(request)

        started = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - started) * 1000)
        result = _mcp_result_for_status(response.status_code)
        OPENCLAW_MCP_REQUESTS.labels(
            channel_path=channel_path,
            status_code=str(response.status_code),
            result=result,
        ).inc()
        OPENCLAW_MCP_REQUEST_DURATION.labels(channel_path=channel_path).observe(
            latency_ms / 1000
        )

        payload: dict[str, Any] = {
            "event": "openclaw_mcp_observability",
            "group": "openclaw_mcp",
            "channel_path": channel_path,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "result": result,
            "severity": _mcp_severity_for(
                channel_path,
                response.status_code,
                latency_ms,
            ),
            "alert_candidate": response.status_code >= 400
            or latency_ms >= _mcp_latency_threshold_ms(channel_path),
            "connection_failed": channel_path in {"mcp", "health"}
            and response.status_code >= 400,
            "capability_discovery_failed": channel_path == "mcp"
            and response.status_code >= 400,
        }

        if channel_path == "health":
            health_payload = _extract_json_payload(response)
            if health_payload is not None:
                issues = health_payload.get("issues")
                if isinstance(issues, list):
                    payload["issues"] = issues
                ready = health_payload.get("ready")
                if isinstance(ready, bool):
                    payload["ready"] = ready

        log_line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if payload["severity"] == "error":
            SQLBotLogUtil.error(log_line, exc_info=False)
        elif payload["severity"] == "warning":
            SQLBotLogUtil.warning(log_line)
        else:
            SQLBotLogUtil.info(log_line)
        return response
