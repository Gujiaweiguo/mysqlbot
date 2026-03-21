import time
import uuid
from typing import Any

import orjson
from sqlalchemy import and_, text
from sqlmodel import col

from apps.chat.crud.chat import get_chart_data_ds
from apps.dashboard.models.dashboard_model import (
    CoreDashboard,
    CreateDashboard,
    DashboardBaseResponse,
    QueryDashboard,
)
from common.core.deps import CurrentUser, SessionDep


def list_resource(
    session: SessionDep,
    dashboard: QueryDashboard,
    current_user: CurrentUser,
) -> list[DashboardBaseResponse]:
    sql = "SELECT id, name, type, node_type, pid, create_time FROM core_dashboard"
    filters = []
    params = {}
    oid = str(current_user.oid if current_user.oid is not None else 1)
    filters.append("workspace_id = :workspace_id")
    filters.append("create_by = :create_by")
    params["workspace_id"] = oid
    params["create_by"] = str(current_user.id)
    if dashboard.node_type is not None and dashboard.node_type != "":
        filters.append("node_type = :node_type")
        params["node_type"] = dashboard.node_type

    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY create_time DESC"
    result = session.execute(text(sql), params)
    nodes = [DashboardBaseResponse(**dict(row)) for row in result.mappings()]
    node_dict = {node.id: node for node in nodes if node.id is not None}
    tree: list[DashboardBaseResponse] = []
    for node in nodes:
        if node.pid == "root":
            tree.append(node)
        elif node.pid in node_dict and node.pid is not None:
            node_dict[node.pid].children.append(node)
    return tree


def load_resource(
    session: SessionDep,
    dashboard: QueryDashboard,
) -> dict[str, Any]:
    sql = text("""
               SELECT cd.*,
                      creator.name AS create_name,
                      updater.name AS update_name
               FROM core_dashboard cd
                        LEFT JOIN sys_user creator ON cd.create_by = creator.id::varchar
        LEFT JOIN sys_user updater
               ON cd.update_by = updater.id:: varchar
               WHERE cd.id = :dashboard_id
               """)
    result = session.execute(sql, {"dashboard_id": dashboard.id}).mappings().first()
    if result is None:
        return {}

    result_dict = dict(result)
    canvas_view_obj: dict[str, Any] = {}
    canvas_view_info = result_dict.get("canvas_view_info")
    if isinstance(canvas_view_info, str):
        try:
            parsed = orjson.loads(canvas_view_info)
            if isinstance(parsed, dict):
                canvas_view_obj = parsed
        except Exception:
            pass
    for item in canvas_view_obj.values():
        if (
            isinstance(item, dict)
            and all(key in item for key in ["datasource", "sql"])
            and isinstance(item.get("datasource"), int)
            and isinstance(item.get("sql"), str)
        ):
            datasource_id = item["datasource"]
            sql_text = item["sql"]
            data_result = get_chart_data_ds(session, datasource_id, sql_text)
            item_data = item.get("data")
            if not isinstance(item_data, dict):
                item_data = {}
                item["data"] = item_data
            item_data["data"] = data_result.get("data", [])
            item["status"] = data_result.get("status")
            item["message"] = data_result.get("message")
    result_dict["canvas_view_info"] = orjson.dumps(canvas_view_obj).decode()
    return result_dict


def get_create_base_info(
    user: CurrentUser, dashboard: CreateDashboard
) -> CoreDashboard:
    new_id = uuid.uuid4().hex
    record = CoreDashboard(**dashboard.model_dump())
    record.workspace_id = str(user.oid if user.oid is not None else 1)
    record.id = new_id
    record.create_by = str(user.id)
    record.create_time = int(time.time())
    return record


def create_resource(
    session: SessionDep,
    user: CurrentUser,
    dashboard: CreateDashboard,
) -> CoreDashboard:
    record = get_create_base_info(user, dashboard)
    session.add(record)
    session.flush()
    session.refresh(record)
    session.commit()
    return record


def update_resource(
    session: SessionDep,
    user: CurrentUser,
    dashboard: QueryDashboard,
) -> CoreDashboard:
    record = session.get(CoreDashboard, dashboard.id)
    if record is None:
        raise ValueError(f"Resource with id {dashboard.id} does not exist")
    record.name = dashboard.name
    record.update_by = str(user.id)
    record.update_time = int(time.time())
    session.add(record)
    session.commit()
    return record


def create_canvas(
    session: SessionDep,
    user: CurrentUser,
    dashboard: CreateDashboard,
) -> CoreDashboard:
    record = get_create_base_info(user, dashboard)
    record.node_type = dashboard.node_type
    record.component_data = dashboard.component_data
    record.canvas_style_data = dashboard.canvas_style_data
    record.canvas_view_info = dashboard.canvas_view_info
    session.add(record)
    session.flush()
    session.refresh(record)
    session.commit()
    return record


def update_canvas(
    session: SessionDep,
    user: CurrentUser,
    dashboard: CreateDashboard,
) -> CoreDashboard:
    record = session.get(CoreDashboard, dashboard.id)
    if record is None:
        raise ValueError(f"Resource with id {dashboard.id} does not exist")
    record.name = dashboard.name
    record.update_by = str(user.id)
    record.update_time = int(time.time())
    record.component_data = dashboard.component_data
    record.canvas_style_data = dashboard.canvas_style_data
    record.canvas_view_info = dashboard.canvas_view_info
    session.add(record)
    session.commit()
    return record


def validate_name(
    session: SessionDep,
    user: CurrentUser,
    dashboard: QueryDashboard,
) -> bool:
    if not dashboard.opt:
        raise ValueError("opt is required")
    oid = str(user.oid if user.oid is not None else 1)
    uid = str(user.id)

    if dashboard.opt in ("newLeaf", "newFolder"):
        query = session.query(CoreDashboard).filter(
            and_(
                col(CoreDashboard.workspace_id) == oid,
                col(CoreDashboard.create_by) == uid,
                col(CoreDashboard.name) == dashboard.name,
            )
        )
    elif dashboard.opt in ("updateLeaf", "updateFolder", "rename"):
        if not dashboard.id:
            raise ValueError("id is required for update operation")
        query = session.query(CoreDashboard).filter(
            and_(
                col(CoreDashboard.workspace_id) == oid,
                col(CoreDashboard.create_by) == uid,
                col(CoreDashboard.name) == dashboard.name,
                col(CoreDashboard.id) != dashboard.id,
            )
        )
    else:
        raise ValueError(f"Invalid opt value: {dashboard.opt}")
    return not bool(session.query(query.exists()).scalar())


def delete_resource(
    session: SessionDep,
    current_user: CurrentUser,
    resource_id: str,
) -> bool:
    core_dashboard = session.get(CoreDashboard, resource_id)
    if not core_dashboard:
        raise ValueError(f"Resource with id {resource_id} does not exist")
    if core_dashboard.create_by != str(current_user.id):
        raise ValueError(
            f"Resource with id {resource_id} not owned by the current user"
        )
    session.delete(core_dashboard)
    session.commit()
    return True
