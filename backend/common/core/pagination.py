from collections.abc import Sequence
from typing import Any, TypeVar, cast

from sqlalchemy import Select, func
from sqlalchemy.engine import Row
from sqlmodel import Session, SQLModel, select
from sqlmodel.sql.expression import SelectOfScalar

from common.core.schemas import PaginatedResponse, PaginationParams

ModelT = TypeVar("ModelT", bound=SQLModel)


class Paginator:
    def __init__(self, session: Session):
        self.session = session

    def _process_result_row(
        self, row: Row[Any] | SQLModel | int | Any
    ) -> dict[str, Any]:
        result_dict: dict[str, Any] = {}
        if isinstance(row, int):
            return {"id": row}
        if isinstance(row, SQLModel) and not hasattr(row, "_fields"):
            return row.model_dump()
        row_fields = getattr(row, "_fields", [])
        for item, key in zip(row, row_fields, strict=False):
            if isinstance(item, SQLModel):
                result_dict.update(item.model_dump())
            else:
                result_dict[str(key)] = item
        return result_dict

    async def paginate(
        self,
        stmt: Select[Any] | SelectOfScalar[Any] | type[ModelT],
        page: int = 1,
        size: int = 20,
        order_by: str | None = None,
        desc: bool = False,
        **filters: Any,
    ) -> tuple[list[Any], int]:
        offset = (page - 1) * size
        single_model = False
        if isinstance(stmt, type) and issubclass(stmt, SQLModel):
            stmt = select(stmt)
            single_model = True

        selected_stmt = stmt

        for field, value in filters.items():
            if value is None:
                continue
            selected_columns = getattr(selected_stmt, "selected_columns", None)
            if selected_columns is None:
                continue
            if "." in field:
                related_model, related_field = field.split(".")
                column = getattr(
                    getattr(selected_columns, related_model), related_field
                )
            else:
                column = getattr(selected_columns, field)
            selected_stmt = selected_stmt.where(column == value)

        if order_by:
            selected_columns = getattr(selected_stmt, "selected_columns", None)
            if selected_columns is not None:
                if "." in order_by:
                    related_model, related_field = order_by.split(".")
                    column = getattr(
                        getattr(selected_columns, related_model), related_field
                    )
                else:
                    column = getattr(selected_columns, order_by)
                selected_stmt = selected_stmt.order_by(
                    column.desc() if desc else column.asc()
                )

        count_stmt = select(func.count()).select_from(selected_stmt.subquery())
        total_result = self.session.exec(count_stmt)
        total_raw = total_result.first()
        if isinstance(total_raw, int):
            total = total_raw
        elif (
            isinstance(total_raw, Sequence)
            and len(total_raw) > 0
            and isinstance(total_raw[0], int)
        ):
            total = total_raw[0]
        else:
            total = 0

        selected_stmt = selected_stmt.offset(offset).limit(size)
        result = self.session.exec(cast(SelectOfScalar[Any], selected_stmt))
        if single_model:
            items = list(result.all())
        else:
            items = [self._process_result_row(row) for row in result]
        return items, total

    async def get_paginated_response(
        self,
        stmt: Select[Any] | SelectOfScalar[Any] | type[ModelT],
        pagination: PaginationParams,
        **filters: Any,
    ) -> PaginatedResponse[Any]:
        items, total = await self.paginate(
            stmt=stmt,
            page=pagination.page,
            size=pagination.size,
            order_by=pagination.order_by,
            desc=pagination.desc,
            **filters,
        )

        total_pages = (total + pagination.size - 1) // pagination.size

        return PaginatedResponse[Any](
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            total_pages=total_pages,
        )
