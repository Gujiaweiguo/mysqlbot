from fastapi import APIRouter

from apps.audit.api import router as audit_router
from apps.chat.api import chat, custom_prompt
from apps.dashboard.api import dashboard_api
from apps.data_training.api import data_training
from apps.datasource.api import (
    datasource,
    permission,
    recommended_problem,
    sync_job,
    table_relation,
)
from apps.mcp import mcp
from apps.openclaw.router import router as openclaw_router
from apps.settings.api import base
from apps.system.api.openclaw import router as openclaw_admin_router
from apps.system.api import (
    aimodel,
    apikey,
    appearance,
    assistant,
    authentication,
    embedded,
    embedding,
    license,
    login,
    parameter,
    platform,
    user,
    variable_api,
    workspace,
)
from apps.terminology.api import terminology

# from audit.api import audit_api


api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(user.router)
api_router.include_router(workspace.router)
api_router.include_router(audit_router)
api_router.include_router(appearance.router)
api_router.include_router(authentication.router)
api_router.include_router(embedded.router)
api_router.include_router(license.router)
api_router.include_router(platform.router)
api_router.include_router(assistant.router)
api_router.include_router(aimodel.router)
api_router.include_router(embedding.router)
api_router.include_router(base.router)
api_router.include_router(openclaw_admin_router)
api_router.include_router(terminology.router)
api_router.include_router(data_training.router)
api_router.include_router(datasource.router)
api_router.include_router(sync_job.router)
api_router.include_router(permission.router)
api_router.include_router(custom_prompt.router)
api_router.include_router(chat.router)
api_router.include_router(dashboard_api.router)
api_router.include_router(mcp.router)
api_router.include_router(openclaw_router)
api_router.include_router(table_relation.router)
api_router.include_router(parameter.router)
api_router.include_router(apikey.router)

api_router.include_router(recommended_problem.router)

api_router.include_router(variable_api.router)
