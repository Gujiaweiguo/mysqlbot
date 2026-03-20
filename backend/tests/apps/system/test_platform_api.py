from __future__ import annotations

import importlib
from typing import Any

import pytest
from apps.system.models.system_model import AuthenticationModel

platform_api = importlib.import_module("apps.system.api.platform")


def test_list_platforms_returns_default_cards_when_unconfigured(
    test_app: Any,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform_api, "_get_auth_model", lambda *_args: None)

    response = test_app.get("/api/v1/system/platform", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["name"] for item in data] == ["wecom", "dingtalk", "lark", "larksuite"]
    assert all(item["config"] == "{}" for item in data)
    assert all(item["enable"] is False for item in data)


def test_list_platforms_uses_stored_platform_config(
    test_app: Any,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wecom = AuthenticationModel(
        name="wecom",
        type=6,
        config='{"corpid":"corp","agent_id":"1001","corpsecret":"secret"}',
        enable=True,
        valid=True,
    )

    def fake_get_auth_model(_session: object, type_id: int) -> object | None:
        return wecom if type_id == 6 else None

    monkeypatch.setattr(platform_api, "_get_auth_model", fake_get_auth_model)

    response = test_app.get("/api/v1/system/platform", headers=auth_headers)

    assert response.status_code == 200
    data = {item["name"]: item for item in response.json()["data"]}
    assert (
        data["wecom"]["config"]
        == '{"corpid":"corp","agent_id":"1001","corpsecret":"secret"}'
    )
    assert data["wecom"]["enable"] is True
    assert data["wecom"]["valid"] is True


def test_get_platform_client_returns_platform_config(
    test_app: Any,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dingtalk = AuthenticationModel(
        name="dingtalk",
        type=7,
        config='{"corpid":"corp","agent_id":"1001","client_id":"key","client_secret":"secret"}',
        enable=True,
        valid=True,
    )
    monkeypatch.setattr(
        platform_api,
        "_get_auth_model",
        lambda _session, type_id: dingtalk if type_id == 7 else None,
    )

    response = test_app.get("/api/v1/system/platform/client/7", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["client_id"] == "key"
