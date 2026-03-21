import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

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
}


def classify_admin_api_group(path: str) -> str | None:
    for group, prefix in CRITICAL_ADMIN_PATHS:
        if path.startswith(prefix):
            return group
    return None


def _severity_for(status_code: int, latency_ms: int, group: str) -> str:
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "warning"
    if latency_ms >= LATENCY_THRESHOLDS_MS.get(group, 1500):
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
        payload: dict[str, Any] = {
            "event": "admin_api_observability",
            "group": group,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "severity": _severity_for(response.status_code, latency_ms, group),
            "alert_candidate": response.status_code >= 400
            or latency_ms >= LATENCY_THRESHOLDS_MS.get(group, 1500),
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
