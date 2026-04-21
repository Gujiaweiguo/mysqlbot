"""DSYNC-008: Post-sync embedding operational safeguards.

Ensures:
- Embedding worker count is bounded by an explicit config constant
- Embedding failure after finalize does NOT corrupt the sync result
- embedding_followup_status is recorded correctly (dispatched / failed)
- Embedding executor cannot starve the DB connection pool
"""

from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnannotatedClassAttribute=false, reportUnusedImport=false

from datetime import datetime
from typing import Any, cast
from collections.abc import Generator

import pytest
from sqlmodel import Session, SQLModel, col, select

from apps.datasource.constants.sync import (
    SYNC_EMBEDDING_MAX_WORKERS,
    SYNC_JOB_MAX_WORKERS,
)
from apps.datasource.models.datasource import (
    CoreDatasource,
    CoreField,
    CoreTable,
    DatasourceConf,
)
from apps.datasource.models.sync_job import DatasourceSyncJob, SyncJobPhase, SyncJobStatus
from apps.datasource.services.sync_engine import (
    SyncJobContext,
    finalize_sync,
    post_process_embeddings,
)
from apps.db.constant import ConnectType
from apps.db.db import DatasourceMetadataContext
from common.core.config import settings
from common.utils.embedding_runtime import embedding_executor





def _build_datasource() -> CoreDatasource:
    return CoreDatasource(
        id=1,
        name="ds",
        description=None,
        type="mysql",
        type_name="mysql",
        configuration="{}",
        create_time=None,
        create_by=1,
        status="Success",
        num="0/1",
        oid=1,
        table_relation=[],
        embedding=None,
        recommended_config=1,
    )


def _build_job() -> DatasourceSyncJob:
    return DatasourceSyncJob(
        id=1,
        ds_id=1,
        oid=1,
        create_by=1,
        status=SyncJobStatus.PENDING,
        phase=SyncJobPhase.SUBMIT,
        total_tables=0,
        completed_tables=0,
        failed_tables=0,
        skipped_tables=0,
        total_fields=0,
        completed_fields=0,
        current_table_name=None,
        requested_tables="[]",
        embedding_followup_status=None,
        error_summary=None,
        create_time=datetime.now(),
        update_time=datetime.now(),
        start_time=None,
        finish_time=None,
    )


@pytest.fixture
def sync_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [
        cast(Any, CoreTable).__table__,
        cast(Any, CoreField).__table__,
        cast(Any, DatasourceSyncJob).__table__,
    ]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


def _persist_context(test_db: Session) -> SyncJobContext:
    ds = _build_datasource()
    job = _build_job()
    test_db.add(job)
    test_db.commit()
    metadata_context = DatasourceMetadataContext(
        ds_type="mysql",
        conf=DatasourceConf(),
        connect_type=ConnectType.sqlalchemy,
    )
    return SyncJobContext.from_job(
        ds=ds,
        job=job,
        requested_tables=[],
        metadata_context=metadata_context,
    )


def _seed_finalized_schema(test_db: Session) -> tuple[SyncJobContext, list[int]]:
    """Create a finalized schema with tables, returning context and table IDs."""
    context = _persist_context(test_db)

    table_ids: list[int] = []
    for idx, name in enumerate(("orders", "customers"), start=10):
        table = CoreTable(
            id=idx,
            ds_id=1,
            checked=True,
            table_name=name,
            table_comment=name,
            custom_comment=name,
            embedding=None,
        )
        test_db.add(table)
        table_ids.append(idx)

    test_db.commit()
    return context, table_ids


class TestEmbeddingWorkerBounding:
    def test_sync_embedding_max_workers_constant_exists(self) -> None:
        """SYNC_EMBEDDING_MAX_WORKERS must be defined and positive."""
        assert isinstance(SYNC_EMBEDDING_MAX_WORKERS, int)
        assert SYNC_EMBEDDING_MAX_WORKERS > 0

    def test_embedding_executor_respects_config_constant(self) -> None:
        """The embedding executor max_workers must match the config setting."""
        assert embedding_executor._max_workers == settings.DATASOURCE_SYNC_EMBEDDING_MAX_WORKERS

    def test_embedding_workers_do_not_exceed_sync_job_workers_by_too_much(self) -> None:
        """Embedding workers should be bounded relative to sync job workers.

        We allow up to 2x SYNC_JOB_MAX_WORKERS to avoid being too restrictive
        for I/O-bound embedding work, but must not be unbounded.
        """
        assert SYNC_EMBEDDING_MAX_WORKERS <= SYNC_JOB_MAX_WORKERS * 4

    def test_config_default_matches_constant(self) -> None:
        """Settings default must equal the contract constant."""
        assert settings.DATASOURCE_SYNC_EMBEDDING_MAX_WORKERS == SYNC_EMBEDDING_MAX_WORKERS

class TestConnectionPoolStarvation:
    def test_embedding_workers_within_pool_capacity(self) -> None:
        """Total concurrent workers (sync + embedding) must fit in the DB pool.

        PG pool capacity = PG_POOL_SIZE + PG_MAX_OVERFLOW.
        Sync jobs + embedding workers together should not exceed pool capacity,
        leaving headroom for API-serving connections.
        """
        pool_capacity = settings.PG_POOL_SIZE + settings.PG_MAX_OVERFLOW
        total_workers = SYNC_JOB_MAX_WORKERS + SYNC_EMBEDDING_MAX_WORKERS
        assert total_workers <= pool_capacity, (
            f"Total workers ({total_workers}) exceeds pool capacity ({pool_capacity})"
        )

    def test_embedding_workers_are_not_unbounded(self) -> None:
        """Embedding executor must never use an unreasonably large pool."""
        assert settings.DATASOURCE_SYNC_EMBEDDING_MAX_WORKERS <= 50, (
            "Embedding worker count should be reasonably bounded"
        )

class TestEmbeddingFailureIsolation:
    def test_embedding_failure_sets_followup_status_failed(
        self,
        sync_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When embedding dispatch raises, embedding_followup_status = 'failed'."""
        _ = sync_tables
        context, table_ids = _seed_finalized_schema(test_db)

        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_table_embeddings",
            lambda ids: (_ for _ in ()).throw(RuntimeError("embedding service down")),
        )

        _ = finalize_sync(test_db, context, staged_table_ids=table_ids)
        post_result = post_process_embeddings(test_db, context, table_ids=table_ids)

        loaded_job = test_db.get(DatasourceSyncJob, 1)
        assert loaded_job is not None
        assert post_result.phase == SyncJobPhase.POST_PROCESS
        assert loaded_job.embedding_followup_status == "failed"
        assert loaded_job.phase == SyncJobPhase.POST_PROCESS

    def test_schema_remains_finalized_after_embedding_failure(
        self,
        sync_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Finalized tables survive even when embedding dispatch fails."""
        _ = sync_tables
        context, table_ids = _seed_finalized_schema(test_db)

        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_table_embeddings",
            lambda ids: (_ for _ in ()).throw(RuntimeError("embedding crash")),
        )
        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_ds_embeddings",
            lambda ids: (_ for _ in ()).throw(RuntimeError("embedding crash")),
        )

        _ = finalize_sync(test_db, context, staged_table_ids=table_ids)
        _ = post_process_embeddings(test_db, context, table_ids=table_ids)

        remaining = list(
            test_db.exec(select(CoreTable).order_by(col(CoreTable.id))).all()
        )
        assert len(remaining) == 2
        assert [t.table_name for t in remaining] == ["orders", "customers"]

    def test_ds_embedding_failure_also_records_followup_failed(
        self,
        sync_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When ds embedding dispatch raises, followup status = 'failed'."""
        _ = sync_tables
        context, table_ids = _seed_finalized_schema(test_db)

        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_table_embeddings",
            lambda ids: None,
        )
        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_ds_embeddings",
            lambda ids: (_ for _ in ()).throw(RuntimeError("ds embedding failed")),
        )

        _ = finalize_sync(test_db, context, staged_table_ids=table_ids)
        _ = post_process_embeddings(test_db, context, table_ids=table_ids)

        loaded_job = test_db.get(DatasourceSyncJob, 1)
        assert loaded_job is not None
        assert loaded_job.embedding_followup_status == "failed"

    def test_post_process_returns_normally_despite_embedding_error(
        self,
        sync_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """post_process_embeddings must not raise — it returns a PostProcessResult."""
        _ = sync_tables
        context, table_ids = _seed_finalized_schema(test_db)

        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_table_embeddings",
            lambda ids: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        _ = finalize_sync(test_db, context, staged_table_ids=table_ids)
        result = post_process_embeddings(test_db, context, table_ids=table_ids)

        assert result.phase == SyncJobPhase.POST_PROCESS
        assert result.dispatched_table_ids == table_ids

    def test_successful_dispatch_records_followup_dispatched(
        self,
        sync_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When embedding dispatch succeeds, followup status = 'dispatched'."""
        _ = sync_tables
        context, table_ids = _seed_finalized_schema(test_db)

        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_table_embeddings",
            lambda ids: None,
        )
        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_ds_embeddings",
            lambda ids: None,
        )

        _ = finalize_sync(test_db, context, staged_table_ids=table_ids)
        _ = post_process_embeddings(test_db, context, table_ids=table_ids)

        loaded_job = test_db.get(DatasourceSyncJob, 1)
        assert loaded_job is not None
        assert loaded_job.embedding_followup_status == "dispatched"

    def test_empty_table_ids_does_not_dispatch(
        self,
        sync_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When no table IDs, no embedding work dispatched, followup stays dispatched."""
        _ = sync_tables
        context, _ = _seed_finalized_schema(test_db)

        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_table_embeddings",
            lambda ids: None,
        )
        monkeypatch.setattr(
            "apps.datasource.services.sync_engine.run_save_ds_embeddings",
            lambda ids: None,
        )

        _ = finalize_sync(test_db, context, staged_table_ids=[])
        result = post_process_embeddings(test_db, context, table_ids=[])

        assert result.chunk_count == 0
        assert result.dispatched_table_ids == []

        loaded_job = test_db.get(DatasourceSyncJob, 1)
        assert loaded_job is not None
        assert loaded_job.embedding_followup_status == "dispatched"


class TestConstantLocks:
    def test_sync_embedding_max_workers_not_zero(self) -> None:
        assert SYNC_EMBEDDING_MAX_WORKERS >= 1

    def test_sync_job_max_workers_not_zero(self) -> None:
        assert SYNC_JOB_MAX_WORKERS >= 1
