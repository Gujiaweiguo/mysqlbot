from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

import apps.audit.api.audit_api as audit_api
from common.audit.models.log_model import OperationType


def test_audit_get_options_returns_operation_types(
    test_app: Any, auth_headers: dict[str, str]
) -> None:
    response = test_app.get("/api/v1/system/audit/get_options", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    ids = {item["id"] for item in data}
    assert OperationType.LOGIN.value in ids
    assert OperationType.CREATE.value in ids


def test_audit_page_returns_paginated_shape(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeExecResult:
        def all(self) -> list[Any]:
            return [
                SimpleNamespace(
                    id=1,
                    operation_type="login",
                    operation_detail="login by admin",
                    user_id=1,
                    user_name="Administrator",
                    operation_status="success",
                    create_time=datetime.now(),
                    oid=1,
                    error_message="",
                    remark="",
                    resource_name="Administrator",
                )
            ]

    monkeypatch.setattr(audit_api, "_base_query", lambda: "base-query")
    monkeypatch.setattr(audit_api, "_apply_filters", lambda query, **_kwargs: query)
    monkeypatch.setattr(
        "sqlmodel.orm.session.Session.exec", lambda self, _query: FakeExecResult()
    )

    response = test_app.get("/api/v1/system/audit/page/1/10", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "data" in data
    assert "total_count" in data
    assert isinstance(data["data"], list)
    assert isinstance(data["total_count"], int)
