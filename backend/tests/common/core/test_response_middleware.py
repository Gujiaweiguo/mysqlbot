import json
from collections.abc import AsyncIterator

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from common.core.response_middleware import ResponseMiddleware, exception_handler


async def noop_app(scope: object, receive: object, send: object) -> None:
    _ = scope
    _ = receive
    _ = send


def build_request(path: str = "/items", path_format: str = "/items") -> Request:
    route = type("Route", (), {"path_format": path_format})()
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": [],
        "route": route,
    }
    return Request(scope)


class TestResponseMiddleware:
    @pytest.mark.asyncio
    async def test_returns_json_response_directly(self) -> None:
        middleware = ResponseMiddleware(noop_app)
        request = build_request()

        async def call_next(_request: Request) -> Response:
            return JSONResponse({"ok": True})

        response = await middleware.dispatch(request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_wraps_plain_json_payload(self) -> None:
        middleware = ResponseMiddleware(noop_app)
        request = build_request("/other", "/other")

        async def iterator() -> AsyncIterator[bytes]:
            yield json.dumps({"hello": "world"}).encode()

        async def call_next(_request: Request) -> Response:
            return StreamingResponse(iterator(), media_type="application/json")

        response = await middleware.dispatch(request, call_next)

        assert isinstance(response, JSONResponse)
        assert json.loads(bytes(response.body)) == {
            "code": 0,
            "data": {"hello": "world"},
            "msg": None,
        }

    @pytest.mark.asyncio
    async def test_keeps_already_wrapped_payload(self) -> None:
        middleware = ResponseMiddleware(noop_app)
        request = build_request("/other", "/other")

        async def iterator() -> AsyncIterator[bytes]:
            yield json.dumps({"code": 0, "data": [], "msg": None}).encode()

        async def call_next(_request: Request) -> Response:
            return StreamingResponse(iterator(), media_type="application/json")

        response = await middleware.dispatch(request, call_next)

        assert isinstance(response, JSONResponse)
        assert json.loads(bytes(response.body)) == {"code": 0, "data": [], "msg": None}

    @pytest.mark.asyncio
    async def test_returns_500_when_json_body_is_invalid(self) -> None:
        middleware = ResponseMiddleware(noop_app)
        request = build_request("/other", "/other")

        async def iterator() -> AsyncIterator[bytes]:
            yield b"not-json"

        async def call_next(_request: Request) -> Response:
            return StreamingResponse(iterator(), media_type="application/json")

        response = await middleware.dispatch(request, call_next)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_returns_original_response_when_body_iterator_missing(self) -> None:
        middleware = ResponseMiddleware(noop_app)
        request = build_request("/other", "/other")

        async def call_next(_request: Request) -> Response:
            return Response('{"ok": true}', media_type="application/json")

        response = await middleware.dispatch(request, call_next)

        assert isinstance(response, Response)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_original_response_for_non_json_content(self) -> None:
        middleware = ResponseMiddleware(noop_app)
        request = build_request("/other", "/other")

        async def call_next(_request: Request) -> Response:
            return Response("plain text", media_type="text/plain")

        response = await middleware.dispatch(request, call_next)

        assert isinstance(response, Response)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_exception_handlers_return_json_responses(self) -> None:
        request = build_request()

        http_response = await exception_handler.http_exception_handler(
            request,
            HTTPException(status_code=418, detail="boom"),
        )
        global_response = await exception_handler.global_exception_handler(
            request,
            Exception("boom"),
        )

        assert isinstance(http_response, JSONResponse)
        assert global_response.status_code == 500
