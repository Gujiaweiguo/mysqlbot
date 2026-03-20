from __future__ import annotations

from typing import Any

import pytest

import apps.system.api.appearance as appearance_api


def test_get_appearance_ui_returns_public_bootstrap_args(
    test_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_get_appearance_args(_session: object) -> list[dict[str, object]]:
        return [
            {"pkey": "themeColor", "pval": "blue", "ptype": "str", "sort_no": 1},
            {"pkey": "navigateBg", "pval": "dark", "ptype": "str", "sort_no": 1},
            {"pkey": "name", "pval": "mySQLBot", "ptype": "str", "sort_no": 1},
        ]

    monkeypatch.setattr(appearance_api, "get_appearance_args", fake_get_appearance_args)

    response = test_app.get("/api/v1/system/appearance/ui")

    assert response.status_code == 200
    assert response.json()["data"] == [
        {"pkey": "themeColor", "pval": "blue", "ptype": "str", "sort_no": 1},
        {"pkey": "navigateBg", "pval": "dark", "ptype": "str", "sort_no": 1},
        {"pkey": "name", "pval": "mySQLBot", "ptype": "str", "sort_no": 1},
    ]
