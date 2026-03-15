import pytest
from fastapi import HTTPException
from starlette.requests import Request

from common.core.config import settings
from common.core.schemas import XOAuth2PasswordBearer


def build_request(headers: list[tuple[bytes, bytes]]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": headers,
    }
    return Request(scope)


class TestXOAuth2PasswordBearer:
    @pytest.mark.asyncio
    async def test_returns_bearer_token(self) -> None:
        dependency = XOAuth2PasswordBearer(tokenUrl="/login", auto_error=False)
        request = build_request([(settings.TOKEN_KEY.lower().encode(), b"Bearer abc")])

        assert await dependency(request) == "abc"

    @pytest.mark.asyncio
    async def test_prefers_assistant_token(self) -> None:
        dependency = XOAuth2PasswordBearer(tokenUrl="/login", auto_error=False)
        request = build_request(
            [
                (settings.TOKEN_KEY.lower().encode(), b"Bearer abc"),
                (settings.ASSISTANT_TOKEN_KEY.lower().encode(), b"Assistant xyz"),
            ]
        )

        assert await dependency(request) == "xyz"

    @pytest.mark.asyncio
    async def test_returns_none_when_auto_error_disabled(self) -> None:
        dependency = XOAuth2PasswordBearer(tokenUrl="/login", auto_error=False)

        assert await dependency(build_request([])) is None

    @pytest.mark.asyncio
    async def test_raises_when_auto_error_enabled(self) -> None:
        dependency = XOAuth2PasswordBearer(tokenUrl="/login", auto_error=True)

        with pytest.raises(HTTPException) as exc_info:
            await dependency(build_request([]))

        assert exc_info.value.status_code == 401
