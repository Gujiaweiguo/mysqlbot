import json
import os
from collections.abc import Iterator
from datetime import timedelta
from typing import Annotated, Any, cast

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlmodel import col, select

from apps.datasource.models.datasource import CoreDatasource
from apps.db.constant import DB
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.crud.assistant import (
    AssistantOutDs,
    AssistantOutDsFactory,
    get_assistant_info,
    get_assistant_primary_workspace_id,
    get_assistant_workspace_ids,
)
from apps.system.crud.assistant_manage import dynamic_upgrade_cors, save
from apps.system.models.system_model import AssistantModel, WorkspaceModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from apps.system.schemas.system_schema import (
    AssistantBase,
    AssistantDTO,
    AssistantUiSchema,
    AssistantValidator,
)
from common.audit.models.log_model import OperationModules, OperationType
from common.audit.schemas.logger_decorator import LogConfig, system_log
from common.core.config import settings
from common.core.deps import CurrentAssistant, CurrentUser, SessionDep, Trans
from common.core.security import create_access_token
from common.core.sqlbot_cache import clear_cache
from common.utils.utils import get_origin_from_referer, origin_match_domain
from common.xpack_compat.file_utils import (
    check_file,
    delete_file,
    get_file_path,
    split_filename_and_flag,
    upload,
)

router = APIRouter(tags=["system_assistant"], prefix="/system/assistant")


def _parse_json_object(raw_json: str) -> dict[str, object]:
    parsed = cast(object, json.loads(raw_json))
    return cast(dict[str, object], parsed) if isinstance(parsed, dict) else {}


def _get_optional_int_value(mapping: dict[str, object], key: str) -> int | None:
    value = mapping.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _get_bool_value(mapping: dict[str, object], key: str) -> bool:
    value = mapping.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def _get_int_list(mapping: dict[str, object], key: str) -> list[int]:
    value = mapping.get(key)
    if not isinstance(value, list):
        return []
    value_list = cast(list[object], value)
    result: list[int] = []
    for item in value_list:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str) and item.isdigit():
            result.append(int(item))
    return result


def _dedupe_positive_ints(values: list[int]) -> list[int]:
    result: list[int] = []
    seen: set[int] = set()
    for value in values:
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _normalize_and_validate_configuration(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    assistant_type: int,
    configuration: str | None,
) -> str | None:
    if not configuration or assistant_type == 4:
        return configuration

    config_obj = _parse_json_object(configuration)
    workspace_ids = get_assistant_workspace_ids(config_obj)
    datasource_ids = _dedupe_positive_ints(_get_int_list(config_obj, "datasource_ids"))
    auto_ds = _get_bool_value(config_obj, "auto_ds")
    default_datasource_id = _get_optional_int_value(config_obj, "default_datasource_id")

    if datasource_ids and not workspace_ids:
        raise HTTPException(
            status_code=400,
            detail="Datasource selection requires at least one workspace",
        )

    for workspace_id in workspace_ids:
        workspace = session.get(WorkspaceModel, workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=400,
                detail=f"Workspace {workspace_id} not found",
            )
        if not current_user.isAdmin and workspace_id != current_user.oid:
            raise HTTPException(
                status_code=403,
                detail=f"No permission for workspace {workspace_id}",
            )

    if datasource_ids:
        datasource_rows = list(
            session.exec(
                select(CoreDatasource).where(col(CoreDatasource.id).in_(datasource_ids))
            ).all()
        )
        datasource_map = {row.id: row for row in datasource_rows}
        missing_ids = [ds_id for ds_id in datasource_ids if ds_id not in datasource_map]
        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Datasource not found: {missing_ids[0]}",
            )
        invalid_scope_ds = [
            ds_id
            for ds_id in datasource_ids
            if datasource_map[ds_id].oid not in workspace_ids
        ]
        if invalid_scope_ds:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Datasource {invalid_scope_ds[0]} is outside the selected workspace scope"
                ),
            )

    if auto_ds:
        if default_datasource_id is None:
            raise HTTPException(
                status_code=400,
                detail="Automatic datasource entry requires a default datasource",
            )
        if default_datasource_id not in datasource_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Default datasource {default_datasource_id} must be within the assistant datasource scope"
                ),
            )
    else:
        default_datasource_id = None

    config_obj["workspace_ids"] = workspace_ids
    config_obj["datasource_ids"] = datasource_ids
    config_obj["auto_ds"] = auto_ds
    config_obj["default_datasource_id"] = default_datasource_id
    if workspace_ids:
        config_obj["oid"] = workspace_ids[0]
    if assistant_type == 0:
        config_obj["public_list"] = datasource_ids

    return json.dumps(config_obj, ensure_ascii=False)


@router.get("/info/{id}", include_in_schema=False)
async def info(
    request: Request, response: Response, session: SessionDep, trans: Trans, id: int
) -> AssistantModel:
    if not id:
        raise Exception("miss assistant id")
    db_model_raw = cast(
        object, await get_assistant_info(session=session, assistant_id=id)
    )
    if not db_model_raw:
        raise RuntimeError("assistant application not exist")
    db_model = AssistantModel.model_validate(db_model_raw)

    origin = request.headers.get("origin") or get_origin_from_referer(request)
    if not origin:
        raise RuntimeError(trans("i18n_embedded.invalid_origin", origin=origin or ""))
    origin = origin.rstrip("/")
    if not origin_match_domain(origin, db_model.domain):
        raise RuntimeError(trans("i18n_embedded.invalid_origin", origin=origin or ""))

    response.headers["Access-Control-Allow-Origin"] = origin
    return db_model


@router.get("/app/{appId}", include_in_schema=False)
async def getApp(
    request: Request, response: Response, session: SessionDep, trans: Trans, appId: str
) -> AssistantModel:
    if not appId:
        raise Exception("miss assistant appId")
    db_model = session.exec(
        select(AssistantModel).where(col(AssistantModel.app_id) == appId)
    ).first()
    if not db_model:
        raise RuntimeError("assistant application not exist")
    db_model = AssistantModel.model_validate(db_model)
    origin = request.headers.get("origin") or get_origin_from_referer(request)
    if not origin:
        raise RuntimeError(trans("i18n_embedded.invalid_origin", origin=origin or ""))
    origin = origin.rstrip("/")
    if not origin_match_domain(origin, db_model.domain):
        raise RuntimeError(trans("i18n_embedded.invalid_origin", origin=origin or ""))

    response.headers["Access-Control-Allow-Origin"] = origin
    return db_model


@router.get("/validator", response_model=AssistantValidator, include_in_schema=False)
async def validator(
    session: SessionDep,
    id: int,
    virtual: Annotated[int | None, Query()] = None,
) -> AssistantValidator:
    if not id:
        raise Exception("miss assistant id")

    db_model_raw = cast(
        object, await get_assistant_info(session=session, assistant_id=id)
    )
    if not db_model_raw:
        return AssistantValidator()
    db_model = AssistantModel.model_validate(db_model_raw)
    assistant_oid = get_assistant_primary_workspace_id(
        db_model.configuration,
        db_model.oid,
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assistant_dict = {
        "id": virtual,
        "account": "sqlbot-inner-assistant",
        "oid": assistant_oid,
        "assistant_id": id,
    }
    access_token = create_access_token(
        assistant_dict, expires_delta=access_token_expires
    )
    return AssistantValidator(True, True, True, access_token)


@router.get(
    "/picture/{file_id}",
    summary=f"{PLACEHOLDER_PREFIX}assistant_picture_api",
    description=f"{PLACEHOLDER_PREFIX}assistant_picture_api",
)
async def picture(
    file_id: Annotated[str, Path(description="file_id")],
) -> StreamingResponse:
    file_path = get_file_path(file_id=file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    if file_id.lower().endswith(".svg"):
        media_type = "image/svg+xml"
    else:
        media_type = "image/jpeg"

    def iterfile() -> Iterator[bytes]:
        with open(file_path, mode="rb") as f:
            yield from f

    return StreamingResponse(iterfile(), media_type=media_type)


@router.patch(
    "/ui",
    summary=f"{PLACEHOLDER_PREFIX}assistant_ui_api",
    description=f"{PLACEHOLDER_PREFIX}assistant_ui_api",
)
@system_log(
    LogConfig(
        operation_type=OperationType.UPDATE,
        module=OperationModules.APPLICATION,
        result_id_expr="id",
    )
)
async def ui(
    session: SessionDep,
    data: Annotated[str, Form()],
    files: list[UploadFile] | None = None,
) -> AssistantModel:
    if files is None:
        files = []
    json_data = _parse_json_object(data)
    uiSchema = AssistantUiSchema.model_validate(json_data)
    id = uiSchema.id
    db_model = session.get(AssistantModel, id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    configuration = db_model.configuration
    config_obj = _parse_json_object(configuration) if configuration else {}

    ui_schema_dict = uiSchema.model_dump(exclude_none=True, exclude_unset=True)
    if files:
        for file in files:
            origin_file_name = file.filename
            file_name, flag_name = split_filename_and_flag(origin_file_name)
            file.filename = file_name
            if flag_name == "logo" or flag_name == "float_icon":
                try:
                    check_file(
                        file=cast(Any, file),
                        file_types=[".jpg", ".png", ".svg"],
                        limit_file_size=(10 * 1024 * 1024),
                    )
                except ValueError as e:
                    error_msg = str(e)
                    if "文件大小超过限制" in error_msg:
                        raise ValueError("文件大小超过限制（最大 10 M）")
                    else:
                        raise e
                existing_file_id = config_obj.get(flag_name)
                if isinstance(existing_file_id, str):
                    delete_file(existing_file_id)
                file_id = await upload(cast(Any, file))
                ui_schema_dict[flag_name] = file_id
            else:
                raise ValueError(f"Unsupported file flag: {flag_name}")

    for flag_name in ["logo", "float_icon"]:
        file_val = config_obj.get(flag_name)
        if isinstance(file_val, str) and not ui_schema_dict.get(flag_name):
            config_obj[flag_name] = None
            delete_file(file_val)

    for attr, value in cast(dict[str, object], ui_schema_dict).items():
        if attr != "id" and not attr.startswith("__"):
            config_obj[attr] = value

    db_model.configuration = json.dumps(config_obj, ensure_ascii=False)
    session.add(db_model)
    session.commit()
    await clear_ui_cache(db_model.id)
    return db_model


@clear_cache(
    namespace=str(CacheNamespace.EMBEDDED_INFO),
    cacheName=str(CacheName.ASSISTANT_INFO),
    keyExpression="id",
)
async def clear_ui_cache(id: int) -> None:
    _ = id


@router.get("/ds", include_in_schema=False, response_model=list[dict[str, object]])
async def ds(
    session: SessionDep, current_assistant: CurrentAssistant
) -> list[dict[str, object]]:
    if current_assistant is None:
        return []
    if current_assistant.type == 0:
        online = current_assistant.online
        configuration = current_assistant.configuration
        assert configuration is not None
        config = _parse_json_object(configuration)
        workspace_ids = get_assistant_workspace_ids(config, current_assistant.oid)
        datasource_ids = _dedupe_positive_ints(_get_int_list(config, "datasource_ids"))
        public_list = _dedupe_positive_ints(_get_int_list(config, "public_list"))
        if not workspace_ids:
            return []
        stmt = select(CoreDatasource).where(col(CoreDatasource.oid).in_(workspace_ids))
        if datasource_ids:
            stmt = stmt.where(col(CoreDatasource.id).in_(datasource_ids))
        elif not online:
            if public_list:
                stmt = stmt.where(col(CoreDatasource.id).in_(public_list))
            else:
                return []
        db_ds_list = session.exec(stmt)
        return [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description,
                "type": ds.type,
                "type_name": ds.type_name,
                "num": ds.num,
            }
            for ds in db_ds_list
        ]
    if current_assistant.type == 1:
        out_ds_instance: AssistantOutDs = AssistantOutDsFactory.get_instance(
            current_assistant
        )
        ds_list = out_ds_instance.ds_list or []
        return [
            {
                "id": str(ds.id),
                "name": ds.name,
                "description": ds.description or ds.comment,
                "type": ds.type,
                "type_name": get_db_type(ds.type),
                "num": len(ds.tables) if ds.tables else 0,
            }
            for ds in ds_list
            if get_db_type(ds.type)
        ]

    return []


def get_db_type(db_type: str | None) -> str | None:
    if db_type is None:
        return None
    try:
        db = DB.get_db(db_type)
        return db.db_name
    except Exception:
        return None


@router.get(
    "",
    response_model=list[AssistantModel],
    summary=f"{PLACEHOLDER_PREFIX}assistant_grid_api",
    description=f"{PLACEHOLDER_PREFIX}assistant_grid_api",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def query(session: SessionDep, current_user: CurrentUser) -> list[AssistantModel]:
    list_result = list(
        session.exec(
            select(AssistantModel)
            .where(
                col(AssistantModel.oid) == current_user.oid,
                col(AssistantModel.type) != 4,
            )
            .order_by(col(AssistantModel.name), col(AssistantModel.create_time))
        ).all()
    )
    return list_result


@router.get(
    "/advanced_application",
    response_model=list[AssistantModel],
    include_in_schema=False,
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def query_advanced_application(
    session: SessionDep, current_user: CurrentUser
) -> list[AssistantModel]:
    list_result = list(
        session.exec(
            select(AssistantModel)
            .where(
                col(AssistantModel.type) == 1,
                col(AssistantModel.oid) == current_user.oid,
            )
            .order_by(col(AssistantModel.name), col(AssistantModel.create_time))
        ).all()
    )
    return list_result


@router.post(
    "",
    summary=f"{PLACEHOLDER_PREFIX}assistant_create_api",
    description=f"{PLACEHOLDER_PREFIX}assistant_create_api",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
@system_log(
    LogConfig(
        operation_type=OperationType.CREATE,
        module=OperationModules.APPLICATION,
        result_id_expr="id",
    )
)
async def add(
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    creator: AssistantBase,
) -> AssistantModel:
    creator.configuration = _normalize_and_validate_configuration(
        session=session,
        current_user=current_user,
        assistant_type=creator.type,
        configuration=creator.configuration,
    )
    oid = current_user.oid if creator.type != 4 else 1
    return await save(request, session, creator, oid)


@router.put(
    "",
    summary=f"{PLACEHOLDER_PREFIX}assistant_update_api",
    description=f"{PLACEHOLDER_PREFIX}assistant_update_api",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
@clear_cache(
    namespace=str(CacheNamespace.EMBEDDED_INFO),
    cacheName=str(CacheName.ASSISTANT_INFO),
    keyExpression="editor.id",
)
@system_log(
    LogConfig(
        operation_type=OperationType.UPDATE,
        module=OperationModules.APPLICATION,
        resource_id_expr="editor.id",
    )
)
async def update(
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    editor: AssistantDTO,
) -> None:
    id = editor.id
    db_model = session.get(AssistantModel, id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    editor.configuration = _normalize_and_validate_configuration(
        session=session,
        current_user=current_user,
        assistant_type=editor.type,
        configuration=editor.configuration,
    )
    update_data = AssistantModel.model_validate(editor)
    _ = db_model.sqlmodel_update(update_data)
    session.add(db_model)
    session.commit()
    dynamic_upgrade_cors(request=request, session=session)


@router.get(
    "/{id}",
    response_model=AssistantModel,
    summary=f"{PLACEHOLDER_PREFIX}assistant_query_api",
    description=f"{PLACEHOLDER_PREFIX}assistant_query_api",
)
async def get_one(
    session: SessionDep, id: Annotated[int, Path(description="ID")]
) -> AssistantModel:
    db_model_raw = cast(
        object, await get_assistant_info(session=session, assistant_id=id)
    )
    if not db_model_raw:
        raise ValueError(f"AssistantModel with id {id} not found")
    db_model = AssistantModel.model_validate(db_model_raw)
    return db_model


@router.delete(
    "/{id}",
    summary=f"{PLACEHOLDER_PREFIX}assistant_del_api",
    description=f"{PLACEHOLDER_PREFIX}assistant_del_api",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
@clear_cache(
    namespace=str(CacheNamespace.EMBEDDED_INFO),
    cacheName=str(CacheName.ASSISTANT_INFO),
    keyExpression="id",
)
@system_log(
    LogConfig(
        operation_type=OperationType.DELETE,
        module=OperationModules.APPLICATION,
        resource_id_expr="id",
    )
)
async def delete(
    request: Request,
    session: SessionDep,
    id: Annotated[int, Path(description="ID")],
) -> None:
    db_model = session.get(AssistantModel, id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    session.delete(db_model)
    session.commit()
    dynamic_upgrade_cors(request=request, session=session)
