from collections import defaultdict
from typing import Any

from sqlmodel import Session, col, select, update

from apps.system.models.system_model import UserWsModel
from apps.system.models.user import UserModel


async def reset_single_user_oid(
    session: Session,
    uid: int,
    oid: int,
    add: bool | None = True,
) -> None:
    user_model = session.get(UserModel, uid)
    if not user_model:
        return
    origin_oid = user_model.oid
    if add and (not origin_oid or origin_oid == 0):
        user_model.oid = oid
        session.add(user_model)
    if not add and origin_oid and origin_oid == oid:
        user_model.oid = 0
        user_ws = session.exec(
            select(UserWsModel).where(UserWsModel.uid == uid, UserWsModel.oid != oid)
        ).first()
        if user_ws:
            user_model.oid = user_ws.oid
        session.add(user_model)


async def reset_user_oid(session: Session, oid: int) -> None:
    stmt: Any = (
        select(
            col(UserModel.id),
            col(UserModel.oid),
            col(UserWsModel.oid).label("associated_oid"),
        )
        .join(UserWsModel, col(UserModel.id) == col(UserWsModel.uid), isouter=True)
        .where(col(UserModel.id) != 1)
    )

    user_filter = (
        select(col(UserModel.id))
        .join(UserWsModel, col(UserModel.id) == col(UserWsModel.uid))
        .where(col(UserWsModel.oid) == oid)
        .distinct()
    )
    stmt = stmt.where(col(UserModel.id).in_(user_filter))

    result_user_list = session.exec(stmt).all()
    if not result_user_list:
        return

    merged: defaultdict[int, list[int | None]] = defaultdict(list)
    extra_attrs: dict[int, int | None] = {}

    for id, oid, associated_oid in result_user_list:
        if not isinstance(id, int):
            continue
        merged[id].append(associated_oid)
        extra_attrs.setdefault(id, oid)

    for user_id, values in merged.items():
        origin_oid = extra_attrs.get(user_id)
        oid_list: list[int] = [
            value for value in values if isinstance(value, int) and value != oid
        ]
        if origin_oid not in oid_list:
            new_oid = oid_list[0] if oid_list else 0
            if new_oid != origin_oid:
                update_stmt = (
                    update(UserModel)
                    .where(col(UserModel.id) == user_id)
                    .values(oid=new_oid)
                )
                session.exec(update_stmt)
