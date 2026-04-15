import json
from collections.abc import Awaitable, Callable

from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from common.core.config import settings
from common.utils.utils import SQLBotLogUtil


class ResponseMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        direct_paths = [
            f"{settings.API_V1_STR}/mcp/mcp_question",
            f"{settings.API_V1_STR}/mcp/mcp_assistant",
            "/openapi.json",
            "/docs",
            "/redoc",
        ]

        route = request.scope.get("route")
        # 获取定义的路径模式，例如 '/items/{item_id}'
        path_pattern = "" if route is None else str(getattr(route, "path_format", ""))

        if (
            isinstance(response, JSONResponse)
            or request.url.path == f"{settings.API_V1_STR}/openapi.json"
            or path_pattern in direct_paths
            or request.url.path.startswith(f"{settings.API_V1_STR}/openclaw")
        ):
            return response
        if response.status_code != 200:
            return response
        if response.headers.get("content-type") == "application/json":
            try:
                body = b""
                body_iterator = getattr(response, "body_iterator", None)
                if body_iterator is None:
                    return response

                async for chunk in body_iterator:
                    body += chunk

                raw_data = json.loads(body.decode())

                if isinstance(raw_data, dict) and all(
                    k in raw_data for k in ["code", "data", "msg"]
                ):
                    return JSONResponse(
                        content=raw_data,
                        status_code=response.status_code,
                        headers={
                            k: v
                            for k, v in response.headers.items()
                            if k.lower() not in ("content-length", "content-type")
                        },
                    )

                wrapped_data = {
                    "code": 0,
                    "data": raw_data,
                    "msg": None,
                }

                return JSONResponse(
                    content=wrapped_data,
                    status_code=response.status_code,
                    headers={
                        k: v
                        for k, v in response.headers.items()
                        if k.lower() not in ("content-length", "content-type")
                    },
                )
            except Exception as e:
                SQLBotLogUtil.error(
                    f"Response processing error: {str(e)}", exc_info=True
                )
                return JSONResponse(
                    status_code=500,
                    content=str(e),
                    headers={
                        k: v
                        for k, v in response.headers.items()
                        if k.lower() not in ("content-length", "content-type")
                    },
                )

        return response


class exception_handler:
    @staticmethod
    async def http_exception_handler(
        _request: Request, exc: HTTPException
    ) -> JSONResponse:
        SQLBotLogUtil.error(f"HTTP Exception: {exc.detail}", exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers={"Access-Control-Allow-Origin": "*"},
        )

    @staticmethod
    async def global_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        SQLBotLogUtil.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=str(exc),
            headers={"Access-Control-Allow-Origin": "*"},
        )
