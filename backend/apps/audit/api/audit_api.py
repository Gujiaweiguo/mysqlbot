from collections.abc import Sequence
from datetime import datetime
from io import BytesIO
from typing import Any, cast

import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlmodel import col, select

from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.audit.models.log_model import OperationStatus, OperationType, SystemLog
from common.audit.schemas.log_utils import build_resource_union_query
from common.core.deps import CurrentUser, SessionDep

router = APIRouter(tags=["Audit"], prefix="/system/audit")


def _parse_multi_values(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item for item in raw.split("__") if item]


def _base_query() -> Any:
    resource_union = build_resource_union_query().subquery()
    select_any = cast(Any, select)
    query = (
        select_any(
            cast(Any, SystemLog.id),
            cast(Any, SystemLog.operation_type),
            cast(Any, SystemLog.operation_detail),
            cast(Any, SystemLog.user_id),
            cast(Any, SystemLog.user_name),
            cast(Any, SystemLog.operation_status),
            cast(Any, SystemLog.create_time),
            cast(Any, SystemLog.oid),
            cast(Any, SystemLog.error_message),
            cast(Any, SystemLog.remark),
            cast(Any, resource_union.c.name.label("resource_name")),
        )
        .select_from(SystemLog)
        .join(
            resource_union,
            (col(SystemLog.resource_id) == resource_union.c.id)
            & (col(SystemLog.module) == resource_union.c.module),
            isouter=True,
        )
        .order_by(col(SystemLog.create_time).desc())
    )
    return cast(Any, query)


def _apply_filters(
    query: Any,
    *,
    name: str | None,
    opt_type_list: str | None,
    uid_list: str | None,
    oid_list: str | None,
    log_status: str | None,
    time_range: str | None,
) -> Any:
    if name:
        query = query.where(col(SystemLog.operation_detail).contains(name))
    opt_types = _parse_multi_values(opt_type_list)
    if opt_types:
        query = query.where(col(SystemLog.operation_type).in_(opt_types))
    uids = [int(item) for item in _parse_multi_values(uid_list) if item.isdigit()]
    if uids:
        query = query.where(col(SystemLog.user_id).in_(uids))
    oids = [int(item) for item in _parse_multi_values(oid_list) if item.isdigit()]
    if oids:
        query = query.where(col(SystemLog.oid).in_(oids))
    statuses = _parse_multi_values(log_status)
    if statuses:
        query = query.where(col(SystemLog.operation_status).in_(statuses))
    range_values = _parse_multi_values(time_range)
    if len(range_values) == 2 and all(item.isdigit() for item in range_values):
        start = datetime.fromtimestamp(int(range_values[0]) / 1000)
        end = datetime.fromtimestamp(int(range_values[1]) / 1000)
        query = query.where(
            col(SystemLog.create_time) >= start,
            col(SystemLog.create_time) <= end,
        )
    return query


def _format_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    operation_type_name = {
        item.value: item.value.replace("_", " ").title() for item in OperationType
    }
    status_name = {
        OperationStatus.SUCCESS.value: "success",
        OperationStatus.FAILED.value: "failed",
    }
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "id": row.id,
                "operation_type_name": operation_type_name.get(
                    row.operation_type, row.operation_type
                ),
                "operation_detail_info": row.operation_detail or "",
                "user_name": row.user_name or "",
                "resource_name": row.resource_name or "",
                "operation_status": row.operation_status or "",
                "operation_status_name": status_name.get(
                    row.operation_status or "", row.operation_status or ""
                ),
                "create_time": row.create_time.isoformat() if row.create_time else "",
                "oid": str(row.oid or -1),
                "oid_name": str(row.oid or -1),
                "error_message": row.error_message or "",
                "remark": row.remark or "",
            }
        )
    return result


@router.get("/page/{page_num}/{page_size}")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def page(
    session: SessionDep,
    _current_user: CurrentUser,
    page_num: int,
    page_size: int,
    name: str | None = Query(default=None),
    opt_type_list: str | None = Query(default=None),
    uid_list: str | None = Query(default=None),
    oid_list: str | None = Query(default=None),
    log_status: str | None = Query(default=None),
    time_range: str | None = Query(default=None),
) -> dict[str, Any]:
    query = _apply_filters(
        _base_query(),
        name=name,
        opt_type_list=opt_type_list,
        uid_list=uid_list,
        oid_list=oid_list,
        log_status=log_status,
        time_range=time_range,
    )
    rows = list(session.exec(query).all())
    total_count = len(rows)
    start = max(page_num - 1, 0) * page_size
    end = start + page_size
    return {"data": _format_rows(rows[start:end]), "total_count": total_count}


@router.get("/get_options")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def get_options(_current_user: CurrentUser) -> list[dict[str, Any]]:
    return [
        {
            "id": item.value,
            "name": item.value.replace("_", " ").title(),
        }
        for item in OperationType
    ]


@router.get("/export")
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def export(
    session: SessionDep,
    _current_user: CurrentUser,
    name: str | None = Query(default=None),
    opt_type_list: str | None = Query(default=None),
    uid_list: str | None = Query(default=None),
    oid_list: str | None = Query(default=None),
    log_status: str | None = Query(default=None),
    time_range: str | None = Query(default=None),
) -> StreamingResponse:
    query = _apply_filters(
        _base_query(),
        name=name,
        opt_type_list=opt_type_list,
        uid_list=uid_list,
        oid_list=oid_list,
        log_status=log_status,
        time_range=time_range,
    )
    rows = list(session.exec(query).all())
    df = pd.DataFrame(_format_rows(rows))
    stream = BytesIO()
    with pd.ExcelWriter(cast(Any, stream), engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="system-log.xlsx"'},
    )
