from __future__ import annotations

import json
from typing import Any

import pytest

import apps.system.api.authentication as authentication_api
from common.observability.admin_api_observability import classify_admin_api_group
from common.utils.utils import SQLBotLogUtil


def test_classify_admin_api_group_matches_critical_paths() -> None:
    assert classify_admin_api_group("/api/v1/system/authentication") == "auth"
    assert classify_admin_api_group("/api/v1/system/platform/client/6") == "platform"
    assert classify_admin_api_group("/api/v1/system/audit/page/1/10") == "audit"
    assert (
        classify_admin_api_group("/api/v1/system/custom_prompt/GENERATE_SQL/page/1/10")
        == "custom_prompt"
    )
    assert classify_admin_api_group("/api/v1/system/appearance") == "appearance"
    assert classify_admin_api_group("/api/v1/system/aimodel/status") == "aimodel"
    assert classify_admin_api_group("/api/v1/ds_permission/list") == "permission"
    assert classify_admin_api_group("/api/v1/workspace") is None


def test_observability_logs_success_for_monitored_admin_endpoint(
    test_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[dict[str, Any]] = []

    monkeypatch.setattr(
        SQLBotLogUtil,
        "info",
        staticmethod(lambda msg, *args, **kwargs: captured.append(json.loads(msg))),
    )
    monkeypatch.setattr(
        SQLBotLogUtil, "warning", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(
        SQLBotLogUtil, "error", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(authentication_api, "_get_auth_model", lambda *_args: None)

    response = test_app.get("/api/v1/system/authentication/platform/status")

    assert response.status_code == 200
    assert captured
    assert captured[-1]["group"] == "auth"
    assert captured[-1]["status_code"] == 200
    assert captured[-1]["severity"] == "info"


def test_observability_logs_warning_for_failed_admin_endpoint(
    test_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[dict[str, Any]] = []

    monkeypatch.setattr(
        SQLBotLogUtil, "info", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(
        SQLBotLogUtil,
        "warning",
        staticmethod(lambda msg, *args, **kwargs: captured.append(json.loads(msg))),
    )
    monkeypatch.setattr(
        SQLBotLogUtil, "error", staticmethod(lambda *args, **kwargs: None)
    )

    response = test_app.get("/api/v1/system/platform")

    assert response.status_code == 401
    assert captured
    assert captured[-1]["group"] == "platform"
    assert captured[-1]["status_code"] == 401
    assert captured[-1]["severity"] == "warning"
