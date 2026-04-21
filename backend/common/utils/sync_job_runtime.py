from __future__ import annotations

# pyright: reportPrivateUsage=false, reportUnnecessaryComparison=false, reportUnusedFunction=false

import asyncio
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import BoundedSemaphore, Lock
from typing import Protocol, TypeVar, cast

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session, col, select

from apps.datasource.constants.sync import (
    ACTIVE_DATASOURCE_SYNC_JOB_STATUSES,
    SYNC_BATCH_SIZE,
    SYNC_EMBEDDING_CHUNK_SIZE,
    SYNC_FIELD_BATCH_SIZE,
    SYNC_JOB_MAX_WORKERS,
    SYNC_JOB_STALE_TIMEOUT_SECONDS,
)
from apps.datasource.crud.sync_job import (
    get_requested_tables,
    get_sync_job_by_id,
    increment_sync_job_progress,
    update_sync_job_status,
)
from apps.datasource.models.datasource import CoreDatasource, SelectedTablePayload
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    SyncJobStatus,
)
from apps.datasource.services.sync_engine import (
    IntrospectedTableSchema,
    SyncJobContext,
    finalize_sync,
    introspect_remote_metadata,
    post_process_embeddings,
    snapshot_requested_tables,
    stage_table_batch,
)
from apps.db.db import DatasourceMetadataContext
from common.core.config import settings
from common.core.db import engine
from common.observability.sync_metrics import SYNC_JOB_TOTAL_DURATION
from common.utils.utils import SQLBotLogUtil

sync_job_executor = ThreadPoolExecutor(max_workers=SYNC_JOB_MAX_WORKERS)
sync_job_session_maker = scoped_session(sessionmaker(bind=engine, class_=Session))
sync_job_worker_limiter = BoundedSemaphore(value=SYNC_JOB_MAX_WORKERS)

_datasource_lock_guard = Lock()
_datasource_locks: dict[int, Lock] = {}


class SyncJobSessionFactory(Protocol):
    def __call__(self) -> Session: ...

    def remove(self) -> None: ...


class TransactionLike(Protocol):
    is_active: bool

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


def _get_datasource_lock(ds_id: int) -> Lock:
    with _datasource_lock_guard:
        lock = _datasource_locks.get(ds_id)
        if lock is None:
            lock = Lock()
            _datasource_locks[ds_id] = lock
        return lock


def _active_jobs_for_datasource(
    session: Session,
    *,
    ds_id: int,
    exclude_job_id: int | None = None,
) -> list[DatasourceSyncJob]:
    statement = (
        select(DatasourceSyncJob)
        .where(col(DatasourceSyncJob.ds_id) == ds_id)
        .where(
            col(DatasourceSyncJob.status).in_(
                [status.value for status in ACTIVE_DATASOURCE_SYNC_JOB_STATUSES]
            )
        )
        .order_by(col(DatasourceSyncJob.create_time).asc())
    )
    jobs = list(session.exec(statement).all())
    if exclude_job_id is None:
        return jobs
    return [job for job in jobs if job.id != exclude_job_id]


def _is_job_stale(job: DatasourceSyncJob, *, now: datetime | None = None) -> bool:
    reference = now or datetime.now()
    return job.update_time < reference - timedelta(seconds=SYNC_JOB_STALE_TIMEOUT_SECONDS)


def _mark_job_failed(
    session: Session,
    *,
    job: DatasourceSyncJob,
    phase: SyncJobPhase | None,
    error_summary: str,
) -> DatasourceSyncJob:
    return update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.FAILED,
        phase=phase,
        current_table_name=None,
        error_summary=error_summary,
    )


def _recover_stale_jobs_in_session(
    session: Session,
    *,
    ds_id: int | None = None,
    exclude_job_id: int | None = None,
) -> list[int]:
    """Mark stale RUNNING/FINALIZING jobs as FAILED so new jobs can proceed.

    Stale detection uses ``SYNC_JOB_STALE_TIMEOUT_SECONDS`` (default 1h). A job
    whose ``update_time`` is older than *now - stale_timeout* is considered
    orphaned (e.g. the worker process crashed mid-sync). Recovery runs at job
    dispatch time inside the datasource lock, and periodically via
    ``start_periodic_stale_recovery``.
    """
    statement = select(DatasourceSyncJob).where(
        col(DatasourceSyncJob.status).in_(
            [SyncJobStatus.RUNNING.value, SyncJobStatus.FINALIZING.value]
        )
    )
    if ds_id is not None:
        statement = statement.where(col(DatasourceSyncJob.ds_id) == ds_id)
    jobs = list(session.exec(statement).all())
    recovered_ids: list[int] = []
    for job in jobs:
        if exclude_job_id is not None and job.id == exclude_job_id:
            continue
        if not _is_job_stale(job):
            continue
        _ = _mark_job_failed(
            session,
            job=job,
            phase=job.phase,
            error_summary="sync job marked failed after stale timeout",
        )
        if job.id is not None:
            recovered_ids.append(job.id)
    return recovered_ids


def _refresh_job(session: Session, job_id: int) -> DatasourceSyncJob:
    job = get_sync_job_by_id(session, job_id)
    if job is None:
        raise RuntimeError("sync job not found")
    return job


def _ensure_not_cancelled(session: Session, job_id: int) -> DatasourceSyncJob:
    job = _refresh_job(session, job_id)
    if job.status == SyncJobStatus.CANCELLED:
        raise RuntimeError("sync job cancelled")
    return job


def _build_partial_summary(failed_tables: int, total_tables: int) -> str:
    return f"{failed_tables} of {total_tables} tables failed during sync"


T = TypeVar("T")


def _batched(items: list[T], batch_size: int) -> list[list[T]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def _rollback_work_session(work_session: Session) -> None:
    outer_transaction = cast(
        TransactionLike | None, work_session.info.get("outer_transaction")
    )
    if outer_transaction is not None and outer_transaction.is_active:
        outer_transaction.rollback()
        return
    work_session.rollback()


def _commit_work_session(work_session: Session) -> None:
    outer_transaction = cast(
        TransactionLike | None, work_session.info.get("outer_transaction")
    )
    if outer_transaction is not None and outer_transaction.is_active:
        outer_transaction.commit()
        return
    work_session.commit()


def _build_session_context(
    session: Session,
    *,
    job_id: int,
    ds_id: int,
    requested_tables: list[SelectedTablePayload],
    metadata_context: DatasourceMetadataContext,
) -> SyncJobContext:
    session_job = get_sync_job_by_id(session, job_id)
    if session_job is None:
        raise RuntimeError("sync job not found")
    session_ds = session.get(CoreDatasource, ds_id)
    if session_ds is None:
        raise RuntimeError("datasource not found")
    return SyncJobContext.from_job(
        ds=session_ds,
        job=session_job,
        requested_tables=requested_tables,
        metadata_context=metadata_context,
    )


def _probe_stage_batch(
    *,
    job_id: int,
    ds_id: int,
    requested_tables: list[SelectedTablePayload],
    metadata_context: DatasourceMetadataContext,
    introspected_batch: list[IntrospectedTableSchema],
) -> None:
    probe_connection = engine.connect()
    probe_transaction = probe_connection.begin()
    probe_session = Session(bind=probe_connection)
    probe_session.info["outer_transaction"] = probe_transaction
    try:
        probe_context = _build_session_context(
            probe_session,
            job_id=job_id,
            ds_id=ds_id,
            requested_tables=requested_tables,
            metadata_context=metadata_context,
        )
        _ = stage_table_batch(
            probe_session,
            probe_context,
            introspected_batch,
            batch_size=SYNC_BATCH_SIZE,
            field_batch_size=SYNC_FIELD_BATCH_SIZE,
        )
    finally:
        if probe_transaction.is_active:
            probe_transaction.rollback()
        probe_session.close()
        probe_connection.close()


def _job_is_cancelled(status_session: Session, job: DatasourceSyncJob) -> bool:
    status_session.refresh(job)
    return job.status == SyncJobStatus.CANCELLED


def _run_sync_job_with_visibility_guard(
    status_session: Session,
    work_session: Session,
    job: DatasourceSyncJob,
) -> None:
    ds = work_session.get(CoreDatasource, job.ds_id)
    if ds is None:
        raise RuntimeError("datasource not found")

    requested_tables = get_requested_tables(job)
    context = SyncJobContext.from_job(
        ds=ds,
        job=job,
        requested_tables=requested_tables,
    )
    _ = snapshot_requested_tables(status_session, context)
    job_id = cast(object, job.id)
    if not isinstance(job_id, int):
        raise RuntimeError("sync job not found")

    if _job_is_cancelled(status_session, job):
        _rollback_work_session(work_session)
        return

    _ = update_sync_job_status(
        status_session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
        total_tables=len(requested_tables),
    )

    introspected_tables: list[IntrospectedTableSchema] = []
    introspected_by_table: dict[str, IntrospectedTableSchema] = {}
    failed_tables = 0
    total_fields = 0
    failure_messages: list[str] = []

    for table_batch in _batched(requested_tables, SYNC_BATCH_SIZE):
        job = _ensure_not_cancelled(status_session, job_id)
        try:
            batch_introspected = introspect_remote_metadata(context, tables=table_batch)
        except Exception as exc:
            if len(table_batch) == 1:
                table = table_batch[0]
                failed_tables += 1
                failure_messages.append(f"introspect:{table.table_name}:{exc}")
                SQLBotLogUtil.warning(
                    f"Introspect failed for table {table.table_name}: {exc}"
                )
                _ = increment_sync_job_progress(
                    status_session,
                    job=job,
                    failed_tables_delta=1,
                    current_table_name=table.table_name,
                    force_commit=True,
                )
                continue

            for table in table_batch:
                job = _ensure_not_cancelled(status_session, job_id)
                try:
                    single_table_result = introspect_remote_metadata(context, tables=[table])
                except Exception as table_exc:
                    failed_tables += 1
                    failure_messages.append(
                        f"introspect:{table.table_name}:{table_exc}"
                    )
                    SQLBotLogUtil.warning(
                        f"Introspect failed for table {table.table_name}: {table_exc}"
                    )
                    _ = increment_sync_job_progress(
                        status_session,
                        job=job,
                        failed_tables_delta=1,
                        current_table_name=table.table_name,
                        force_commit=True,
                    )
                    continue

                introspected_tables.extend(single_table_result)
                introspected_by_table.update(
                    {item.table.table_name: item for item in single_table_result}
                )
                total_fields += sum(len(item.fields) for item in single_table_result)
                _ = update_sync_job_status(
                    status_session,
                    job=job,
                    status=SyncJobStatus.RUNNING,
                    phase=SyncJobPhase.INTROSPECT,
                    total_tables=len(requested_tables),
                    failed_tables=failed_tables,
                    total_fields=total_fields,
                    current_table_name=table.table_name,
                )
            continue

        introspected_tables.extend(batch_introspected)
        introspected_by_table.update(
            {item.table.table_name: item for item in batch_introspected}
        )
        total_fields += sum(len(item.fields) for item in batch_introspected)
        _ = update_sync_job_status(
            status_session,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.INTROSPECT,
            total_tables=len(requested_tables),
            failed_tables=failed_tables,
            total_fields=total_fields,
            current_table_name=batch_introspected[-1].table.table_name,
        )

    if _job_is_cancelled(status_session, job):
        _rollback_work_session(work_session)
        return

    _ = update_sync_job_status(
        status_session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        total_tables=len(requested_tables),
        failed_tables=failed_tables,
        total_fields=total_fields,
        current_table_name=None,
    )

    completed_tables = 0
    completed_fields = 0

    for introspected_batch in _batched(introspected_tables, SYNC_BATCH_SIZE):
        job = _ensure_not_cancelled(status_session, job_id)
        try:
            _probe_stage_batch(
                job_id=job_id,
                ds_id=job.ds_id,
                requested_tables=requested_tables,
                metadata_context=context.metadata_context,
                introspected_batch=introspected_batch,
            )
        except Exception as exc:
            if len(introspected_batch) == 1:
                failed_item = introspected_batch[0]
                failed_tables += 1
                failure_messages.append(
                    f"stage:{failed_item.table.table_name}:{exc}"
                )
                SQLBotLogUtil.warning(
                    f"Stage failed for table {failed_item.table.table_name}: {exc}"
                )
                _ = increment_sync_job_progress(
                    status_session,
                    job=job,
                    failed_tables_delta=1,
                    current_table_name=failed_item.table.table_name,
                    force_commit=True,
                )
                continue

            for introspected_item in introspected_batch:
                job = _ensure_not_cancelled(status_session, job_id)
                try:
                    _probe_stage_batch(
                        job_id=job_id,
                        ds_id=job.ds_id,
                        requested_tables=requested_tables,
                        metadata_context=context.metadata_context,
                        introspected_batch=[introspected_item],
                    )
                except Exception as table_exc:
                    failed_tables += 1
                    failure_messages.append(
                        f"stage:{introspected_item.table.table_name}:{table_exc}"
                    )
                    SQLBotLogUtil.warning(
                        f"Stage failed for table {introspected_item.table.table_name}: {table_exc}"
                    )
                    _ = increment_sync_job_progress(
                        status_session,
                        job=job,
                        failed_tables_delta=1,
                        current_table_name=introspected_item.table.table_name,
                        force_commit=True,
                    )
                    continue

                completed_tables += 1
                completed_fields += len(introspected_item.fields)
                _ = update_sync_job_status(
                    status_session,
                    job=job,
                    status=SyncJobStatus.RUNNING,
                    phase=SyncJobPhase.STAGE,
                    total_tables=len(requested_tables),
                    completed_tables=completed_tables,
                    failed_tables=failed_tables,
                    total_fields=total_fields,
                    completed_fields=completed_fields,
                    current_table_name=introspected_item.table.table_name,
                )
            continue

        completed_tables += len(introspected_batch)
        completed_fields += sum(len(item.fields) for item in introspected_batch)
        _ = update_sync_job_status(
            status_session,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            total_tables=len(requested_tables),
            completed_tables=completed_tables,
            failed_tables=failed_tables,
            total_fields=total_fields,
            completed_fields=completed_fields,
            current_table_name=introspected_batch[-1].table.table_name,
        )

    # All tables failed during introspect/stage: nothing to publish, roll back
    # the work transaction so the previously visible schema stays untouched.
    if failed_tables > 0 and completed_tables == 0:
        _rollback_work_session(work_session)
        _ = update_sync_job_status(
            status_session,
            job=job,
            status=SyncJobStatus.FAILED,
            phase=SyncJobPhase.STAGE,
            completed_tables=0,
            failed_tables=failed_tables,
            total_tables=len(requested_tables),
            total_fields=total_fields,
            completed_fields=0,
            current_table_name=None,
            error_summary=_build_partial_summary(failed_tables, len(requested_tables)),
        )
        return

    # Partial success: some tables staged but others failed. Roll back the work
    # transaction so the partially-staged schema does NOT become visible. The
    # existing schema remains unchanged, which is safer than publishing a
    # partial state that may confuse downstream consumers.
    if failed_tables > 0:
        _rollback_work_session(work_session)
        _ = update_sync_job_status(
            status_session,
            job=job,
            status=SyncJobStatus.PARTIAL,
            phase=SyncJobPhase.STAGE,
            completed_tables=completed_tables,
            failed_tables=failed_tables,
            total_tables=len(requested_tables),
            total_fields=total_fields,
            completed_fields=completed_fields,
            current_table_name=None,
            error_summary=_build_partial_summary(failed_tables, len(requested_tables)),
        )
        return

    job = _ensure_not_cancelled(status_session, job_id)
    _ = update_sync_job_status(
        status_session,
        job=job,
        status=SyncJobStatus.FINALIZING,
        phase=SyncJobPhase.FINALIZE,
        total_tables=len(requested_tables),
        completed_tables=completed_tables,
        failed_tables=failed_tables,
        total_fields=total_fields,
        completed_fields=completed_fields,
        current_table_name=None,
    )

    stage_context = _build_session_context(
        work_session,
        job_id=job_id,
        ds_id=job.ds_id,
        requested_tables=requested_tables,
        metadata_context=context.metadata_context,
    )
    staged_table_ids: list[int] = []
    ordered_introspected_tables = [
        introspected_by_table[requested_table.table_name]
        for requested_table in requested_tables
        if requested_table.table_name in introspected_by_table
    ]
    for stage_batch in _batched(ordered_introspected_tables, SYNC_BATCH_SIZE):
        if _job_is_cancelled(status_session, job):
            _rollback_work_session(work_session)
            return
        stage_result = stage_table_batch(
            work_session,
            stage_context,
            stage_batch,
            batch_size=SYNC_BATCH_SIZE,
            field_batch_size=SYNC_FIELD_BATCH_SIZE,
        )
        staged_table_ids.extend(stage_result.table_ids)

    finalize_context = _build_session_context(
        work_session,
        job_id=job_id,
        ds_id=job.ds_id,
        requested_tables=requested_tables,
        metadata_context=context.metadata_context,
    )
    _ = finalize_sync(work_session, finalize_context, staged_table_ids=staged_table_ids)
    _commit_work_session(work_session)

    job = _ensure_not_cancelled(status_session, job_id)
    post_process_context = SyncJobContext.from_job(
        ds=ds,
        job=job,
        requested_tables=requested_tables,
        metadata_context=context.metadata_context,
    )
    post_result = post_process_embeddings(
        status_session,
        post_process_context,
        table_ids=staged_table_ids,
        chunk_size=SYNC_EMBEDDING_CHUNK_SIZE,
    )
    _ = update_sync_job_status(
        status_session,
        job=_refresh_job(status_session, job_id),
        status=SyncJobStatus.SUCCEEDED,
        phase=post_result.phase,
        total_tables=len(requested_tables),
        completed_tables=completed_tables,
        failed_tables=failed_tables,
        total_fields=total_fields,
        completed_fields=completed_fields,
        current_table_name=None,
        error_summary=None,
    )


def _run_sync_job(session: Session, job_id: int) -> None:
    job = _refresh_job(session, job_id)
    ds = session.get(CoreDatasource, job.ds_id)
    if ds is None:
        raise RuntimeError("datasource not found")

    requested_tables = get_requested_tables(job)
    context = SyncJobContext.from_job(ds=ds, job=job, requested_tables=requested_tables)
    _ = snapshot_requested_tables(session, context)

    job = _refresh_job(session, job_id)
    context = SyncJobContext.from_job(
        ds=ds,
        job=job,
        requested_tables=requested_tables,
        metadata_context=context.metadata_context,
    )
    _ = update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.INTROSPECT,
        total_tables=len(requested_tables),
        completed_tables=0,
        failed_tables=0,
        total_fields=0,
        completed_fields=0,
        current_table_name=None,
        error_summary=None,
    )

    introspected_tables: list[IntrospectedTableSchema] = []
    total_fields = 0
    failed_tables = 0
    failure_messages: list[str] = []

    for table in requested_tables:
        job = _ensure_not_cancelled(session, job_id)
        try:
            introspected_batch = introspect_remote_metadata(context, tables=[table])
        except Exception as exc:
            failed_tables += 1
            failure_messages.append(f"introspect:{table.table_name}:{exc}")
            _ = increment_sync_job_progress(
                session,
                job=job,
                failed_tables_delta=1,
                current_table_name=table.table_name,
                force_commit=True,
            )
            continue

        introspected_tables.extend(introspected_batch)
        total_fields += sum(len(item.fields) for item in introspected_batch)
        _ = update_sync_job_status(
            session,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.INTROSPECT,
            total_tables=len(requested_tables),
            failed_tables=failed_tables,
            total_fields=total_fields,
            current_table_name=table.table_name,
        )

    job = _ensure_not_cancelled(session, job_id)
    _ = update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        total_tables=len(requested_tables),
        failed_tables=failed_tables,
        total_fields=total_fields,
        current_table_name=None,
    )

    completed_tables = 0
    completed_fields = 0
    staged_table_ids: list[int] = []

    for introspected in introspected_tables:
        job = _ensure_not_cancelled(session, job_id)
        stage_context = SyncJobContext.from_job(
            ds=ds,
            job=job,
            requested_tables=requested_tables,
            metadata_context=context.metadata_context,
        )
        try:
            stage_result = stage_table_batch(
                session,
                stage_context,
                [introspected],
                batch_size=1,
                field_batch_size=SYNC_FIELD_BATCH_SIZE,
            )
        except Exception as exc:
            session.rollback()
            failed_tables += 1
            failure_messages.append(f"stage:{introspected.table.table_name}:{exc}")
            job = _refresh_job(session, job_id)
            _ = update_sync_job_status(
                session,
                job=job,
                status=SyncJobStatus.RUNNING,
                phase=SyncJobPhase.STAGE,
                total_tables=len(requested_tables),
                completed_tables=completed_tables,
                failed_tables=failed_tables,
                total_fields=total_fields,
                completed_fields=completed_fields,
                current_table_name=introspected.table.table_name,
            )
            continue

        staged_table_ids.extend(stage_result.table_ids)
        completed_tables += stage_result.completed_tables
        completed_fields += stage_result.completed_fields
        job = _refresh_job(session, job_id)
        _ = update_sync_job_status(
            session,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            total_tables=len(requested_tables),
            completed_tables=completed_tables,
            failed_tables=failed_tables,
            total_fields=total_fields,
            completed_fields=completed_fields,
            current_table_name=introspected.table.table_name,
        )

    job = _ensure_not_cancelled(session, job_id)
    if not staged_table_ids and failed_tables > 0:
        error_summary = failure_messages[0] if failure_messages else "sync job failed"
        _ = _mark_job_failed(
            session,
            job=job,
            phase=SyncJobPhase.STAGE,
            error_summary=error_summary,
        )
        return

    _ = update_sync_job_status(
        session,
        job=job,
        status=SyncJobStatus.FINALIZING,
        phase=SyncJobPhase.FINALIZE,
        total_tables=len(requested_tables),
        completed_tables=completed_tables,
        failed_tables=failed_tables,
        total_fields=total_fields,
        completed_fields=completed_fields,
        current_table_name=None,
    )

    finalize_context = SyncJobContext.from_job(
        ds=ds,
        job=job,
        requested_tables=requested_tables,
        metadata_context=context.metadata_context,
    )
    _ = finalize_sync(session, finalize_context, staged_table_ids=staged_table_ids)

    job = _ensure_not_cancelled(session, job_id)
    post_process_context = SyncJobContext.from_job(
        ds=ds,
        job=job,
        requested_tables=requested_tables,
        metadata_context=context.metadata_context,
    )
    post_result = post_process_embeddings(
        session,
        post_process_context,
        table_ids=staged_table_ids,
        chunk_size=SYNC_EMBEDDING_CHUNK_SIZE,
    )

    final_status = (
        SyncJobStatus.PARTIAL if failed_tables > 0 else SyncJobStatus.SUCCEEDED
    )
    _ = update_sync_job_status(
        session,
        job=_refresh_job(session, job_id),
        status=final_status,
        phase=post_result.phase,
        total_tables=len(requested_tables),
        completed_tables=completed_tables,
        failed_tables=failed_tables,
        total_fields=total_fields,
        completed_fields=completed_fields,
        current_table_name=None,
        error_summary=(
            _build_partial_summary(failed_tables, len(requested_tables))
            if final_status == SyncJobStatus.PARTIAL
            else None
        ),
    )


def _run_job_with_datasource_lock(
    session: Session,
    work_session: Session,
    job_id: int,
) -> None:
    """Acquire per-datasource lock, recover stale jobs, then run the sync.

    Only one sync job per datasource can be active at a time. Stale jobs
    (RUNNING/FINALIZING past the timeout) are recovered before checking for
    blockers, so a crashed worker doesn't permanently block new submissions.
    """
    job = get_sync_job_by_id(session, job_id)
    if job is None:
        return
    datasource_lock = _get_datasource_lock(job.ds_id)
    with datasource_lock:
        job = get_sync_job_by_id(session, job_id)
        if job is None or job.status != SyncJobStatus.PENDING:
            return

        _ = _recover_stale_jobs_in_session(
            session,
            ds_id=job.ds_id,
            exclude_job_id=job.id,
        )
        blockers = _active_jobs_for_datasource(
            session,
            ds_id=job.ds_id,
            exclude_job_id=job.id,
        )
        if blockers:
            _ = _mark_job_failed(
                session,
                job=job,
                phase=job.phase,
                error_summary="another active sync job is already running for this datasource",
            )
            return

        _run_sync_job_with_visibility_guard(session, work_session, job)


def run_sync_job_with_session_factory(
    session_factory: SyncJobSessionFactory,
    job_id: int,
) -> None:
    total_start = time.perf_counter()
    _ = sync_job_worker_limiter.acquire()
    session = session_factory()
    work_connection = engine.connect()
    work_transaction = work_connection.begin()
    work_session = Session(bind=work_connection)
    work_session.info["outer_transaction"] = work_transaction
    try:
        try:
            _run_job_with_datasource_lock(session, work_session, job_id)
        except RuntimeError as exc:
            _rollback_work_session(work_session)
            if str(exc) != "sync job cancelled":
                job = get_sync_job_by_id(session, job_id)
                if job is not None and job.status in {
                    SyncJobStatus.PENDING,
                    SyncJobStatus.RUNNING,
                    SyncJobStatus.FINALIZING,
                }:
                    _ = _mark_job_failed(
                        session,
                        job=job,
                        phase=job.phase,
                        error_summary=str(exc),
                    )
        except Exception as exc:
            _rollback_work_session(work_session)
            session.rollback()
            job = get_sync_job_by_id(session, job_id)
            if job is not None and job.status in {
                SyncJobStatus.PENDING,
                SyncJobStatus.RUNNING,
                SyncJobStatus.FINALIZING,
            }:
                _ = _mark_job_failed(
                    session,
                    job=job,
                    phase=job.phase,
                    error_summary=str(exc),
                )

        job = get_sync_job_by_id(session, job_id)
        if job is not None and job.status in {
            SyncJobStatus.SUCCEEDED,
            SyncJobStatus.FAILED,
            SyncJobStatus.PARTIAL,
            SyncJobStatus.CANCELLED,
        }:
            SYNC_JOB_TOTAL_DURATION.observe(time.perf_counter() - total_start)
    finally:
        if work_transaction.is_active:
            work_transaction.rollback()
        work_session.close()
        work_connection.close()
        session.close()
        session_factory.remove()
        sync_job_worker_limiter.release()


def dispatch_sync_job(job_id: int) -> Future[None]:
    return sync_job_executor.submit(
        run_sync_job_with_session_factory, sync_job_session_maker, job_id
    )


def recover_stale_sync_jobs(
    session_factory: SyncJobSessionFactory,
) -> list[int]:
    session = session_factory()
    try:
        return _recover_stale_jobs_in_session(session)
    finally:
        session.close()
        session_factory.remove()


async def start_periodic_stale_recovery() -> asyncio.Task[None]:
    async def _recovery_loop() -> None:
        interval = settings.DATASOURCE_SYNC_JOB_STALE_RECOVERY_INTERVAL_SECONDS
        while True:
            await asyncio.sleep(interval)
            loop = asyncio.get_running_loop()
            _ = await loop.run_in_executor(
                None, recover_stale_sync_jobs, sync_job_session_maker
            )

    return asyncio.create_task(_recovery_loop())
