from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast

import pytest

import apps.system.api.appearance as appearance_api
import apps.system.crud.parameter_manage as parameter_manage


class FakeUploadFile:
    def __init__(self, filename: str) -> None:
        self.filename = filename


class FakeFormData:
    def __init__(self, data: str, files: list[object]) -> None:
        self._data = data
        self._files = files

    def get(self, key: str) -> object | None:
        if key == "data":
            return self._data
        return None

    def getlist(self, key: str) -> list[object]:
        if key == "files":
            return self._files
        return []


class FakeRequest:
    def __init__(self, form_data: FakeFormData) -> None:
        self._form_data = form_data

    async def form(self) -> FakeFormData:
        return self._form_data


@pytest.mark.asyncio
async def test_save_appearance_args_persists_plain_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(parameter_manage, "get_sys_arg_model", lambda: SimpleNamespace)

    async def fake_get_appearance_args(_session: object) -> list[object]:
        return []

    monkeypatch.setattr(
        parameter_manage, "get_appearance_args", fake_get_appearance_args
    )

    async def fake_save_group_args(
        *, session: object, sys_args: list[object], file_mapping: dict[str, str] | None
    ) -> None:
        captured["session"] = session
        captured["sys_args"] = sys_args
        captured["file_mapping"] = file_mapping

    monkeypatch.setattr(
        parameter_manage, "compat_save_group_args", fake_save_group_args
    )

    request = FakeRequest(
        FakeFormData(
            data=json.dumps(
                [
                    {"pkey": "name", "pval": "mySQLBot", "ptype": "str", "sort": 1},
                    {"pkey": "showAbout", "pval": "0", "ptype": "str", "sort": 1},
                ]
            ),
            files=[],
        )
    )

    await parameter_manage.save_appearance_args(
        cast(Any, "session"), cast(Any, request)
    )

    assert captured["session"] == "session"
    assert captured["file_mapping"] is None
    assert [item.pkey for item in captured["sys_args"]] == ["name", "showAbout"]


@pytest.mark.asyncio
async def test_save_appearance_args_replaces_old_file_and_saves_new_file_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    deleted: list[str] = []

    monkeypatch.setattr(parameter_manage, "get_sys_arg_model", lambda: SimpleNamespace)

    async def fake_get_appearance_args(_session: object) -> list[object]:
        return [SimpleNamespace(pkey="web", ptype="file", pval="old-logo.png")]

    monkeypatch.setattr(
        parameter_manage, "get_appearance_args", fake_get_appearance_args
    )
    monkeypatch.setattr(parameter_manage, "UploadFile", FakeUploadFile)
    monkeypatch.setattr(parameter_manage, "check_file", lambda **_kwargs: None)
    monkeypatch.setattr(
        parameter_manage, "delete_file", lambda file_id: deleted.append(file_id)
    )

    async def fake_upload(_file: object) -> str:
        return "new-logo.png"

    monkeypatch.setattr(parameter_manage, "upload", fake_upload)

    async def fake_save_group_args(
        *, session: object, sys_args: list[object], file_mapping: dict[str, str] | None
    ) -> None:
        captured["sys_args"] = sys_args
        captured["file_mapping"] = file_mapping

    monkeypatch.setattr(
        parameter_manage, "compat_save_group_args", fake_save_group_args
    )

    request = FakeRequest(
        FakeFormData(
            data=json.dumps(
                [{"pkey": "web", "pval": "placeholder", "ptype": "file", "sort": 1}]
            ),
            files=[FakeUploadFile("logo.png,web")],
        )
    )

    await parameter_manage.save_appearance_args(
        cast(Any, "session"), cast(Any, request)
    )

    assert deleted == ["old-logo.png"]
    assert captured["file_mapping"] == {"web": "new-logo.png"}
    assert captured["sys_args"][0].pkey == "web"


@pytest.mark.asyncio
async def test_save_appearance_route_delegates_to_crud(
    test_app: Any, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def fake_save_appearance_args(_session: object, _request: object) -> None:
        calls.append("saved")

    monkeypatch.setattr(
        appearance_api, "save_appearance_args", fake_save_appearance_args
    )

    response = test_app.post(
        "/api/v1/system/appearance",
        headers=auth_headers,
        files={
            "data": (
                None,
                json.dumps(
                    [{"pkey": "name", "pval": "mySQLBot", "ptype": "str", "sort": 1}]
                ),
            )
        },
    )

    assert response.status_code == 200
    assert calls == ["saved"]
