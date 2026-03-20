from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from sqlmodel import Session

import apps.chat.api.custom_prompt as custom_prompt_api
from apps.chat.models.custom_prompt_model import CustomPrompt, CustomPromptTypeEnum


def test_custom_prompt_page_returns_paginated_shape(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    prompt = CustomPrompt(
        id=1,
        oid=1,
        type=CustomPromptTypeEnum.GENERATE_SQL,
        create_time=datetime.now(),
        name="sql prompt",
        prompt="be precise",
        specific_ds=False,
        datasource_ids=[],
    )
    monkeypatch.setattr(
        custom_prompt_api, "_list_prompts", lambda *args, **kwargs: [prompt]
    )
    monkeypatch.setattr(custom_prompt_api, "_datasource_name_map", lambda *_args: {})

    response = test_app.get(
        "/api/v1/system/custom_prompt/GENERATE_SQL/page/1/10", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_count"] == 1
    assert data["data"][0]["name"] == "sql prompt"


def test_custom_prompt_get_one_returns_prompt_payload(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    prompt = CustomPrompt(
        id=9,
        oid=1,
        type=CustomPromptTypeEnum.ANALYSIS,
        create_time=datetime.now(),
        name="analysis prompt",
        prompt="analyze carefully",
        specific_ds=True,
        datasource_ids=[11],
    )
    monkeypatch.setattr(Session, "get", lambda self, _model, _id: prompt)
    monkeypatch.setattr(
        custom_prompt_api, "_datasource_name_map", lambda *_args: {11: "ds-1"}
    )

    response = test_app.get("/api/v1/system/custom_prompt/9", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "analysis prompt"
    assert response.json()["data"]["datasource_names"] == ["ds-1"]


def test_custom_prompt_create_or_update_returns_new_id(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(self: Session, _model: object, _id: object) -> Any:
        return None

    def fake_add(self: Session, obj: Any) -> None:
        captured["obj"] = obj

    def fake_commit(self: Session) -> None:
        return None

    def fake_refresh(self: Session, obj: Any) -> None:
        obj.id = 12

    monkeypatch.setattr(Session, "get", fake_get)
    monkeypatch.setattr(Session, "add", fake_add)
    monkeypatch.setattr(Session, "commit", fake_commit)
    monkeypatch.setattr(Session, "refresh", fake_refresh)

    response = test_app.put(
        "/api/v1/system/custom_prompt",
        headers=auth_headers,
        json={
            "type": "PREDICT_DATA",
            "name": "predict",
            "prompt": "predict trend",
            "specific_ds": False,
            "datasource_ids": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == 12
    assert captured["obj"].name == "predict"


def test_custom_prompt_delete_removes_record(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    prompt = CustomPrompt(
        id=5,
        oid=1,
        type=CustomPromptTypeEnum.GENERATE_SQL,
        create_time=datetime.now(),
        name="to delete",
        prompt="delete me",
        specific_ds=False,
        datasource_ids=[],
    )
    deleted: list[int] = []

    monkeypatch.setattr(Session, "get", lambda self, _model, _id: prompt)
    monkeypatch.setattr(Session, "delete", lambda self, obj: deleted.append(obj.id))
    monkeypatch.setattr(Session, "commit", lambda self: None)

    response = test_app.request(
        "DELETE",
        "/api/v1/system/custom_prompt",
        headers=auth_headers,
        json=[5],
    )

    assert response.status_code == 200
    assert deleted == [5]


def test_custom_prompt_export_returns_excel_stream(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    prompt = CustomPrompt(
        id=1,
        oid=1,
        type=CustomPromptTypeEnum.GENERATE_SQL,
        create_time=datetime.now(),
        name="sql prompt",
        prompt="be precise",
        specific_ds=False,
        datasource_ids=[],
    )
    monkeypatch.setattr(
        custom_prompt_api, "_list_prompts", lambda *args, **kwargs: [prompt]
    )
    monkeypatch.setattr(custom_prompt_api, "_datasource_name_map", lambda *_args: {})

    response = test_app.get(
        "/api/v1/system/custom_prompt/GENERATE_SQL/export", headers=auth_headers
    )

    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.content[:2] == b"PK"
