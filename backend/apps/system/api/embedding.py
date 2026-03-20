from fastapi import APIRouter, Body, HTTPException

from apps.system.crud.embedding_admin import (
    disable_embedding,
    enable_embedding,
    get_embedding_admin_config,
    get_embedding_admin_config_unmasked,
    get_embedding_models,
    save_embedding_admin_config,
    validate_embedding_config,
)
from apps.system.schemas.embedding_schema import (
    EmbeddingConfigResponse,
    EmbeddingConfigUpdateRequest,
    EmbeddingModelOption,
    EmbeddingModelsResponse,
    EmbeddingToggleResponse,
    EmbeddingValidateRequest,
    EmbeddingValidateResponse,
)
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import CurrentUser, SessionDep

router = APIRouter(tags=["embedding_admin"], prefix="/system/embedding")


@router.get("/config", response_model=EmbeddingConfigResponse)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def get_config(session: SessionDep) -> EmbeddingConfigResponse:
    return get_embedding_admin_config(session)


@router.put("/config", response_model=EmbeddingConfigResponse)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def save_config(
    session: SessionDep,
    current_user: CurrentUser,
    request: EmbeddingConfigUpdateRequest,
) -> EmbeddingConfigResponse:
    return save_embedding_admin_config(session, request.config, user_id=current_user.id)


@router.post("/validate", response_model=EmbeddingValidateResponse)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def validate_config(
    session: SessionDep, request: EmbeddingValidateRequest
) -> EmbeddingValidateResponse:
    if request.use_saved_config:
        current = get_embedding_admin_config_unmasked(session)
        return validate_embedding_config(session, current.config, persist_result=True)
    if request.config is None:
        raise HTTPException(
            status_code=400, detail="config is required when use_saved_config=false"
        )
    return validate_embedding_config(session, request.config, persist_result=False)


@router.post("/enable", response_model=EmbeddingToggleResponse)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def enable_config(
    session: SessionDep,
    confirm_reindex: bool = Body(default=False, embed=True),
) -> EmbeddingToggleResponse:
    try:
        status = enable_embedding(session, confirm_reindex=confirm_reindex)
        return EmbeddingToggleResponse(
            success=True, state=status.state, message="Embedding has been enabled"
        )
    except ValueError as exc:
        return EmbeddingToggleResponse(
            success=False,
            state=get_embedding_admin_config(session).status.state,
            message=str(exc),
        )


@router.post("/disable", response_model=EmbeddingToggleResponse)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def disable_config(session: SessionDep) -> EmbeddingToggleResponse:
    status = disable_embedding(session)
    return EmbeddingToggleResponse(
        success=True, state=status.state, message="Embedding has been disabled"
    )


@router.get("/models", response_model=EmbeddingModelsResponse)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def get_models(supplier_id: int) -> EmbeddingModelsResponse:
    model_names = get_embedding_models(supplier_id)
    return EmbeddingModelsResponse(
        supplier_id=supplier_id,
        models=[EmbeddingModelOption(name=m) for m in model_names],
    )
