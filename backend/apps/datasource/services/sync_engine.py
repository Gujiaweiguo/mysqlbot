from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import HTTPException
from sqlalchemy import and_, delete, text
from sqlmodel import Session, col, select

from apps.datasource.constants.sync import (
    SYNC_BATCH_SIZE,
    SYNC_EMBEDDING_CHUNK_SIZE,
    SYNC_FIELD_BATCH_SIZE,
)
from apps.datasource.models.datasource import (
    ColumnSchema,
    CoreDatasource,
    CoreField,
    CoreTable,
    SelectedTablePayload,
)
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    dump_selected_tables_payload,
)
from apps.db.constant import ConnectType
from apps.db.db import (
    DatasourceMetadataContext,
    build_metadata_context,
    get_fields_from_context,
)
from apps.db.db_sql import get_field_sql
from common.utils.embedding_threads import (
    run_save_ds_embeddings,
    run_save_table_embeddings,
)


def _allocate_sqlite_identity(session: Session, model: type[CoreTable] | type[CoreField]) -> int:
    statement = select(model.id).order_by(col(model.id).desc())
    latest_id = session.exec(statement).first()
    if latest_id is None:
        return 1
    return latest_id + 1


def _assign_sqlite_identity(session: Session, record: CoreTable | CoreField) -> None:
    bind = session.get_bind()
    if bind.dialect.name != "sqlite":
        return
    if isinstance(record, CoreTable):
        record.id = _allocate_sqlite_identity(session, CoreTable)
        return
    record.id = _allocate_sqlite_identity(session, CoreField)


@dataclass(slots=True)
class SyncJobContext:
    ds: CoreDatasource
    job: DatasourceSyncJob
    requested_tables: list[SelectedTablePayload]
    metadata_context: DatasourceMetadataContext

    @classmethod
    def from_job(
        cls,
        *,
        ds: CoreDatasource,
        job: DatasourceSyncJob,
        requested_tables: list[SelectedTablePayload],
        metadata_context: DatasourceMetadataContext | None = None,
    ) -> "SyncJobContext":
        return cls(
            ds=ds,
            job=job,
            requested_tables=requested_tables,
            metadata_context=metadata_context or build_metadata_context(ds),
        )


@dataclass(slots=True)
class SnapshotResult:
    phase: SyncJobPhase
    requested_table_count: int


@dataclass(slots=True)
class IntrospectedTableSchema:
    table: SelectedTablePayload
    fields: list[ColumnSchema]


@dataclass(slots=True)
class StageBatchResult:
    phase: SyncJobPhase
    table_ids: list[int]
    total_fields: int
    completed_tables: int
    completed_fields: int
    commit_count: int


@dataclass(slots=True)
class PostProcessResult:
    phase: SyncJobPhase
    dispatched_table_ids: list[int]
    chunk_count: int


def snapshot_requested_tables(
    session: Session,
    context: SyncJobContext,
) -> SnapshotResult:
    context.job.phase = SyncJobPhase.SUBMIT
    context.job.requested_tables = dump_selected_tables_payload(context.requested_tables)
    context.job.total_tables = len(context.requested_tables)
    session.add(context.job)
    session.commit()
    session.refresh(context.job)
    return SnapshotResult(
        phase=SyncJobPhase.SUBMIT,
        requested_table_count=len(context.requested_tables),
    )


def introspect_remote_metadata(
    context: SyncJobContext,
    *,
    tables: list[SelectedTablePayload] | None = None,
) -> list[IntrospectedTableSchema]:
    requested_tables = tables if tables is not None else context.requested_tables
    if (
        context.metadata_context.connect_type == ConnectType.sqlalchemy
        and context.metadata_context.session_factory is not None
    ):
        return _introspect_sqlalchemy_batch(context, requested_tables)

    return [
        IntrospectedTableSchema(
            table=item,
            fields=list(
                get_fields_from_context(
                    context.ds,
                    context.metadata_context,
                    item.table_name,
                )
                or []
            ),
        )
        for item in requested_tables
    ]


def _introspect_sqlalchemy_batch(
    context: SyncJobContext,
    tables: list[SelectedTablePayload],
) -> list[IntrospectedTableSchema]:
    session_factory = context.metadata_context.session_factory
    if session_factory is None:
        raise RuntimeError("Datasource metadata context is missing session factory")
    results: list[IntrospectedTableSchema] = []
    with session_factory() as remote_session:
        for item in tables:
            table_sql, param1, param2 = get_field_sql(
                context.ds,
                context.metadata_context.conf,
                item.table_name,
            )
            with remote_session.execute(
                text(table_sql), {"param1": param1, "param2": param2}
            ) as query_result:
                rows = cast(list[tuple[str, str, str | None]], query_result.fetchall())
            results.append(
                IntrospectedTableSchema(
                    table=item,
                    fields=[ColumnSchema(*row) for row in rows],
                )
            )
    return results


def stage_table_batch(
    session: Session,
    context: SyncJobContext,
    introspected_tables: list[IntrospectedTableSchema],
    *,
    batch_size: int = SYNC_BATCH_SIZE,
    field_batch_size: int = SYNC_FIELD_BATCH_SIZE,
) -> StageBatchResult:
    """Write introspected table+field rows into the local catalog.

    Batching boundary is the table chunk, not individual fields. Each chunk of
    ``batch_size`` tables is committed together so that partial progress survives
    a mid-batch crash. Within a chunk, field inserts are flushed in sub-batches
    of ``field_batch_size`` to obtain primary keys before stale-field pruning,
    but the outer commit happens once per table chunk.
    """
    ds_id = cast(object, context.ds.id)
    if not isinstance(ds_id, int):
        raise HTTPException(status_code=500, detail="datasource not found")

    context.job.phase = SyncJobPhase.STAGE
    session.add(context.job)

    table_ids: list[int] = []
    total_fields = 0
    completed_fields = 0
    commit_count = 0

    for start in range(0, len(introspected_tables), batch_size):
        chunk = introspected_tables[start : start + batch_size]
        for item in chunk:
            current_table = _upsert_table(session, ds_id=ds_id, item=item.table)
            table_ids.append(current_table.id)
            fields_written = _stage_fields(
                session,
                ds_id=ds_id,
                table_id=current_table.id,
                fields=item.fields,
                field_batch_size=field_batch_size,
            )
            total_fields += len(item.fields)
            completed_fields += fields_written
            context.job.completed_tables = len(table_ids)
            context.job.completed_fields = completed_fields
            context.job.total_fields = total_fields
            context.job.current_table_name = item.table.table_name
            session.add(context.job)
        session.commit()
        commit_count += 1
        session.refresh(context.job)

    return StageBatchResult(
        phase=SyncJobPhase.STAGE,
        table_ids=table_ids,
        total_fields=total_fields,
        completed_tables=len(table_ids),
        completed_fields=completed_fields,
        commit_count=commit_count,
    )


def _upsert_table(
    session: Session,
    *,
    ds_id: int,
    item: SelectedTablePayload,
) -> CoreTable:
    statement = select(CoreTable).where(
        and_(col(CoreTable.ds_id) == ds_id, col(CoreTable.table_name) == item.table_name)
    )
    record = session.exec(statement).first()
    if record is not None:
        record.table_comment = item.table_comment
        record.custom_comment = item.table_comment
        session.add(record)
        return record

    table = CoreTable(
        id=0,
        ds_id=ds_id,
        checked=True,
        table_name=item.table_name,
        table_comment=item.table_comment,
        custom_comment=item.table_comment,
        embedding=None,
    )
    object.__setattr__(table, "id", None)
    _assign_sqlite_identity(session, table)
    session.add(table)
    session.flush()
    session.refresh(table)
    table_id = cast(object, getattr(table, "id", None))
    if not isinstance(table_id, int):
        raise HTTPException(status_code=500, detail="table create failed")
    return table


def _stage_fields(
    session: Session,
    *,
    ds_id: int,
    table_id: int,
    fields: list[ColumnSchema],
    field_batch_size: int,
) -> int:
    existing_fields = {
        field.field_name: field
        for field in session.exec(
            select(CoreField).where(col(CoreField.table_id) == table_id)
        ).all()
    }

    retained_ids: list[int] = []
    pending_creates: list[CoreField] = []

    def flush_pending_creates() -> None:
        if not pending_creates:
            return
        session.flush()
        for pending_field in pending_creates:
            field_id = cast(object, getattr(pending_field, "id", None))
            if not isinstance(field_id, int):
                raise HTTPException(status_code=500, detail="field create failed")
            retained_ids.append(field_id)
        pending_creates.clear()

    for index, item in enumerate(fields):
        record = existing_fields.get(item.fieldName)
        if record is not None:
            record.field_comment = item.fieldComment or ""
            record.field_type = item.fieldType
            record.field_index = index
            session.add(record)
            retained_ids.append(record.id)
        else:
            field = CoreField(
                id=0,
                ds_id=ds_id,
                table_id=table_id,
                checked=True,
                field_name=item.fieldName,
                field_type=item.fieldType,
                field_comment=item.fieldComment or "",
                custom_comment=item.fieldComment or "",
                field_index=index,
            )
            object.__setattr__(field, "id", None)
            _assign_sqlite_identity(session, field)
            session.add(field)
            pending_creates.append(field)
            if len(pending_creates) >= field_batch_size:
                flush_pending_creates()

    flush_pending_creates()

    if retained_ids:
        _ = session.exec(
            delete(CoreField).where(
                and_(
                    col(CoreField.table_id) == table_id,
                    col(CoreField.id).not_in(retained_ids),
                )
            )
        )
    else:
        _ = session.exec(delete(CoreField).where(col(CoreField.table_id) == table_id))
    return len(fields)


def finalize_sync(
    session: Session,
    context: SyncJobContext,
    *,
    staged_table_ids: list[int],
) -> SyncJobPhase:
    context.job.phase = SyncJobPhase.FINALIZE
    session.add(context.job)
    if staged_table_ids:
        _ = session.exec(
            delete(CoreTable).where(
                and_(
                    col(CoreTable.ds_id) == context.ds.id,
                    col(CoreTable.id).not_in(staged_table_ids),
                )
            )
        )
        _ = session.exec(
            delete(CoreField).where(
                and_(
                    col(CoreField.ds_id) == context.ds.id,
                    col(CoreField.table_id).not_in(staged_table_ids),
                )
            )
        )
    else:
        _ = session.exec(delete(CoreTable).where(col(CoreTable.ds_id) == context.ds.id))
        _ = session.exec(delete(CoreField).where(col(CoreField.ds_id) == context.ds.id))
    session.commit()
    session.refresh(context.job)
    return SyncJobPhase.FINALIZE


def post_process_embeddings(
    session: Session,
    context: SyncJobContext,
    *,
    table_ids: list[int],
    chunk_size: int = SYNC_EMBEDDING_CHUNK_SIZE,
) -> PostProcessResult:
    context.job.phase = SyncJobPhase.POST_PROCESS
    context.job.embedding_followup_status = "dispatched"
    session.add(context.job)
    session.commit()
    session.refresh(context.job)

    chunk_count = 0
    try:
        for start in range(0, len(table_ids), chunk_size):
            chunk = table_ids[start : start + chunk_size]
            if not chunk:
                continue
            run_save_table_embeddings(chunk)
            chunk_count += 1
        if table_ids and context.ds.id is not None:
            run_save_ds_embeddings([context.ds.id])
    except Exception:
        context.job.embedding_followup_status = "failed"
        session.add(context.job)
        session.commit()
    return PostProcessResult(
        phase=SyncJobPhase.POST_PROCESS,
        dispatched_table_ids=table_ids,
        chunk_count=chunk_count,
    )
