import base64
from typing import cast

import jwt
from fastapi.responses import Response
from starlette.requests import Request

from apps.system.middleware.auth import TokenMiddleware, xor_decrypt
from common.core.config import settings
from apps.system.schemas.system_schema import UserInfoDTO
from common.utils.locale import I18nHelper


class DummyTrans:
    lang = "en"

    def __call__(self, key: str, **kwargs: object) -> str:
        msg = kwargs.get("msg", "")
        return f"{key}:{msg}"


async def noop_app(scope: object, receive: object, send: object) -> None:
    _ = scope
    _ = receive
    _ = send


def xor_encrypt(value: int, key: int = 0xABCD1234) -> str:
    encrypted_num = value ^ key
    hex_str = format(encrypted_num, "x")
    if len(hex_str) % 2:
        hex_str = f"0{hex_str}"
    return base64.urlsafe_b64encode(bytes.fromhex(hex_str)).decode()


def make_user_info() -> UserInfoDTO:
    return UserInfoDTO(
        id=1,
        account="demo",
        oid=1,
        name="Demo",
        email="demo@example.com",
        status=1,
        origin=0,
        oid_list=[1],
        system_variables=[],
        language="en",
        weight=0,
        isAdmin=False,
    )


class DummySessionContext:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = exc_type
        _ = exc
        _ = tb


def build_request(
    path: str = "/private", headers: list[tuple[bytes, bytes]] | None = None
) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"",
        "headers": headers or [],
        "state": {},
    }
    return Request(scope)


class TestTokenMiddleware:
    async def test_validate_token_rejects_missing_token(self) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        valid, message = await middleware.validateToken(None, trans)

        assert valid is False
        assert "Miss Token" in str(message)

    async def test_validate_token_rejects_wrong_schema(self) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        valid, message = await middleware.validateToken("Basic abc", trans)

        assert valid is False
        assert message == "Token schema error!"

    async def test_validate_token_maps_expired_errors(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        def fake_decode(*args: object, **kwargs: object) -> dict[str, object]:
            _ = args
            _ = kwargs
            raise Exception("expired token")

        monkeypatch.setattr("apps.system.middleware.auth.jwt.decode", fake_decode)

        valid, message = await middleware.validateToken("Bearer token", trans)

        assert valid is False
        assert isinstance(message, jwt.ExpiredSignatureError)

    async def test_validate_ask_token_handles_missing_access_key(
        self, monkeypatch
    ) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {},
        )

        valid, message = await middleware.validateAskToken("sk token", trans)

        assert valid is False
        assert message == "Miss access_key payload error!"

    async def test_validate_assistant_rejects_wrong_schema(self) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        valid, message, assistant = await middleware.validateAssistant(
            "Bearer token", trans
        )

        assert valid is False
        assert "Token schema error!" in str(message)
        assert assistant is None

    async def test_validate_embedded_rejects_missing_account(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"appId": "demo", "embeddedId": 1, "account": ""},
        )

        valid, message, assistant = await middleware.validateEmbedded("token", trans)

        assert valid is False
        assert "Miss account payload error!" in str(message)
        assert assistant is None

    async def test_validate_embedded_rejects_missing_app_secret(
        self, monkeypatch
    ) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {
                "appId": "demo",
                "embeddedId": 2,
                "account": "demo",
            },
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_assistant_info(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "id": 2,
                "name": "Assistant",
                "type": 1,
                "domain": "demo",
                "configuration": "{}",
                "description": None,
                "create_time": 0,
                "app_id": None,
                "app_secret": None,
                "oid": 1,
            }

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_assistant_info", fake_get_assistant_info
        )

        valid, message, assistant = await middleware.validateEmbedded("token", trans)

        assert valid is False
        assert "Missing app secret" in str(message)
        assert assistant is None

    async def test_validate_embedded_rejects_missing_account_user(
        self, monkeypatch
    ) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        decode_calls = iter(
            [
                {"appId": "demo", "embeddedId": 2, "account": "demo"},
                {"sub": "ok"},
            ]
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: next(decode_calls),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_assistant_info(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "id": 2,
                "name": "Assistant",
                "type": 1,
                "domain": "demo",
                "configuration": "{}",
                "description": None,
                "create_time": 0,
                "app_id": None,
                "app_secret": "secret",
                "oid": 1,
            }

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_assistant_info", fake_get_assistant_info
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_by_account",
            lambda *args, **kwargs: None,
        )

        valid, message, assistant = await middleware.validateEmbedded("token", trans)

        assert valid is False
        assert "i18n_not_exist" in str(message)
        assert assistant is None

    async def test_validate_embedded_accepts_valid_token(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        decode_calls = iter(
            [
                {"appId": xor_encrypt(2), "account": "demo"},
                {"sub": "ok"},
            ]
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: next(decode_calls),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_assistant_info(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "id": 2,
                "name": "Assistant",
                "type": 1,
                "domain": "demo",
                "configuration": "{}",
                "description": None,
                "create_time": 0,
                "app_id": None,
                "app_secret": "secret",
                "oid": 1,
            }

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return make_user_info()

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_assistant_info", fake_get_assistant_info
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_by_account",
            lambda *args, **kwargs: type("AccountUser", (), {"id": 1})(),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, user, assistant = await middleware.validateEmbedded("token", trans)

        assert valid is True
        assert isinstance(user, UserInfoDTO)
        assert assistant is not None
        assert assistant.oid == 1

    async def test_validate_token_accepts_valid_user(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"id": 1},
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return make_user_info()

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, user = await middleware.validateToken("Bearer token", trans)

        assert valid is True
        assert isinstance(user, UserInfoDTO)
        assert user.account == "demo"

    async def test_validate_token_rejects_missing_user_id(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"id": None},
        )

        valid, message = await middleware.validateToken("Bearer token", trans)

        assert valid is False
        assert message == "Miss user id payload error!"

    async def test_validate_token_rejects_missing_user(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"id": 1},
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_user_info(*args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs
            return None

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, message = await middleware.validateToken("Bearer token", trans)

        assert valid is False
        assert "i18n_not_exist" in str(message)

    async def test_validate_token_rejects_disabled_user(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        disabled_user = make_user_info().model_copy(update={"status": 0})

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"id": 1},
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return disabled_user

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, message = await middleware.validateToken("Bearer token", trans)

        assert valid is False
        assert "i18n_login.user_disable" in str(message)

    async def test_validate_token_rejects_user_without_workspace(
        self, monkeypatch
    ) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        no_workspace_user = make_user_info().model_copy(update={"oid": 0})

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"id": 1},
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return no_workspace_user

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, message = await middleware.validateToken("Bearer token", trans)

        assert valid is False
        assert "i18n_login.no_associated_ws" in str(message)

    async def test_validate_ask_token_rejects_disabled_key(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"access_key": "k"},
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_api_key(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "access_key": "k",
                "secret_key": "secret",
                "uid": 1,
                "status": False,
                "create_time": 0,
            }

        monkeypatch.setattr("apps.system.middleware.auth.get_api_key", fake_get_api_key)

        valid, message = await middleware.validateAskToken("sk token", trans)

        assert valid is False
        assert message == "Disabled access_key!"

    async def test_validate_ask_token_accepts_valid_key(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        decode_calls = iter([{"access_key": "k"}, {"sub": "ok"}])

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: next(decode_calls),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_api_key(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "access_key": "k",
                "secret_key": "secret",
                "uid": 1,
                "status": True,
                "create_time": 0,
            }

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return make_user_info()

        monkeypatch.setattr("apps.system.middleware.auth.get_api_key", fake_get_api_key)
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, user = await middleware.validateAskToken("sk token", trans)

        assert valid is True
        assert isinstance(user, UserInfoDTO)

    async def test_validate_ask_token_rejects_missing_user(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        decode_calls = iter([{"access_key": "k"}, {"sub": "ok"}])

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: next(decode_calls),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_api_key(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "access_key": "k",
                "secret_key": "secret",
                "uid": 1,
                "status": True,
                "create_time": 0,
            }

        async def fake_get_user_info(*args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs
            return None

        monkeypatch.setattr("apps.system.middleware.auth.get_api_key", fake_get_api_key)
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, message = await middleware.validateAskToken("sk token", trans)

        assert valid is False
        assert "i18n_not_exist" in str(message)

    async def test_validate_ask_token_rejects_disabled_user(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        decode_calls = iter([{"access_key": "k"}, {"sub": "ok"}])
        disabled_user = make_user_info().model_copy(update={"status": 0})

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: next(decode_calls),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_api_key(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "access_key": "k",
                "secret_key": "secret",
                "uid": 1,
                "status": True,
                "create_time": 0,
            }

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return disabled_user

        monkeypatch.setattr("apps.system.middleware.auth.get_api_key", fake_get_api_key)
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, message = await middleware.validateAskToken("sk token", trans)

        assert valid is False
        assert "i18n_login.user_disable" in str(message)

    async def test_validate_ask_token_rejects_user_without_workspace(
        self, monkeypatch
    ) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        decode_calls = iter([{"access_key": "k"}, {"sub": "ok"}])
        no_workspace_user = make_user_info().model_copy(update={"oid": 0})

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: next(decode_calls),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_api_key(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "access_key": "k",
                "secret_key": "secret",
                "uid": 1,
                "status": True,
                "create_time": 0,
            }

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return no_workspace_user

        monkeypatch.setattr("apps.system.middleware.auth.get_api_key", fake_get_api_key)
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, message = await middleware.validateAskToken("sk token", trans)

        assert valid is False
        assert "i18n_login.no_associated_ws" in str(message)

    async def test_validate_assistant_accepts_valid_token(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"id": 1, "assistant_id": 2},
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_assistant_user",
            lambda id: make_user_info(),
        )

        async def fake_get_assistant_info(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "id": 2,
                "name": "Assistant",
                "type": 1,
                "domain": "demo",
                "configuration": "{}",
                "description": None,
                "create_time": 0,
                "app_id": None,
                "app_secret": None,
                "oid": 1,
            }

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_assistant_info", fake_get_assistant_info
        )

        valid, user, assistant = await middleware.validateAssistant(
            "Assistant token", trans
        )

        assert valid is True
        assert isinstance(user, UserInfoDTO)
        assert assistant is not None
        assert assistant.name == "Assistant"

    async def test_validate_assistant_rejects_missing_assistant_payload(
        self, monkeypatch
    ) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"id": 1, "assistant_id": None},
        )

        valid, message, assistant = await middleware.validateAssistant(
            "Assistant token", trans
        )

        assert valid is False
        assert "Miss assistant payload error!" in str(message)
        assert assistant is None

    async def test_validate_assistant_rejects_missing_token(self) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        valid, message, assistant = await middleware.validateAssistant(None, trans)

        assert valid is False
        assert "Miss Token" in str(message)
        assert assistant is None

    async def test_validate_assistant_uses_embedded_schema(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        async def fake_validate_embedded(
            param: str, _trans: I18nHelper
        ) -> tuple[bool, object, object | None]:
            assert param == "token"
            return True, make_user_info(), None

        monkeypatch.setattr(middleware, "validateEmbedded", fake_validate_embedded)

        valid, user, assistant = await middleware.validateAssistant(
            "Embedded token", trans
        )

        assert valid is True
        assert isinstance(user, UserInfoDTO)
        assert assistant is None

    async def test_validate_assistant_rejects_missing_user_id(
        self, monkeypatch
    ) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))

        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: {"id": None, "assistant_id": 2},
        )

        valid, message, assistant = await middleware.validateAssistant(
            "Assistant token", trans
        )

        assert valid is False
        assert "Miss user id payload error!" in str(message)
        assert assistant is None

    async def test_validate_embedded_rejects_disabled_user(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        decode_calls = iter(
            [
                {"appId": "demo", "embeddedId": 2, "account": "demo"},
                {"sub": "ok"},
            ]
        )
        disabled_user = make_user_info().model_copy(update={"status": 0})
        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: next(decode_calls),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_assistant_info(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "id": 2,
                "name": "Assistant",
                "type": 1,
                "domain": "demo",
                "configuration": "{}",
                "description": None,
                "create_time": 0,
                "app_id": None,
                "app_secret": "secret",
                "oid": 1,
            }

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return disabled_user

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_assistant_info", fake_get_assistant_info
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_by_account",
            lambda *args, **kwargs: type("AccountUser", (), {"id": 1})(),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, message, assistant = await middleware.validateEmbedded("token", trans)

        assert valid is False
        assert "i18n_login.user_disable" in str(message)
        assert assistant is None

    async def test_validate_embedded_rejects_user_without_workspace(
        self, monkeypatch
    ) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        decode_calls = iter(
            [
                {"appId": "demo", "embeddedId": 2, "account": "demo"},
                {"sub": "ok"},
            ]
        )
        no_workspace_user = make_user_info().model_copy(update={"oid": 0})
        monkeypatch.setattr(
            "apps.system.middleware.auth.jwt.decode",
            lambda *args, **kwargs: next(decode_calls),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.Session",
            lambda _engine: DummySessionContext(),
        )

        async def fake_get_assistant_info(
            *args: object, **kwargs: object
        ) -> dict[str, object]:
            _ = args
            _ = kwargs
            return {
                "id": 2,
                "name": "Assistant",
                "type": 1,
                "domain": "demo",
                "configuration": "{}",
                "description": None,
                "create_time": 0,
                "app_id": None,
                "app_secret": "secret",
                "oid": 1,
            }

        async def fake_get_user_info(*args: object, **kwargs: object) -> UserInfoDTO:
            _ = args
            _ = kwargs
            return no_workspace_user

        monkeypatch.setattr(
            "apps.system.middleware.auth.get_assistant_info", fake_get_assistant_info
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_by_account",
            lambda *args, **kwargs: type("AccountUser", (), {"id": 1})(),
        )
        monkeypatch.setattr(
            "apps.system.middleware.auth.get_user_info", fake_get_user_info
        )

        valid, message, assistant = await middleware.validateEmbedded("token", trans)

        assert valid is False
        assert "i18n_login.no_associated_ws" in str(message)
        assert assistant is None

    async def test_dispatch_allows_whitelisted_path(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        request = build_request(path="/openapi.json")

        monkeypatch.setattr(
            "apps.system.middleware.auth.whiteUtils.is_whitelisted",
            lambda path: path == "/openapi.json",
        )

        async def call_next(_request: Request) -> Response:
            return Response("ok", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    async def test_dispatch_uses_ask_token_success_path(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        request = build_request(headers=[(b"x-sqlbot-ask-token", b"sk token")])

        monkeypatch.setattr(
            "apps.system.middleware.auth.whiteUtils.is_whitelisted", lambda path: False
        )

        async def fake_get_i18n(_request: Request) -> I18nHelper:
            return trans

        async def fake_validate_ask_token(
            _token: str, _trans: I18nHelper
        ) -> tuple[bool, object]:
            return True, make_user_info()

        monkeypatch.setattr("apps.system.middleware.auth.get_i18n", fake_get_i18n)
        monkeypatch.setattr(middleware, "validateAskToken", fake_validate_ask_token)

        async def call_next(_request: Request) -> Response:
            return Response("ok", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        assert request.state.current_user.account == "demo"

    async def test_dispatch_returns_401_for_failed_ask_token(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        request = build_request(headers=[(b"x-sqlbot-ask-token", b"sk token")])

        monkeypatch.setattr(
            "apps.system.middleware.auth.whiteUtils.is_whitelisted", lambda path: False
        )

        async def fake_get_i18n(_request: Request) -> I18nHelper:
            return trans

        async def fake_validate_ask_token(
            _token: str, _trans: I18nHelper
        ) -> tuple[bool, object]:
            return False, "bad token"

        monkeypatch.setattr("apps.system.middleware.auth.get_i18n", fake_get_i18n)
        monkeypatch.setattr(middleware, "validateAskToken", fake_validate_ask_token)

        async def call_next(_request: Request) -> Response:
            return Response("ok", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 401

    async def test_dispatch_uses_bearer_success_path(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        request = build_request(
            headers=[(settings.TOKEN_KEY.lower().encode(), b"Bearer token")]
        )

        monkeypatch.setattr(
            "apps.system.middleware.auth.whiteUtils.is_whitelisted", lambda path: False
        )

        async def fake_get_i18n(_request: Request) -> I18nHelper:
            return trans

        async def fake_validate_token(
            _token: str | None, _trans: I18nHelper
        ) -> tuple[bool, object]:
            return True, make_user_info()

        monkeypatch.setattr("apps.system.middleware.auth.get_i18n", fake_get_i18n)
        monkeypatch.setattr(middleware, "validateToken", fake_validate_token)

        async def call_next(_request: Request) -> Response:
            return Response("ok", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        assert request.state.current_user.account == "demo"

    async def test_dispatch_uses_assistant_success_path(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        request = build_request(
            headers=[
                (settings.ASSISTANT_TOKEN_KEY.lower().encode(), b"Assistant token")
            ]
        )

        monkeypatch.setattr(
            "apps.system.middleware.auth.whiteUtils.is_whitelisted", lambda path: False
        )

        async def fake_get_i18n(_request: Request) -> I18nHelper:
            return trans

        async def fake_validate_assistant(
            _token: str | None, _trans: I18nHelper
        ) -> tuple[bool, object, object | None]:
            return (
                True,
                make_user_info(),
                type("Assistant", (), {"request_origin": None})(),
            )

        monkeypatch.setattr("apps.system.middleware.auth.get_i18n", fake_get_i18n)
        monkeypatch.setattr(middleware, "validateAssistant", fake_validate_assistant)

        async def call_next(_request: Request) -> Response:
            return Response("ok", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        assert request.state.current_user.account == "demo"

    async def test_dispatch_returns_401_for_failed_assistant(self, monkeypatch) -> None:
        middleware = TokenMiddleware(noop_app)
        trans = cast(I18nHelper, cast(object, DummyTrans()))
        request = build_request(
            headers=[
                (settings.ASSISTANT_TOKEN_KEY.lower().encode(), b"Assistant token")
            ]
        )

        monkeypatch.setattr(
            "apps.system.middleware.auth.whiteUtils.is_whitelisted", lambda path: False
        )

        async def fake_get_i18n(_request: Request) -> I18nHelper:
            return trans

        async def fake_validate_assistant(
            _token: str | None, _trans: I18nHelper
        ) -> tuple[bool, object, object | None]:
            return False, "bad assistant", None

        monkeypatch.setattr("apps.system.middleware.auth.get_i18n", fake_get_i18n)
        monkeypatch.setattr(middleware, "validateAssistant", fake_validate_assistant)

        async def call_next(_request: Request) -> Response:
            return Response("ok", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 401

    def test_xor_decrypt_round_trip(self) -> None:
        original = 123456
        encrypted = xor_encrypt(original)

        assert xor_decrypt(encrypted) == original
