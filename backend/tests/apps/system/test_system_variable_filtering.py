from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

import apps.system.crud.system_variable as system_variable_crud
from apps.system.models.system_variable_model import SystemVariable
from common.core.deps import SessionDep, Trans


def _make_variable(
    *, name: str, var_type: str, type_: str, value: list[Any]
) -> SystemVariable:
    return SystemVariable(
        id=1,
        name=name,
        var_type=var_type,
        type=type_,
        value=value,
        create_time=None,
        create_by=None,
    )


def test_list_all_hides_internal_embedding_variable() -> None:
    records = [
        _make_variable(
            name="i18n_variable.name", var_type="text", type_="system", value=["name"]
        ),
        _make_variable(
            name="embedding_admin_config",
            var_type="embedding",
            type_="system",
            value=[{}],
        ),
        _make_variable(
            name="custom_threshold", var_type="number", type_="custom", value=[1, 100]
        ),
    ]

    class FakeSession:
        def exec(self, _stmt: object) -> Any:
            return SimpleNamespace(all=lambda: records)

    result = system_variable_crud.list_all(
        cast(SessionDep, cast(Any, SimpleNamespace(exec=FakeSession().exec))),
        cast(
            Trans, cast(Any, (lambda key: {"i18n_variable.name": "姓名"}.get(key, key)))
        ),
        None,
    )

    assert [item.name for item in result] == ["姓名", "custom_threshold"]


@pytest.mark.asyncio
async def test_list_page_hides_internal_embedding_variable() -> None:
    items = [
        _make_variable(
            name="i18n_variable.email", var_type="text", type_="system", value=["email"]
        ),
        _make_variable(
            name="embedding_admin_config",
            var_type="embedding",
            type_="system",
            value=[{}],
        ),
    ]

    class FakePaginator:
        def __init__(self, _session: object) -> None:
            pass

        async def get_paginated_response(self, **_kwargs: Any) -> Any:
            return SimpleNamespace(items=items, page=1, size=10, total=2, total_pages=1)

    original_paginator = system_variable_crud.Paginator
    system_variable_crud.Paginator = FakePaginator  # type: ignore[assignment]
    try:
        result = await system_variable_crud.list_page(
            cast(SessionDep, cast(Any, SimpleNamespace())),
            cast(
                Trans,
                cast(Any, (lambda key: {"i18n_variable.email": "邮箱"}.get(key, key))),
            ),
            1,
            10,
            None,
        )
    finally:
        system_variable_crud.Paginator = original_paginator  # type: ignore[assignment]

    assert [item.name for item in result["items"]] == ["邮箱"]
    assert result["total"] == 1
