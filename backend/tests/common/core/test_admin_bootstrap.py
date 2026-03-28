from __future__ import annotations

from apps.system.models.user import UserModel
from apps.system.crud.user import (
    LEGACY_ADMIN_PASSWORD_HASH,
    sync_default_admin_password,
)
from common.core.security import default_md5_pwd, md5pwd


class FakeSession:
    user: UserModel | None
    commits: int

    def __init__(self, user: UserModel | None) -> None:
        self.user = user
        self.added: list[object] = []
        self.commits = 0

    def get(self, _entity: type[UserModel], _ident: int) -> UserModel | None:
        return self.user

    def add(self, instance: object, _warn: bool = True) -> None:
        self.added.append(instance)

    def commit(self) -> None:
        self.commits += 1


def _build_admin(password: str) -> UserModel:
    return UserModel(
        id=1,
        account="admin",
        oid=1,
        name="Administrator",
        password=password,
        email="fit2cloud.com",
        status=1,
        origin=0,
        language="zh-CN",
    )


def test_sync_default_admin_password_updates_legacy_seed() -> None:
    admin_user = _build_admin(LEGACY_ADMIN_PASSWORD_HASH)
    session = FakeSession(admin_user)

    updated = sync_default_admin_password(session=session)

    assert updated is True
    assert admin_user.password == default_md5_pwd()
    assert session.added == [admin_user]
    assert session.commits == 1


def test_sync_default_admin_password_keeps_custom_password() -> None:
    admin_user = _build_admin(md5pwd("CustomPassword1!"))
    session = FakeSession(admin_user)

    updated = sync_default_admin_password(session=session)

    assert updated is False
    assert admin_user.password == md5pwd("CustomPassword1!")
    assert session.added == []
    assert session.commits == 0


def test_sync_default_admin_password_skips_missing_admin() -> None:
    session = FakeSession(None)

    updated = sync_default_admin_password(session=session)

    assert updated is False
    assert session.added == []
    assert session.commits == 0
