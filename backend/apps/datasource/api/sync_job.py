from fastapi import APIRouter, HTTPException, Path, Query
from sqlmodel import col, select

from apps.datasource.constants.sync import should_route_async
from apps.datasource.crud.sync_job import (
    build_sync_job_status_response,
    cancel_sync_job,
    get_sync_job_by_id,
    list_sync_jobs_by_ds,
    retry_sync_job,
    submit_datasource_sync_job,
)
from apps.datasource.models.datasource import CoreDatasource, SelectedTablePayload
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    DatasourceSyncJobStatusResponse,
    DatasourceSyncJobSubmitResponse,
)
from apps.datasource.schemas.sync_job import (
    SyncJobStatusResponse,
    SyncJobSubmitRequest,
    SyncJobSubmitResponse,
    SyncJobSummary,
)
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.config import settings
from common.core.deps import CurrentUser, SessionDep
from common.utils.sync_job_runtime import dispatch_sync_job

router = APIRouter(tags=["Sync Job"], prefix="/sync-jobs")


def _to_submit_wire(resp: DatasourceSyncJobSubmitResponse) -> SyncJobSubmitResponse:
    return SyncJobSubmitResponse(**resp.model_dump())


def _to_status_wire(resp: DatasourceSyncJobStatusResponse) -> SyncJobStatusResponse:
    return SyncJobStatusResponse(**resp.model_dump())


def _to_summary(job: DatasourceSyncJob) -> SyncJobSummary:
    job_id = job.id
    if job_id is None:
        raise ValueError("sync job id is missing")
    return SyncJobSummary(
        job_id=job_id,
        datasource_id=job.ds_id,
        status=job.status,
        total_tables=job.total_tables,
        completed_tables=job.completed_tables,
        failed_tables=job.failed_tables,
        skipped_tables=job.skipped_tables,
        create_time=job.create_time,
        finish_time=job.finish_time,
    )


@router.post(
    "",
    response_model=SyncJobSubmitResponse,
    status_code=202,
    summary=f"{PLACEHOLDER_PREFIX}sync_job_submit",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def submit_sync_job(
    session: SessionDep,
    user: CurrentUser,
    body: SyncJobSubmitRequest,
) -> SyncJobSubmitResponse:
    if not should_route_async(
        flag_enabled=settings.DATASOURCE_ASYNC_SYNC_ENABLED,
        selected_table_count=len(body.tables),
        threshold=settings.DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD,
    ):
        raise HTTPException(
            status_code=422,
            detail="async sync not available: feature flag disabled or below threshold",
        )
    ds = session.exec(
        select(CoreDatasource).where(col(CoreDatasource.id) == body.datasource_id)
    ).first()
    if ds is None:
        raise HTTPException(status_code=404, detail="datasource not found")
    tables = [SelectedTablePayload(table_name=name) for name in body.tables]
    result = submit_datasource_sync_job(
        session,
        ds_id=body.datasource_id,
        oid=user.oid,
        create_by=user.id,
        total_tables=len(tables),
        requested_tables=tables,
    )
    if not result.reused_active_job:
        _ = dispatch_sync_job(result.job_id)
    return _to_submit_wire(result)


@router.get(
    "",
    response_model=list[SyncJobSummary],
    summary=f"{PLACEHOLDER_PREFIX}sync_job_list",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def list_jobs(
    session: SessionDep,
    datasource_id: int = Query(..., description="datasource id"),
) -> list[SyncJobSummary]:
    return [_to_summary(job) for job in list_sync_jobs_by_ds(session, datasource_id)]


@router.get(
    "/{job_id}",
    response_model=SyncJobStatusResponse,
    summary=f"{PLACEHOLDER_PREFIX}sync_job_status",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def get_status(
    session: SessionDep,
    job_id: int = Path(..., description="sync job id"),
) -> SyncJobStatusResponse:
    job = get_sync_job_by_id(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="sync job not found")
    return _to_status_wire(build_sync_job_status_response(job))


@router.post(
    "/{job_id}/cancel",
    response_model=SyncJobStatusResponse,
    summary=f"{PLACEHOLDER_PREFIX}sync_job_cancel",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def cancel_job(
    session: SessionDep,
    job_id: int = Path(..., description="sync job id"),
) -> SyncJobStatusResponse:
    job = get_sync_job_by_id(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="sync job not found")
    try:
        cancelled = cancel_sync_job(session, job=job)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_status_wire(build_sync_job_status_response(cancelled))


@router.post(
    "/{job_id}/retry",
    response_model=SyncJobSubmitResponse,
    status_code=202,
    summary=f"{PLACEHOLDER_PREFIX}sync_job_retry",
)
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def retry_job(
    session: SessionDep,
    user: CurrentUser,
    job_id: int = Path(..., description="sync job id"),
) -> SyncJobSubmitResponse:
    job = get_sync_job_by_id(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="sync job not found")
    try:
        result = retry_sync_job(session, job=job, oid=user.oid, create_by=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not result.reused_active_job:
        _ = dispatch_sync_job(result.job_id)
    return _to_submit_wire(result)
