import pytest

from apps.system.schemas import permission as permission_module


@pytest.mark.asyncio
async def test_check_ws_permission_accepts_numeric_string_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_ws_resource(oid: int, type: str) -> list[int]:
        assert oid == 1
        assert type == "ds"
        return [2, 3, 4]

    monkeypatch.setattr(permission_module, "get_ws_resource", fake_get_ws_resource)

    assert await permission_module.check_ws_permission(1, "ds", "4") is True


@pytest.mark.asyncio
async def test_check_ws_permission_accepts_numeric_string_resource_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_ws_resource(oid: int, type: str) -> list[int]:
        assert oid == 1
        assert type == "ds"
        return [2, 3, 4]

    monkeypatch.setattr(permission_module, "get_ws_resource", fake_get_ws_resource)

    assert await permission_module.check_ws_permission(1, "ds", ["3", "4"]) is True


@pytest.mark.asyncio
async def test_check_ws_permission_keeps_rejecting_unknown_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_ws_resource(oid: int, type: str) -> list[int]:
        assert oid == 1
        assert type == "ds"
        return [2, 3, 4]

    monkeypatch.setattr(permission_module, "get_ws_resource", fake_get_ws_resource)

    assert await permission_module.check_ws_permission(1, "ds", "9") is False
