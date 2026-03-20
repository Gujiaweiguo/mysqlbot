from __future__ import annotations

from typing import Any

import pytest

import apps.system.api.authentication as authentication_api


def test_list_authentication_returns_default_provider_statuses(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(authentication_api, "_get_auth_model", lambda *_args: None)

    response = test_app.get("/api/v1/system/authentication", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["name"] for item in data] == ["cas", "oidc", "ldap", "oauth2", "saml2"]
    assert all(item["enable"] is False for item in data)
    assert all(item["valid"] is False for item in data)


def test_get_authentication_uses_stored_provider_data(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    record = authentication_api.AuthenticationModel(
        name="oidc",
        type=2,
        config='{"client_id":"cid"}',
        enable=True,
        valid=True,
    )
    monkeypatch.setattr(authentication_api, "_get_auth_model", lambda *_args: record)

    response = test_app.get("/api/v1/system/authentication/2", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": 2,
        "type": 2,
        "name": "oidc",
        "config": '{"client_id":"cid"}',
        "valid": True,
        "enable": True,
    }


def test_create_authentication_returns_upserted_payload(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    created = authentication_api.AuthenticationModel(
        name="ldap",
        type=3,
        config='{"server_address":"ldap://server","bind_dn":"cn=admin","bind_pwd":"pwd","ou":"ou=users","user_filter":"(uid=%s)"}',
        enable=False,
        valid=True,
    )
    monkeypatch.setattr(
        authentication_api, "_upsert_auth_model", lambda *_args: created
    )

    response = test_app.post(
        "/api/v1/system/authentication",
        headers=auth_headers,
        json={
            "id": 3,
            "type": 3,
            "name": "ldap",
            "config": '{"server_address":"ldap://server","bind_dn":"cn=admin","bind_pwd":"pwd","ou":"ou=users","user_filter":"(uid=%s)"}',
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["type"] == 3
    assert response.json()["data"]["name"] == "ldap"
    assert response.json()["data"]["valid"] is True


def test_platform_status_uses_persisted_provider_enablement(
    test_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    enabled_ldap = authentication_api.AuthenticationModel(
        name="ldap",
        type=3,
        config="{}",
        enable=True,
        valid=True,
    )

    def fake_get_auth_model(_session: object, type_id: int) -> object | None:
        return enabled_ldap if type_id == 3 else None

    monkeypatch.setattr(authentication_api, "_get_auth_model", fake_get_auth_model)

    response = test_app.get("/api/v1/system/authentication/platform/status")

    assert response.status_code == 200
    login_status = {item["name"]: item for item in response.json()["data"]}
    assert login_status["ldap"]["enable"] is True
    assert login_status["ldap"]["valid"] is True
    assert login_status["cas"]["enable"] is False
