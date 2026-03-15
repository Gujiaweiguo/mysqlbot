from collections import namedtuple
from typing import Any, cast

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, SQLModel, Session, create_engine, select

from common.core.pagination import Paginator
from common.core.schemas import PaginationParams


class PaginationItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    category: str


def build_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine, tables=[cast(Any, PaginationItem).__table__])
    session = Session(engine)
    session.add_all(
        [
            PaginationItem(name="apple", category="fruit"),
            PaginationItem(name="banana", category="fruit"),
            PaginationItem(name="carrot", category="vegetable"),
        ]
    )
    session.commit()
    return session


class TestPaginator:
    def test_process_result_row_handles_int_and_model_and_row_like(self) -> None:
        session = build_session()
        paginator = Paginator(session)
        row_like = namedtuple("RowLike", ["name", "count"])("alice", 2)
        model = session.exec(select(PaginationItem)).first()

        assert paginator._process_result_row(7) == {"id": 7}
        assert model is not None
        assert paginator._process_result_row(model)["name"] in {
            "apple",
            "banana",
            "carrot",
        }
        assert paginator._process_result_row(row_like) == {"name": "alice", "count": 2}

        session.close()

    @pytest.mark.asyncio
    async def test_paginate_supports_model_filters_and_ordering(self) -> None:
        session = build_session()
        paginator = Paginator(session)

        items, total = await paginator.paginate(
            PaginationItem,
            page=1,
            size=2,
            order_by="name",
            desc=True,
            category="fruit",
        )

        assert total == 2
        assert [item.name for item in items] == ["banana", "apple"]

        session.close()

    @pytest.mark.asyncio
    async def test_paginate_supports_selected_columns(self) -> None:
        session = build_session()
        paginator = Paginator(session)

        items, total = await paginator.paginate(
            select(PaginationItem.id, PaginationItem.name),
            page=2,
            size=1,
            order_by="id",
        )

        assert total == 3
        assert items == [{"id": 2, "name": "banana"}]

        session.close()

    @pytest.mark.asyncio
    async def test_get_paginated_response_returns_metadata(self) -> None:
        session = build_session()
        paginator = Paginator(session)

        response = await paginator.get_paginated_response(
            PaginationItem,
            PaginationParams(page=1, size=2, order_by="id"),
        )

        assert response.total == 3
        assert response.page == 1
        assert response.size == 2
        assert response.total_pages == 2
        assert len(response.items) == 2

        session.close()
