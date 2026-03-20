from __future__ import annotations

from typing import Any, cast

import pytest

import apps.system.api.parameter as parameter_api


def test_get_parameter_args_includes_platform_and_login_settings(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_get_parameter_args(_session: object) -> list[dict[str, object]]:
        return [
            {
                "pkey": "platform.auto_create",
                "pval": "true",
                "ptype": "str",
                "sort_no": 1,
            },
            {"pkey": "platform.oid", "pval": "1", "ptype": "str", "sort_no": 1},
            {"pkey": "platform.rid", "pval": "0", "ptype": "str", "sort_no": 1},
            {"pkey": "login.default_login", "pval": "3", "ptype": "str", "sort_no": 1},
        ]

    monkeypatch.setattr(parameter_api, "get_parameter_args", fake_get_parameter_args)

    response = test_app.get("/api/v1/system/parameter", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert {item["pkey"] for item in data} == {
        "platform.auto_create",
        "platform.oid",
        "platform.rid",
        "login.default_login",
    }


def test_save_parameter_args_accepts_platform_and_login_settings(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    async def fake_save_parameter_args(*, session: object, request: object) -> None:
        _ = session
        form = await cast(Any, request).form()
        captured["data"] = form.get("data")

    monkeypatch.setattr(parameter_api, "save_parameter_args", fake_save_parameter_args)

    response = test_app.post(
        "/api/v1/system/parameter",
        headers=auth_headers,
        files={
            "data": (
                None,
                '[{"pkey":"platform.auto_create","pval":"true"},'
                '{"pkey":"platform.oid","pval":"1"},'
                '{"pkey":"platform.rid","pval":"0"},'
                '{"pkey":"login.default_login","pval":"3"}]',
            )
        },
    )

    assert response.status_code == 200
    assert "platform.auto_create" in captured["data"]
    assert "login.default_login" in captured["data"]
