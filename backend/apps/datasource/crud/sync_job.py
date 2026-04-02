from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from apps.datasource.models.datasource import SelectedTablePayload
from apps.datasource.models.sync_job import (
    ACTIVE_DATASOURCE_SYNC_JOB_STATUSES,
    DatasourceSyncJob,
    DatasourceSyncJobStatusResponse,
    DatasourceSyncJobSubmitResponse,
    SyncJobPhase,
    SyncJobStatus,
    dump_selected_tables_payload,
    load_selected_tables_payload,
)
from common.core.config import settings
from common.observability.sync_metrics import (
    SYNC_JOB_STATUS_TRANSITIONS,
    SYNC_JOBS_SUBMITTED,
)


def _allocate_sqlite_job_id(session: Session) -> int:
    statement = select(DatasourceSyncJob.id).order_by(col(DatasourceSyncJob.id).desc())
    latest_id = session.exec(statement).first()
    if latest_id is None:
        return 1
    return latest_id + 1


def create_sync_job(
    session: Session,
    *,
    ds_id: int,
    oid: int,
    create_by: int,
    total_tables: int = 0,
    total_fields: int = 0,
) -> DatasourceSyncJob:
    now = datetime.now()
    job = DatasourceSyncJob(
        ds_id=ds_id,
        oid=oid,
        create_by=create_by,
        status=SyncJobStatus.PENDING,
        phase=SyncJobPhase.SUBMIT,
        total_tables=total_tables,
        completed_tables=0,
        failed_tables=0,
        skipped_tables=0,
        total_fields=total_fields,
        completed_fields=0,
        requested_tables="[]",
        create_time=now,
        update_time=now,
    )
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        job.id = _allocate_sqlite_job_id(session)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_sync_job_by_id(session: Session, job_id: int) -> DatasourceSyncJob | None:
    statement = select(DatasourceSyncJob).where(col(DatasourceSyncJob.id) == job_id)
    return session.exec(statement).first()


def get_active_sync_job(session: Session, ds_id: int) -> DatasourceSyncJob | None:
    statement = (
        select(DatasourceSyncJob)
        .where(col(DatasourceSyncJob.ds_id) == ds_id)
        .where(
            col(DatasourceSyncJob.status).in_(
                [status.value for status in ACTIVE_DATASOURCE_SYNC_JOB_STATUSES]
            )
        )
        .order_by(col(DatasourceSyncJob.create_time).desc())
    )
    return session.exec(statement).first()


def list_sync_jobs_by_ds(
    session: Session,
    ds_id: int,
    *,
    limit: int = 10,
) -> list[DatasourceSyncJob]:
    statement = (
        select(DatasourceSyncJob)
        .where(col(DatasourceSyncJob.ds_id) == ds_id)
        .order_by(col(DatasourceSyncJob.create_time).desc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def build_sync_job_status_response(
    job: DatasourceSyncJob,
) -> DatasourceSyncJobStatusResponse:
    job_id = job.id
    if job_id is None:
        raise ValueError("sync job id is missing")
    return DatasourceSyncJobStatusResponse(
        job_id=job_id,
        datasource_id=job.ds_id,
        status=job.status,
        phase=job.phase,
        total_tables=job.total_tables,
        completed_tables=job.completed_tables,
        failed_tables=job.failed_tables,
        skipped_tables=job.skipped_tables,
        total_fields=job.total_fields,
        completed_fields=job.completed_fields,
        current_table_name=job.current_table_name,
        embedding_followup_status=job.embedding_followup_status,
        error_summary=job.error_summary,
        create_time=job.create_time,
        update_time=job.update_time,
        start_time=job.start_time,
        finish_time=job.finish_time,
    )


def submit_datasource_sync_job(
    session: Session,
    *,
    ds_id: int,
    oid: int,
    create_by: int,
    total_tables: int,
    requested_tables: list[SelectedTablePayload] | None = None,
) -> DatasourceSyncJobSubmitResponse:
    active_job = get_active_sync_job(session, ds_id)
    if active_job is not None:
        active_job_id = active_job.id
        if active_job_id is None:
            raise ValueError("active sync job id is missing")
        SYNC_JOBS_SUBMITTED.labels(reused_active="true").inc()
        return DatasourceSyncJobSubmitResponse(
            job_id=active_job_id,
            datasource_id=active_job.ds_id,
            status=active_job.status,
            phase=active_job.phase,
            reused_active_job=True,
        )

    try:
        job = create_sync_job(
            session,
            ds_id=ds_id,
            oid=oid,
            create_by=create_by,
            total_tables=total_tables,
        )
        job.requested_tables = dump_selected_tables_payload(requested_tables or [])
        session.add(job)
        session.commit()
        session.refresh(job)
    except IntegrityError:
        session.rollback()
        active_job = get_active_sync_job(session, ds_id)
        if active_job is not None:
            active_job_id = active_job.id
            if active_job_id is None:
                raise ValueError("active sync job id is missing")
            SYNC_JOBS_SUBMITTED.labels(reused_active="true").inc()
            return DatasourceSyncJobSubmitResponse(
                job_id=active_job_id,
                datasource_id=active_job.ds_id,
                status=active_job.status,
                phase=active_job.phase,
                reused_active_job=True,
            )
        raise
    job_id = job.id
    if job_id is None:
        raise ValueError("created sync job id is missing")
    SYNC_JOBS_SUBMITTED.labels(reused_active="false").inc()
    return DatasourceSyncJobSubmitResponse(
        job_id=job_id,
        datasource_id=job.ds_id,
        status=job.status,
        phase=job.phase,
        reused_active_job=False,
    )


def get_requested_tables(job: DatasourceSyncJob) -> list[SelectedTablePayload]:
    return load_selected_tables_payload(job.requested_tables)


def cancel_sync_job(session: Session, *, job: DatasourceSyncJob) -> DatasourceSyncJob:
    if job.status not in ACTIVE_DATASOURCE_SYNC_JOB_STATUSES:
        raise ValueError("sync job is not cancelable")
    return update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.CANCELLED,
        phase=job.phase,
        current_table_name=None,
        error_summary="sync job cancelled by operator",
    )


def retry_sync_job(
    session: Session,
    *,
    job: DatasourceSyncJob,
    oid: int,
    create_by: int,
) -> DatasourceSyncJobSubmitResponse:
    if job.status not in {
        SyncJobStatus.FAILED,
        SyncJobStatus.PARTIAL,
        SyncJobStatus.CANCELLED,
    }:
        raise ValueError("sync job is not retryable")

    requested_tables = get_requested_tables(job)
    if not requested_tables:
        raise ValueError("sync job has no requested tables to retry")

    return submit_datasource_sync_job(
        session,
        ds_id=job.ds_id,
        oid=oid,
        create_by=create_by,
        total_tables=len(requested_tables),
        requested_tables=requested_tables,
    )


def update_sync_job_status(
    session: Session,
    *,
    job: DatasourceSyncJob,
    status: SyncJobStatus,
    phase: SyncJobPhase | None = None,
    total_tables: int | None = None,
    completed_tables: int | None = None,
    failed_tables: int | None = None,
    skipped_tables: int | None = None,
    total_fields: int | None = None,
    completed_fields: int | None = None,
    current_table_name: str | None = None,
    error_summary: str | None = None,
) -> DatasourceSyncJob:
    now = datetime.now()
    job.status = status
    if phase is not None:
        job.phase = phase
    if total_tables is not None:
        job.total_tables = total_tables
    if completed_tables is not None:
        job.completed_tables = completed_tables
    if failed_tables is not None:
        job.failed_tables = failed_tables
    if skipped_tables is not None:
        job.skipped_tables = skipped_tables
    if total_fields is not None:
        job.total_fields = total_fields
    if completed_fields is not None:
        job.completed_fields = completed_fields
    if current_table_name is not None:
        job.current_table_name = current_table_name
    if error_summary is not None:
        job.error_summary = error_summary
    if (
        status in {SyncJobStatus.RUNNING, SyncJobStatus.FINALIZING}
        and job.start_time is None
    ):
        job.start_time = now
    if status in {
        SyncJobStatus.SUCCEEDED,
        SyncJobStatus.FAILED,
        SyncJobStatus.PARTIAL,
        SyncJobStatus.CANCELLED,
    }:
        job.finish_time = now
    job.update_time = now
    session.add(job)
    session.commit()
    session.refresh(job)
    SYNC_JOB_STATUS_TRANSITIONS.labels(status=status.value).inc()
    return job


def increment_sync_job_progress(
    session: Session,
    *,
    job: DatasourceSyncJob,
    completed_tables_delta: int = 0,
    failed_tables_delta: int = 0,
    skipped_tables_delta: int = 0,
    completed_fields_delta: int = 0,
    total_fields_delta: int = 0,
    current_table_name: str | None = None,
    force_commit: bool = False,
) -> DatasourceSyncJob:
    job.completed_tables += completed_tables_delta
    job.failed_tables += failed_tables_delta
    job.skipped_tables += skipped_tables_delta
    job.completed_fields += completed_fields_delta
    job.total_fields += total_fields_delta
    if current_table_name is not None:
        job.current_table_name = current_table_name

    now = datetime.now()
    elapsed = (now - job.update_time).total_seconds()
    should_commit = (
        force_commit
        or elapsed >= settings.DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS
    )
    if not should_commit:
        return job

    job.update_time = now
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
