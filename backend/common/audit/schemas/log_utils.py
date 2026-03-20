from importlib import import_module
from typing import Protocol, cast

from sqlalchemy import String, func, literal, union_all
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, select

from apps.chat.models.chat_model import Chat
from apps.chat.models.custom_prompt_model import CustomPrompt
from apps.dashboard.models.dashboard_model import CoreDashboard
from apps.data_training.models.data_training_model import DataTraining
from apps.datasource.models.datasource import CoreDatasource
from apps.datasource.models.permission import DsPermission, DsRules
from apps.system.models.system_model import (
    AiModelDetail,
    ApiKeyModel,
    AssistantModel,
    WorkspaceModel,
)
from apps.system.models.user import UserModel
from apps.terminology.models.terminology_model import Terminology


class _NamedResourceModel(Protocol):
    id: object
    name: object


def _resource_query(
    id_column: object,
    name_column: object,
    module: str,
    from_model: type[object],
) -> Select[tuple[object, object, str]]:
    id_col = cast(ColumnElement[object], cast(object, col(id_column)))
    name_col = cast(ColumnElement[object], cast(object, col(name_column)))
    query = select(
        func.cast(id_col, String).label("id"),
        name_col.label("name"),
        literal(module).label("module"),
    ).select_from(from_model)
    return cast(Select[tuple[object, object, str]], query)


def _load_xpack_model(module_path: str, class_name: str) -> type[_NamedResourceModel]:
    module = import_module(module_path)
    model = getattr(module, class_name, None)
    if not isinstance(model, type):
        raise TypeError(
            f"Invalid model '{class_name}' loaded from module '{module_path}'"
        )
    return cast(type[_NamedResourceModel], model)


def build_resource_union_query() -> Select[tuple[object, object, object]]:
    """
    构建资源名称的union查询
    返回包含id, name, module的查询
    """
    # 创建各个子查询，每个查询都包含module字段

    custom_prompt_model = cast(type[_NamedResourceModel], CustomPrompt)
    ds_permission_model = cast(type[_NamedResourceModel], DsPermission)
    ds_rules_model = cast(type[_NamedResourceModel], DsRules)

    # ai_model 表查询
    ai_model_query = _resource_query(
        AiModelDetail.id,
        AiModelDetail.name,
        "ai_model",
        AiModelDetail,
    )

    # chat 表查询（使用brief作为name）
    chat_query = _resource_query(
        Chat.id,
        Chat.brief,
        "chat",
        Chat,
    )

    # dashboard 表查询
    dashboard_query = _resource_query(
        CoreDashboard.id,
        CoreDashboard.name,
        "dashboard",
        CoreDashboard,
    )

    # datasource 表查询
    datasource_query = _resource_query(
        CoreDatasource.id,
        CoreDatasource.name,
        "datasource",
        CoreDatasource,
    )

    # custom_prompt 表查询
    custom_prompt_query = _resource_query(
        custom_prompt_model.id,
        custom_prompt_model.name,
        "prompt_words",
        custom_prompt_model,
    )

    # data_training 表查询（使用question作为name）
    data_training_query = _resource_query(
        DataTraining.id,
        DataTraining.question,
        "data_training",
        DataTraining,
    )

    # ds_permission 表查询
    ds_permission_query = _resource_query(
        ds_permission_model.id,
        ds_permission_model.name,
        "permission",
        ds_permission_model,
    )

    # ds_rules 表查询
    ds_rules_query = _resource_query(
        ds_rules_model.id,
        ds_rules_model.name,
        "rules",
        ds_rules_model,
    )

    # sys_user 表查询
    user_query = _resource_query(
        UserModel.id,
        UserModel.name,
        "user",
        UserModel,
    )

    # sys_user 表查询
    member_query = _resource_query(
        UserModel.id,
        UserModel.name,
        "member",
        UserModel,
    )

    # sys_workspace 表查询
    sys_workspace_query = _resource_query(
        WorkspaceModel.id,
        WorkspaceModel.name,
        "workspace",
        WorkspaceModel,
    )

    # terminology 表查询（使用word作为name）
    terminology_query = _resource_query(
        Terminology.id,
        Terminology.word,
        "terminology",
        Terminology,
    )

    # sys_assistant 表查询
    sys_assistant_query = _resource_query(
        AssistantModel.id,
        AssistantModel.name,
        "application",
        AssistantModel,
    )

    # sys_apikey 表查询
    sys_apikey_query = _resource_query(
        ApiKeyModel.id,
        ApiKeyModel.access_key,
        "api_key",
        ApiKeyModel,
    )

    # 使用 union_all() 方法连接所有查询
    union_query = union_all(
        ai_model_query,
        chat_query,
        dashboard_query,
        datasource_query,
        custom_prompt_query,
        data_training_query,
        ds_permission_query,
        ds_rules_query,
        user_query,
        member_query,
        sys_workspace_query,
        terminology_query,
        sys_assistant_query,
        sys_apikey_query,
    )

    # 返回查询，包含所有字段
    final_query = select(union_query.c.id, union_query.c.name, union_query.c.module)
    return cast(Select[tuple[object, object, object]], final_query)
