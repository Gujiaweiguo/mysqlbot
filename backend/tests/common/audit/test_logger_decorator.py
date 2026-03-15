from collections.abc import Awaitable, Callable
from typing import cast

from starlette.requests import Request

from apps.system.schemas.system_schema import UserInfoDTO
from common.audit.models.log_model import OperationType
from common.audit.schemas.logger_decorator import LogConfig, SystemLogger, system_log
from common.audit.schemas.request_context import RequestContext


def build_request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/audit",
        "query_string": b"page=1",
        "headers": [
            (b"user-agent", b"pytest"),
            (b"x-forwarded-for", b"1.2.3.4"),
            (b"authorization", b"secret"),
            (b"content-type", b"application/json"),
            (b"content-length", b"10"),
        ],
        "client": ("5.6.7.8", 1234),
        "path_params": {"item_id": "9"},
        "state": {},
    }
    return Request(scope)


class DummyObject:
    def __init__(self) -> None:
        self.user = {"items": [{"id": 7}]}


class TestSystemLoggerHelpers:
    def test_extract_value_from_object_handles_nested_paths(self) -> None:
        obj = DummyObject()

        assert SystemLogger.extract_value_from_object("user.items[0].id", obj) == 7
        assert SystemLogger.extract_value_from_object("result_self", obj) is obj
        assert SystemLogger.extract_value_from_object("missing.value", obj) is None

    def test_extract_resource_id_supports_args_kwargs_and_result(self) -> None:
        assert SystemLogger.extract_resource_id("args[0]", ("abc",), "args") == "abc"
        assert (
            SystemLogger.extract_resource_id("account", {"account": "demo"}, "kwargs")
            == "demo"
        )
        assert SystemLogger.extract_resource_id("id", {"id": 9}, "result") == 9

    def test_extract_from_function_params_falls_back_to_kwargs(self) -> None:
        result = SystemLogger.extract_from_function_params(
            "account",
            ("ignored",),
            {"account": "alice"},
        )

        assert result == "alice"

    def test_get_current_user_and_request_params(self) -> None:
        request = build_request()
        request.state.current_user = UserInfoDTO(
            id=1,
            account="admin",
            oid=1,
            name="Admin",
            email="admin@example.com",
            status=1,
            origin=0,
            oid_list=[1],
            system_variables=[],
            language="en",
            weight=0,
            isAdmin=True,
        )

        current_user = SystemLogger.get_current_user(request)
        params = SystemLogger.extract_request_params(request)
        client_info = SystemLogger.get_client_info(request)

        assert current_user is not None
        assert current_user.account == "admin"
        assert params is not None
        assert "authorization" not in params
        assert "page" in params
        assert client_info == {"ip_address": "1.2.3.4", "user_agent": "pytest"}


class TestSystemLogDecorator:
    async def test_async_wrapper_records_result_id(self, monkeypatch) -> None:
        captured: dict[str, object] = {}

        async def fake_create_log_record(**kwargs: object) -> None:
            captured.update(kwargs)

        monkeypatch.setattr(SystemLogger, "create_log_record", fake_create_log_record)
        monkeypatch.setattr(RequestContext, "get_request", staticmethod(lambda: None))

        @system_log(LogConfig(operation_type=OperationType.CREATE, result_id_expr="id"))
        async def create_item() -> dict[str, int]:
            return {"id": 99}

        create_item_callable = cast(
            Callable[[], Awaitable[dict[str, int]]], create_item
        )
        result = await create_item_callable()

        assert result == {"id": 99}
        assert captured["resource_id"] == 99
