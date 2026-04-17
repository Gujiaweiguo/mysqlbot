from fastapi import APIRouter

from apps.openclaw import mcp_metadata
from apps.system.schemas import openclaw_integration_schema as openclaw_schema
from apps.system.schemas.permission import SqlbotPermission, require_permissions

router = APIRouter(tags=["system/openclaw"], prefix="/system/openclaw")


@router.get("/mcp-config", response_model=openclaw_schema.OpenClawMcpConfigResponse)
@require_permissions(permission=SqlbotPermission(role=["admin"]))
async def get_openclaw_mcp_config() -> openclaw_schema.OpenClawMcpConfigResponse:
    return openclaw_schema.OpenClawMcpConfigResponse.model_validate(
        mcp_metadata.build_openclaw_mcp_runtime_contract()
    )
