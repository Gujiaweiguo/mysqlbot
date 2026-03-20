import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Body, Path, Query, Request
from pydantic import BaseModel
from sqlmodel import col, select

from apps.system.crud.assistant_manage import dynamic_upgrade_cors, save
from apps.system.models.system_model import AssistantModel
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from apps.system.schemas.system_schema import AssistantBase, AssistantDTO
from common.core.deps import CurrentUser, SessionDep

router = APIRouter(tags=["system_embedded"], prefix="/system/embedded")


class EmbeddedPageResult(BaseModel):
    items: list[AssistantModel]
    total: int


def _ensure_app_credentials(model: AssistantModel) -> None:
    if not model.app_id:
        model.app_id = secrets.token_hex(8)
    if not model.app_secret:
        model.app_secret = secrets.token_hex(16)


@router.get("/{page_num}/{page_size}")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def list_embedded(
    session: SessionDep,
    current_user: CurrentUser,
    page_num: int = Path(..., description="page number"),
    page_size: int = Path(..., description="page size"),
    keyword: str = Query(default=""),
) -> EmbeddedPageResult:
    stmt = select(AssistantModel).where(
        col(AssistantModel.type) == 4,
        col(AssistantModel.oid) == 1,
    )
    if keyword:
        stmt = stmt.where(col(AssistantModel.name).contains(keyword))
    items = list(
        session.exec(stmt.order_by(col(AssistantModel.create_time).desc())).all()
    )
    start = max(page_num - 1, 0) * page_size
    end = start + page_size
    paged = items[start:end]
    for item in paged:
        _ensure_app_credentials(item)
        session.add(item)
    session.commit()
    _ = current_user
    return EmbeddedPageResult(items=paged, total=len(items))


@router.get("/{id}")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def get_embedded(
    session: SessionDep, id: Annotated[int, Path(description="ID")]
) -> AssistantModel:
    db_model = session.get(AssistantModel, id)
    if not db_model or db_model.type != 4:
        raise ValueError(f"Embedded assistant with id {id} not found")
    _ensure_app_credentials(db_model)
    session.add(db_model)
    session.commit()
    return db_model


@router.post("")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def add_embedded(
    request: Request,
    session: SessionDep,
    current_user: CurrentUser,
    creator: AssistantBase,
) -> AssistantModel:
    creator.type = 4
    db_model = await save(request, session, creator, 1)
    _ensure_app_credentials(db_model)
    session.add(db_model)
    session.commit()
    _ = current_user
    return db_model


@router.put("")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def update_embedded(
    request: Request, session: SessionDep, editor: AssistantDTO
) -> AssistantModel:
    db_model = session.get(AssistantModel, editor.id)
    if not db_model or db_model.type != 4:
        raise ValueError(f"Embedded assistant with id {editor.id} not found")
    update_data = AssistantModel.model_validate(editor)
    update_data.type = 4
    _ = db_model.sqlmodel_update(update_data)
    _ensure_app_credentials(db_model)
    session.add(db_model)
    session.commit()
    dynamic_upgrade_cors(request=request, session=session)
    return db_model


@router.patch("/secret/{id}")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def refresh_secret(
    session: SessionDep, id: Annotated[int, Path(description="ID")]
) -> AssistantModel:
    db_model = session.get(AssistantModel, id)
    if not db_model or db_model.type != 4:
        raise ValueError(f"Embedded assistant with id {id} not found")
    if not db_model.app_id:
        db_model.app_id = secrets.token_hex(8)
    db_model.app_secret = secrets.token_hex(16)
    session.add(db_model)
    session.commit()
    return db_model


@router.delete("")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def delete_embedded(
    session: SessionDep,
    ids: Annotated[list[int], Body()],
) -> bool:
    for id in ids:
        db_model = session.get(AssistantModel, id)
        if db_model and db_model.type == 4:
            session.delete(db_model)
    session.commit()
    return True
