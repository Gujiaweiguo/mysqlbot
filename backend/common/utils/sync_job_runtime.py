from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session, col, select

from apps.datasource.crud.datasource import (
    _finalize_sync_table_prune,
    _reconcile_single_table,
    _run_sync_table_embeddings,
)
from apps.datasource.crud.sync_job import (
    get_requested_tables,
    get_sync_job_by_id,
    update_sync_job_status,
)
from apps.datasource.models.datasource import ColumnSchema, CoreDatasource
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    SyncJobStatus,
)
from apps.db.db import build_metadata_context, get_fields_from_context
from common.core.config import settings
from common.core.db import engine
from common.utils.utils import SQLBotLogUtil

sync_job_executor = ThreadPoolExecutor(
    max_workers=settings.DATASOURCE_SYNC_JOB_MAX_WORKERS
)
sync_job_session_maker = scoped_session(sessionmaker(bind=engine, class_=Session))


class SyncJobSessionFactory(Protocol):
    def __call__(self) -> Session: ...

    def remove(self) -> None: ...


def _run_sync_job_phases(session: Session, job: DatasourceSyncJob) -> None:
    update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
    )
    update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
    )
    update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.FINALIZING,
        phase=SyncJobPhase.FINALIZE,
    )
    update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.SUCCEEDED,
        phase=SyncJobPhase.FINALIZE,
    )


def _run_sync_job_with_visibility_guard(
    status_session: Session,
    work_session: Session,
    job: DatasourceSyncJob,
) -> None:
    ds = work_session.get(CoreDatasource, job.ds_id)
    if ds is None:
        raise RuntimeError("datasource not found")
    requested_tables = get_requested_tables(job)

    update_sync_job_status(
        status_session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
        total_tables=len(requested_tables),
    )

    metadata_context = build_metadata_context(ds)
    table_field_map: dict[str, list[ColumnSchema]] = {}
    total_fields = 0
    for item in requested_tables:
        fields = get_fields_from_context(ds, metadata_context, item.table_name) or []
        table_field_map[item.table_name] = fields
        total_fields += len(fields)

    update_sync_job_status(
        status_session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        total_fields=total_fields,
    )

    id_list: list[int] = []
    for item in requested_tables:
        resolved_fields = table_field_map[item.table_name]
        current_table = _reconcile_single_table(
            session=work_session,
            ds=ds,
            item=item,
            metadata_context=metadata_context,
            fields=resolved_fields,
            auto_commit=False,
        )
        id_list.append(current_table.id)
    # Publish schema changes only once at the end so previously visible metadata
    # remains stable until the transaction commits successfully.
    _finalize_sync_table_prune(work_session, ds, id_list, auto_commit=False)
    work_session.commit()
    update_sync_job_status(
        status_session,
        job=job,
        status=SyncJobStatus.SUCCEEDED,
        phase=SyncJobPhase.POST_PROCESS,
        completed_tables=len(requested_tables),
        completed_fields=total_fields,
        current_table_name=None,
    )
    # Embedding follow-up is recorded separately from sync success because schema
    # publication must not be rolled back by async embedding dispatch problems.
    try:
        _run_sync_table_embeddings(ds, id_list)
    except Exception as exc:
        job.embedding_followup_status = "failed"
        status_session.add(job)
        status_session.commit()
        status_session.refresh(job)
        SQLBotLogUtil.warning(
            f"Post-sync embedding dispatch failed for job {job.id}: {exc}"
        )
        return
    job.embedding_followup_status = "dispatched"
    status_session.add(job)
    status_session.commit()
    status_session.refresh(job)


def run_sync_job_with_session_factory(
    session_factory: SyncJobSessionFactory,
    job_id: int,
) -> None:
    session = session_factory()
    work_session = Session(bind=engine)
    try:
        job = get_sync_job_by_id(session, job_id)
        if job is None or job.status != SyncJobStatus.PENDING:
            return
        try:
            _run_sync_job_with_visibility_guard(session, work_session, job)
        except Exception as exc:
            work_session.rollback()
            update_sync_job_status(
                session,
                job=job,
                status=SyncJobStatus.FAILED,
                phase=job.phase,
                error_summary=str(exc),
            )
    finally:
        work_session.close()
        session.close()
        session_factory.remove()


def dispatch_sync_job(job_id: int) -> Future[None]:
    return sync_job_executor.submit(
        run_sync_job_with_session_factory, sync_job_session_maker, job_id
    )


def recover_stale_sync_jobs(
    session_factory: SyncJobSessionFactory,
) -> list[int]:
    session = session_factory()
    try:
        threshold = datetime.now() - timedelta(
            seconds=settings.DATASOURCE_SYNC_JOB_STALE_TIMEOUT_SECONDS
        )
        statement = (
            select(DatasourceSyncJob)
            .where(
                col(DatasourceSyncJob.status).in_(
                    [SyncJobStatus.RUNNING.value, SyncJobStatus.FINALIZING.value]
                )
            )
            .where(col(DatasourceSyncJob.update_time) < threshold)
        )
        jobs = list(session.exec(statement).all())
        recovered_ids: list[int] = []
        for job in jobs:
            update_sync_job_status(
                session,
                job=job,
                status=SyncJobStatus.FAILED,
                phase=job.phase,
                error_summary="sync job marked failed after stale timeout",
            )
            if job.id is not None:
                recovered_ids.append(job.id)
        return recovered_ids
    finally:
        session.close()
        session_factory.remove()
