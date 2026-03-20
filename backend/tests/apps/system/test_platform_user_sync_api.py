from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from apps.system.api.platform import PlatformSyncPayload, sync_platform_users
from apps.system.models.system_model import UserWsModel
from apps.system.models.user import UserModel, UserPlatformModel
from apps.system.schemas.system_schema import UserInfoDTO


class _ExecResult:
    def __init__(self, value: Any):
        self._value = value

    def first(self) -> Any:
        return self._value


class FakeSession:
    def __init__(self) -> None:
        self.user_by_platform: dict[tuple[int, str], UserPlatformModel] = {}
        self.user_by_id: dict[int, UserModel] = {}
        self.user_ws_by_pair: dict[tuple[int, int], UserWsModel] = {}
        self.added: list[Any] = []
        self.next_user_id = 100

    def exec(self, _stmt: object) -> _ExecResult:
        raise AssertionError("exec() should be monkeypatched per test")

    def get(self, model: type[Any], key: int) -> Any:
        if model is UserModel:
            return self.user_by_id.get(key)
        return None

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        if isinstance(obj, UserModel) and obj.id is None:
            obj.id = self.next_user_id
            self.next_user_id += 1
            self.user_by_id[obj.id] = obj
        elif isinstance(obj, UserModel) and obj.id is not None:
            self.user_by_id[obj.id] = obj
        elif isinstance(obj, UserPlatformModel):
            self.user_by_platform[(obj.origin, obj.platform_uid)] = obj
        elif isinstance(obj, UserWsModel):
            self.user_ws_by_pair[(obj.uid, obj.oid)] = obj

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_platform_user_sync_skips_creation_when_auto_create_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    monkeypatch.setattr(
        "apps.system.api.platform._parameter_defaults",
        lambda _session: {
            "platform.auto_create": "false",
            "platform.oid": "1",
            "platform.rid": "0",
        },
    )
    monkeypatch.setattr(
        session,
        "exec",
        lambda _stmt: _ExecResult(None),
    )

    result = await sync_platform_users(
        PlatformSyncPayload(
            origin=6,
            cover=False,
            user_list=[{"id": "u-1", "name": "Alice", "email": "alice@example.com"}],
        ),
        cast(Any, session),
        cast(UserInfoDTO, cast(Any, SimpleNamespace())),
    )

    assert result.successCount == 0
    assert result.errorCount == 1


@pytest.mark.asyncio
async def test_platform_user_sync_creates_user_with_default_workspace_and_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    monkeypatch.setattr(
        "apps.system.api.platform._parameter_defaults",
        lambda _session: {
            "platform.auto_create": "true",
            "platform.oid": "1",
            "platform.rid": "0",
        },
    )
    monkeypatch.setattr(session, "exec", lambda _stmt: _ExecResult(None))

    result = await sync_platform_users(
        PlatformSyncPayload(
            origin=7,
            cover=False,
            user_list=[{"id": "u-2", "name": "Bob", "email": "bob@example.com"}],
        ),
        cast(Any, session),
        cast(UserInfoDTO, cast(Any, SimpleNamespace())),
    )

    assert result.successCount == 1
    assert result.errorCount == 0
    created_user = next(obj for obj in session.added if isinstance(obj, UserModel))
    assert created_user.account == "platform_7_u-2"
    assert created_user.oid == 1
    assert created_user.origin == 7
    created_link = next(
        obj for obj in session.added if isinstance(obj, UserPlatformModel)
    )
    assert created_link.platform_uid == "u-2"
    created_ws = next(obj for obj in session.added if isinstance(obj, UserWsModel))
    assert created_ws.oid == 1
    assert created_ws.weight == 0


@pytest.mark.asyncio
async def test_platform_user_sync_cover_updates_existing_user_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    existing_user = UserModel(
        id=42,
        account="platform_8_u-3",
        oid=2,
        name="Old Name",
        password="pwd",
        email="old@example.com",
        status=1,
        origin=8,
        language="zh-CN",
    )
    existing_platform = UserPlatformModel(uid=42, origin=8, platform_uid="u-3")
    existing_ws = UserWsModel(uid=42, oid=1, weight=1)
    session.user_by_id[42] = existing_user
    session.user_by_platform[(8, "u-3")] = existing_platform
    session.user_ws_by_pair[(42, 1)] = existing_ws

    def fake_exec(_stmt: object) -> _ExecResult:
        class _StatementText(str):
            pass

        text = str(_stmt)
        if "sys_user_platform" in text:
            return _ExecResult(existing_platform)
        if "sys_user_ws" in text:
            return _ExecResult(existing_ws)
        return _ExecResult(None)

    monkeypatch.setattr(
        "apps.system.api.platform._parameter_defaults",
        lambda _session: {
            "platform.auto_create": "true",
            "platform.oid": "1",
            "platform.rid": "0",
        },
    )
    monkeypatch.setattr(session, "exec", fake_exec)

    result = await sync_platform_users(
        PlatformSyncPayload(
            origin=8,
            cover=True,
            user_list=[{"id": "u-3", "name": "New Name", "email": "new@example.com"}],
        ),
        cast(Any, session),
        cast(UserInfoDTO, cast(Any, SimpleNamespace())),
    )

    assert result.successCount == 1
    assert result.errorCount == 0
    assert existing_user.name == "New Name"
    assert existing_user.email == "new@example.com"
    assert existing_user.oid == 1
    assert existing_ws.weight == 0
