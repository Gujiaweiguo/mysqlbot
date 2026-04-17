import asyncio
import json
import os
from collections.abc import AsyncIterator
from importlib import import_module
from pathlib import Path
from typing import Any

from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.exception_handlers import (
    request_validation_exception_handler as fastapi_request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from alembic import command
from apps.api import api_router
from apps.datasource.crud.datasource import ensure_internal_pg_datasource
from apps.openclaw.mcp_metadata import (
    OPENCLAW_MCP_OPERATION_IDS,
    build_openclaw_mcp_runtime_contract,
    openclaw_mcp_setup_enabled,
)
from apps.openclaw.router import openclaw_validation_error_response
from apps.swagger.i18n import (
    DEFAULT_LANG,
    PLACEHOLDER_PREFIX,
    get_translation,
    i18n_list,
    tags_metadata,
)
from apps.system.crud.aimodel_manage import async_model_info
from apps.system.crud.assistant import init_dynamic_cors
from apps.system.crud.assistant_manage import ensure_default_embedded_assistant
from apps.system.crud.embedding_admin import (
    embedding_runtime_enabled,
    get_effective_embedding_config,
)
from apps.system.crud.user import sync_default_admin_password
from apps.system.middleware.auth import TokenMiddleware
from apps.system.models.system_model import WorkspaceModel
from apps.system.schemas.embedding_schema import EmbeddingProviderType
from apps.system.schemas.permission import RequestContextMiddleware
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.config import settings
from common.core.db import engine
from common.core.response_middleware import ResponseMiddleware, exception_handler
from common.core.sqlbot_cache import init_sqlbot_cache
from common.observability import (
    AdminApiObservabilityMiddleware,
    McpObservabilityMiddleware,
    metrics_view,
)
from common.utils.embedding_threads import (
    fill_empty_data_training_embeddings,
    fill_empty_table_and_ds_embeddings,
    fill_empty_terminology_embeddings,
)
from common.utils.sync_job_runtime import (
    recover_stale_sync_jobs,
    start_periodic_stale_recovery,
    sync_job_session_maker,
)
from common.utils.utils import SQLBotLogUtil
from common.xpack_compat.startup import (
    clean_xpack_cache,
    monitor_app,
)
from common.xpack_compat.startup import (
    init_fastapi_app as init_xpack_fastapi_app,
)


def run_migrations() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def init_terminology_embedding_data() -> None:
    fill_empty_terminology_embeddings()


def init_data_training_embedding_data() -> None:
    fill_empty_data_training_embeddings()


def init_table_and_ds_embedding() -> None:
    fill_empty_table_and_ds_embeddings()


def init_default_internal_datasource() -> None:
    with Session(engine) as session:
        workspace_ids = session.exec(select(WorkspaceModel.id)).all()
        if not workspace_ids:
            workspace_ids = [1]
        for workspace_id in workspace_ids:
            if workspace_id is None:
                continue
            ensure_internal_pg_datasource(
                session=session, oid=workspace_id, create_by=1, commit=False
            )
        session.commit()


def init_stale_datasource_sync_jobs() -> None:
    recover_stale_sync_jobs(sync_job_session_maker)


def _get_fastapi_mcp_class() -> Any:
    mcp_module = import_module("fastapi_mcp")
    return mcp_module.FastApiMCP


def _should_run_startup_tasks() -> bool:
    return os.getenv("SKIP_STARTUP_TASKS", "false").lower() not in {
        "1",
        "true",
        "yes",
    }


def _should_setup_mcp() -> bool:
    return openclaw_mcp_setup_enabled()


def _should_run_embedding_startup_backfill() -> bool:
    if not embedding_runtime_enabled():
        return False
    config = get_effective_embedding_config()
    if config.provider_type != EmbeddingProviderType.OPENAI_COMPATIBLE:
        return True
    return config.startup_backfill_policy == "eager"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not _should_run_startup_tasks():
        SQLBotLogUtil.info("⏭️ Skipping startup side effects")
        yield
        return

    run_migrations()
    with Session(engine) as session:
        sync_default_admin_password(session=session)
    with Session(engine) as session:
        ensure_default_embedded_assistant(session=session)
    init_sqlbot_cache()
    init_dynamic_cors(app)
    if _should_run_embedding_startup_backfill():
        init_terminology_embedding_data()
        init_data_training_embedding_data()
    else:
        SQLBotLogUtil.info("⏭️ Skipping startup embedding backfill for remote provider")
    init_default_internal_datasource()
    init_stale_datasource_sync_jobs()
    stale_recovery_task = await start_periodic_stale_recovery()
    if _should_run_embedding_startup_backfill():
        init_table_and_ds_embedding()
    SQLBotLogUtil.info("✅ SQLBot 初始化完成")
    await clean_xpack_cache()
    await async_model_info()  # 异步加密已有模型的密钥和地址
    await monitor_app(app)
    yield
    stale_recovery_task.cancel()
    try:
        await stale_recovery_task
    except asyncio.CancelledError:
        pass
    SQLBotLogUtil.info("SQLBot 应用关闭")


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags and len(route.tags) > 0 else ""
    return f"{tag}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

# cache docs for different text
_openapi_cache: dict[str, dict[str, Any]] = {}


# replace placeholder
def replace_placeholders_in_schema(schema: Any, trans: dict[str, str]) -> None:
    """
    search OpenAPI schema，replace PLACEHOLDER_xxx to text。
    """
    if isinstance(schema, dict):
        for key, value in schema.items():
            if isinstance(value, str) and value.startswith(PLACEHOLDER_PREFIX):
                placeholder_key = value[len(PLACEHOLDER_PREFIX) :]
                schema[key] = trans.get(placeholder_key, value)
            else:
                replace_placeholders_in_schema(value, trans)
    elif isinstance(schema, list):
        for item in schema:
            replace_placeholders_in_schema(item, trans)


# OpenAPI build
def get_language_from_request(request: Request) -> str:
    # get param from query ?lang=zh
    lang = request.query_params.get("lang")
    if lang in i18n_list:
        return lang
    # get lang from Accept-Language Header
    accept_lang = request.headers.get("accept-language", "")
    if "zh" in accept_lang.lower():
        return "zh"
    return DEFAULT_LANG


def generate_openapi_for_lang(lang: str) -> dict[str, Any]:
    if lang in _openapi_cache:
        return _openapi_cache[lang]

    # tags metadata
    trans = get_translation(lang)
    localized_tags = []
    for tag in tags_metadata:
        desc = tag["description"]
        if desc.startswith(PLACEHOLDER_PREFIX):
            key = desc[len(PLACEHOLDER_PREFIX) :]
            desc = trans.get(key, desc)
        localized_tags.append({"name": tag["name"], "description": desc})

    # 1. create OpenAPI
    openapi_schema = get_openapi(
        title="SQLBot API Document" if lang == "en" else "SQLBot API 文档",
        version="1.0.0",
        routes=app.routes,
        tags=localized_tags,
    )

    # openapi version
    openapi_schema.setdefault("openapi", "3.1.0")

    # 2. get trans for lang
    trans = get_translation(lang)

    # 3. replace placeholder
    replace_placeholders_in_schema(openapi_schema, trans)

    # 4. cache
    _openapi_cache[lang] = openapi_schema
    return openapi_schema


def _frontend_dist_dir() -> Path | None:
    candidates = [
        Path(settings.BASE_DIR) / "frontend" / "dist",
        Path(__file__).resolve().parents[1] / "frontend" / "dist",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _frontend_response(full_path: str) -> FileResponse:
    frontend_dir = _frontend_dist_dir()
    if frontend_dir is None:
        raise StarletteHTTPException(status_code=404, detail="Not Found")

    resolved_dir = frontend_dir.resolve()
    requested = (resolved_dir / full_path).resolve()
    if requested.is_file() and resolved_dir in requested.parents:
        return FileResponse(
            requested,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    index_file = resolved_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file, headers={"Cache-Control": "no-store"})
    raise StarletteHTTPException(status_code=404, detail="Not Found")


# custom /openapi.json and /docs
@app.get("/openapi.json", include_in_schema=False)
async def custom_openapi(request: Request) -> JSONResponse:
    lang = get_language_from_request(request)
    schema = generate_openapi_for_lang(lang)
    return JSONResponse(schema)


@app.get("/health", include_in_schema=False)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics(request: Request) -> Response:
    return await metrics_view(request)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui(request: Request) -> HTMLResponse:
    lang = get_language_from_request(request)
    from fastapi.openapi.docs import get_swagger_ui_html

    return get_swagger_ui_html(
        openapi_url=f"/openapi.json?lang={lang}",
        title="SQLBot API Docs",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        swagger_js_url="/swagger-ui-bundle.js",
        swagger_css_url="/swagger-ui.css",
    )


async def starlette_http_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    if isinstance(exc, StarletteHTTPException):
        return await exception_handler.http_exception_handler(request, exc)
    return await exception_handler.global_exception_handler(request, exc)


async def request_validation_handler(request: Request, exc: Exception) -> Response:
    if not isinstance(exc, RequestValidationError):
        return await exception_handler.global_exception_handler(request, exc)

    openclaw_response = openclaw_validation_error_response(request, exc)
    if openclaw_response is not None:
        return openclaw_response

    return await fastapi_request_validation_exception_handler(request, exc)


mcp_app = FastAPI()
images_path = settings.MCP_IMAGE_PATH
os.makedirs(images_path, exist_ok=True)
mcp_app.mount("/images", StaticFiles(directory=images_path), name="images")


@mcp_app.get(settings.MCP_HEALTH_PATH, include_in_schema=False)
async def mcp_health_check() -> JSONResponse:
    contract = build_openclaw_mcp_runtime_contract()
    if not contract["ready"]:
        SQLBotLogUtil.error(
            json.dumps(
                {
                    "event": "openclaw_mcp_health_state",
                    "group": "openclaw_mcp",
                    "channel_path": "health",
                    "status_code": 503,
                    "ready": contract["ready"],
                    "issues": contract["issues"],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            exc_info=False,
        )
    return JSONResponse(
        status_code=200 if contract["ready"] else 503,
        content=contract,
    )


@mcp_app.get("/metrics", include_in_schema=False)
async def mcp_prometheus_metrics(request: Request) -> Response:
    return await metrics_view(request)


@app.get("/images/{file_path:path}")
async def serve_chart_image(file_path: str) -> FileResponse:
    import re

    clean = re.sub(r"[^a-zA-Z0-9_./-]", "", file_path)
    full = os.path.join(images_path, clean)
    if os.path.isfile(full):
        return FileResponse(full, media_type="image/png")
    return Response(status_code=404)


if _should_setup_mcp():
    # FastApiMCP.setup_server() runs inside __init__, so the environment gate must
    # wrap object creation itself instead of a later setup call.
    mcp = _get_fastapi_mcp_class()(
        app,
        name="SQLBot MCP Server",
        description="SQLBot MCP Server",
        describe_all_responses=True,
        describe_full_response_schema=True,
        include_operations=list(OPENCLAW_MCP_OPERATION_IDS),
    )
    mcp.mount(mcp_app)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(TokenMiddleware)
app.add_middleware(ResponseMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RequestContextMiddlewareCommon)
app.add_middleware(AdminApiObservabilityMiddleware)
mcp_app.add_middleware(McpObservabilityMiddleware)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Register exception handlers
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(Exception, exception_handler.global_exception_handler)

init_xpack_fastapi_app(app)


@app.get("/", include_in_schema=False)
async def frontend_index() -> FileResponse:
    return _frontend_response("")


@app.get("/{full_path:path}", include_in_schema=False)
async def frontend_assets(full_path: str) -> FileResponse:
    if full_path.startswith("api/") or full_path in {"docs", "openapi.json", "mcp"}:
        raise StarletteHTTPException(status_code=404, detail="Not Found")
    return _frontend_response(full_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # uvicorn.run("main:mcp_app", host="0.0.0.0", port=8001) # mcp server
