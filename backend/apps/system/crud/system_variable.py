import datetime
from typing import Any

from fastapi import HTTPException
from sqlmodel import col, select
from sqlmodel import delete as sql_delete

from apps.system.models.system_variable_model import SystemVariable
from common.core.deps import CurrentUser, SessionDep, Trans
from common.core.pagination import Paginator
from common.core.schemas import PaginationParams


def save(
    session: SessionDep,
    user: CurrentUser,
    trans: Trans,
    variable: SystemVariable,
) -> bool:
    checkName(session, trans, variable)
    variable.type = "custom"
    if variable.id is None:
        variable.create_time = datetime.datetime.now()
        variable.create_by = user.id
        session.add(variable)
        session.commit()
    else:
        record = session.exec(
            select(SystemVariable).where(col(SystemVariable.id) == variable.id)
        ).first()
        if record is None:
            raise HTTPException(status_code=404, detail=trans("i18n_not_exist"))
        update_data = variable.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)
        session.add(record)
        session.commit()
    return True


def delete(session: SessionDep, ids: list[int]) -> None:
    if not ids:
        return
    stmt = sql_delete(SystemVariable).where(col(SystemVariable.id).in_(ids))
    session.exec(stmt)
    session.commit()


def list_all(
    session: SessionDep,
    trans: Trans,
    variable: SystemVariable | None = None,
) -> list[SystemVariable]:
    if variable is None or variable.name is None:
        stmt = select(SystemVariable).order_by(col(SystemVariable.type).desc())
    else:
        stmt = (
            select(SystemVariable)
            .where(
                col(SystemVariable.name).like(f"%{variable.name}%"),
                col(SystemVariable.type) != "system",
            )
            .order_by(col(SystemVariable.type).desc())
        )

    records = session.exec(stmt).all()

    res: list[SystemVariable] = []
    for r in records:
        data = SystemVariable.model_validate(r)
        if data.type == "system":
            data.name = trans(data.name)
        res.append(data)
    return res


async def list_page(
    session: SessionDep,
    trans: Trans,
    pageNum: int,
    pageSize: int,
    variable: SystemVariable | None = None,
) -> dict[str, Any]:
    pagination = PaginationParams(page=pageNum, size=pageSize)
    paginator = Paginator(session)
    filters: dict[str, Any] = {}

    if variable is None or variable.name is None:
        stmt = select(SystemVariable).order_by(col(SystemVariable.type).desc())
    else:
        stmt = (
            select(SystemVariable)
            .where(
                col(SystemVariable.name).like(f"%{variable.name}%"),
                col(SystemVariable.type) != "system",
            )
            .order_by(col(SystemVariable.type).desc())
        )

    variable_page = await paginator.get_paginated_response(
        stmt=stmt, pagination=pagination, **filters
    )

    res: list[SystemVariable] = []
    for r in variable_page.items:
        if isinstance(r, dict):
            data = SystemVariable.model_validate(r)
        else:
            data = SystemVariable.model_validate(r.model_dump())
        if data.type == "system":
            data.name = trans(data.name)
        res.append(data)

    return {
        "items": res,
        "page": variable_page.page,
        "size": variable_page.size,
        "total": variable_page.total,
        "total_pages": variable_page.total_pages,
    }


def checkName(session: SessionDep, trans: Trans, variable: SystemVariable) -> None:
    if variable.id is None:
        stmt = select(SystemVariable).where(col(SystemVariable.name) == variable.name)
    else:
        stmt = select(SystemVariable).where(
            col(SystemVariable.name) == variable.name,
            col(SystemVariable.id) != variable.id,
        )
    records = session.exec(stmt).all()
    if records:
        raise HTTPException(status_code=500, detail=trans("i18n_variable.name_exist"))


def checkValue(session: SessionDep, trans: Trans, values: list[Any]) -> None:
    # values: [{"variableId":1,"variableValues":["a","b"]}]
    pass
