from __future__ import annotations

import asyncio
import json
import time
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
from apps.datasource.models.datasource import (
    ColumnSchema,
    CoreDatasource,
    SelectedTablePayload,
)
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    SyncJobStatus,
)
from apps.db.db import build_metadata_context, get_fields_from_context
from common.core.config import settings
from common.core.db import engine
from common.observability.sync_metrics import (
    SYNC_EMBEDDING_FOLLOWUP,
    SYNC_JOB_PHASE_DURATION,
    SYNC_JOB_TABLES_FIELDS,
    SYNC_JOB_TOTAL_DURATION,
)
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

    _total_start = time.perf_counter()
    _introspect_start = time.perf_counter()
    metadata_context = build_metadata_context(ds)
    table_field_map: dict[str, list[ColumnSchema]] = {}
    total_fields = 0
    completed_fields = 0
    failed_tables = 0

    def _introspect_table(table_name: str) -> tuple[str, list[ColumnSchema]]:
        fields = get_fields_from_context(ds, metadata_context, table_name) or []
        return table_name, fields

    introspect_workers = min(
        settings.DATASOURCE_SYNC_JOB_MAX_WORKERS, len(requested_tables)
    )
    if introspect_workers > 1 and len(requested_tables) > 1:
        with ThreadPoolExecutor(max_workers=introspect_workers) as introspect_pool:
            futures = {
                introspect_pool.submit(
                    _introspect_table, item.table_name
                ): item.table_name
                for item in requested_tables
            }
            for future in futures:
                tbl_name = futures[future]
                try:
                    table_name, fields = future.result()
                    table_field_map[table_name] = fields
                    total_fields += len(fields)
                except Exception as exc:
                    failed_tables += 1
                    SQLBotLogUtil.warning(
                        f"Introspect failed for table {tbl_name}: {exc}"
                    )
    else:
        for item in requested_tables:
            try:
                table_name, fields = _introspect_table(item.table_name)
                table_field_map[table_name] = fields
                total_fields += len(fields)
            except Exception as exc:
                failed_tables += 1
                SQLBotLogUtil.warning(
                    f"Introspect failed for table {item.table_name}: {exc}"
                )
    introspect_elapsed = time.perf_counter() - _introspect_start
    SYNC_JOB_PHASE_DURATION.labels(phase="introspect").observe(introspect_elapsed)

    update_sync_job_status(
        status_session,
        job=job,
        status=SyncJobStatus.RUNNING,
        phase=SyncJobPhase.STAGE,
        total_fields=total_fields,
    )

    _stage_start = time.perf_counter()
    id_list: list[int] = []
    staged_items: list[tuple[SelectedTablePayload, list[ColumnSchema]]] = []
    bind = work_session.get_bind()
    use_sqlite_probe_stage = bind is not None and bind.dialect.name == "sqlite"
    for item in requested_tables:
        if item.table_name not in table_field_map:
            continue
        resolved_fields = table_field_map[item.table_name]
        try:
            if use_sqlite_probe_stage:
                probe_session = Session(bind=engine)
                try:
                    _reconcile_single_table(
                        session=probe_session,
                        ds=ds,
                        item=item,
                        metadata_context=metadata_context,
                        fields=resolved_fields,
                        auto_commit=False,
                    )
                    staged_items.append((item, resolved_fields))
                    completed_fields += len(resolved_fields)
                finally:
                    probe_session.rollback()
                    probe_session.close()
            else:
                with work_session.begin_nested():
                    current_table = _reconcile_single_table(
                        session=work_session,
                        ds=ds,
                        item=item,
                        metadata_context=metadata_context,
                        fields=resolved_fields,
                        auto_commit=False,
                    )
                id_list.append(current_table.id)
                completed_fields += len(resolved_fields)
        except Exception as exc:
            failed_tables += 1
            SQLBotLogUtil.warning(f"Stage failed for table {item.table_name}: {exc}")

    stage_elapsed = time.perf_counter() - _stage_start
    SYNC_JOB_PHASE_DURATION.labels(phase="stage").observe(stage_elapsed)

    completed_count = len(staged_items) if use_sqlite_probe_stage else len(id_list)
    if failed_tables > 0 and completed_count > 0:
        final_status = SyncJobStatus.PARTIAL
    elif failed_tables > 0 and completed_count == 0:
        final_status = SyncJobStatus.FAILED
    else:
        final_status = SyncJobStatus.SUCCEEDED

    if final_status != SyncJobStatus.SUCCEEDED:
        work_session.rollback()
        update_sync_job_status(
            status_session,
            job=job,
            status=final_status,
            phase=SyncJobPhase.STAGE,
            completed_tables=completed_count,
            failed_tables=failed_tables,
            completed_fields=completed_fields,
            current_table_name=None,
            error_summary=(
                f"{failed_tables} of {len(requested_tables)} tables failed during sync"
            ),
        )
        return

    if use_sqlite_probe_stage:
        for item, resolved_fields in staged_items:
            current_table = _reconcile_single_table(
                session=work_session,
                ds=ds,
                item=item,
                metadata_context=metadata_context,
                fields=resolved_fields,
                auto_commit=False,
            )
            id_list.append(current_table.id)

    _finalize_sync_table_prune(work_session, ds, id_list, auto_commit=False)
    work_session.commit()
    update_sync_job_status(
        status_session,
        job=job,
        status=final_status,
        phase=SyncJobPhase.POST_PROCESS,
        completed_tables=completed_count,
        failed_tables=failed_tables,
        completed_fields=completed_fields,
        current_table_name=None,
    )
    # Embedding follow-up is recorded separately from sync success because schema
    # publication must not be rolled back by async embedding dispatch problems.
    _post_process_start = time.perf_counter()
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
        post_process_elapsed = time.perf_counter() - _post_process_start
        total_elapsed = time.perf_counter() - _total_start
        SYNC_JOB_PHASE_DURATION.labels(phase="post_process").observe(
            post_process_elapsed
        )
        SYNC_JOB_TOTAL_DURATION.observe(total_elapsed)
        SYNC_JOB_TABLES_FIELDS.labels(metric="tables").observe(len(requested_tables))
        SYNC_JOB_TABLES_FIELDS.labels(metric="fields").observe(total_fields)
        SYNC_EMBEDDING_FOLLOWUP.labels(outcome="failed").inc()
        SQLBotLogUtil.info(
            json.dumps(
                {
                    "event": "sync_job_timing",
                    "job_id": job.id,
                    "ds_id": job.ds_id,
                    "total_tables": len(requested_tables),
                    "total_fields": total_fields,
                    "introspect_seconds": round(introspect_elapsed, 3),
                    "stage_seconds": round(stage_elapsed, 3),
                    "post_process_seconds": round(post_process_elapsed, 3),
                    "total_seconds": round(total_elapsed, 3),
                }
            )
        )
        return
    job.embedding_followup_status = "dispatched"
    status_session.add(job)
    status_session.commit()
    status_session.refresh(job)
    post_process_elapsed = time.perf_counter() - _post_process_start
    total_elapsed = time.perf_counter() - _total_start
    SYNC_JOB_PHASE_DURATION.labels(phase="post_process").observe(post_process_elapsed)
    SYNC_JOB_TOTAL_DURATION.observe(total_elapsed)
    SYNC_JOB_TABLES_FIELDS.labels(metric="tables").observe(len(requested_tables))
    SYNC_JOB_TABLES_FIELDS.labels(metric="fields").observe(total_fields)
    SYNC_EMBEDDING_FOLLOWUP.labels(outcome="dispatched").inc()
    SQLBotLogUtil.info(
        json.dumps(
            {
                "event": "sync_job_timing",
                "job_id": job.id,
                "ds_id": job.ds_id,
                "total_tables": len(requested_tables),
                "total_fields": total_fields,
                "introspect_seconds": round(introspect_elapsed, 3),
                "stage_seconds": round(stage_elapsed, 3),
                "post_process_seconds": round(post_process_elapsed, 3),
                "total_seconds": round(total_elapsed, 3),
            }
        )
    )


def run_sync_job_with_session_factory(
    session_factory: SyncJobSessionFactory,
    job_id: int,
) -> None:
    total_start = time.perf_counter()
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
            SYNC_JOB_TOTAL_DURATION.observe(time.perf_counter() - total_start)
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


async def start_periodic_stale_recovery() -> asyncio.Task[None]:
    """Start periodic stale sync job recovery as a background task."""

    async def _recovery_loop() -> None:
        interval = settings.DATASOURCE_SYNC_JOB_STALE_RECOVERY_INTERVAL_SECONDS
        while True:
            await asyncio.sleep(interval)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, recover_stale_sync_jobs, sync_job_session_maker
            )

    return asyncio.create_task(_recovery_loop())
