"""DSYNC-010: Contract resilience, integration, and edge-case tests.

Validates:
1. Submit → duplicate submit returns reused_active_job
2. Submit → cancel → submit new job succeeds
3. Submit → stale recovery → new job succeeds
4. Flag on → submit succeeds → flag off → submit rejected
5. Visibility: job running → schema unchanged → job succeeded → schema updated
6. Large table count simulation (1000 tables) → submit returns quickly
7. Failed job → retry → succeeds
8. Multiple datasources can have concurrent active jobs
"""

from __future__ import annotations

# pyright: reportAny=false, reportExplicitAny=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnannotatedClassAttribute=false, reportUnusedParameter=false

import time
from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel, col, select

from apps.datasource.constants.sync import (
    ACTIVE_DATASOURCE_SYNC_JOB_STATUSES,
    SYNC_ASYNC_THRESHOLD_TABLES,
    SYNC_FEATURE_FLAG_KEY,
    SYNC_JOB_STALE_TIMEOUT_SECONDS,
    should_route_async,
)
from apps.datasource.crud.sync_job import (
    cancel_sync_job,
    create_sync_job,
    get_active_sync_job,
    get_sync_job_by_id,
    retry_sync_job,
    submit_datasource_sync_job,
    update_sync_job_status,
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
    SyncJobStatus,
    dump_selected_tables_payload,
    should_publish_datasource_sync_result,
)
from common.core.config import settings
from common.utils import sync_job_runtime


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def resilience_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [
        cast(Any, DatasourceSyncJob).__table__,
        cast(Any, CoreTable).__table__,
        cast(Any, CoreField).__table__,
    ]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


# ---------------------------------------------------------------------------
# 1. Submit → duplicate submit returns reused_active_job
# ---------------------------------------------------------------------------


class TestDuplicateSubmitReuse:
    """Verify that submitting while an active job exists returns the same job."""

    def test_duplicate_submit_returns_reused_active_job(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        first = submit_datasource_sync_job(
            test_db, ds_id=1000, oid=1, create_by=1, total_tables=10,
        )
        assert first.reused_active_job is False

        second = submit_datasource_sync_job(
            test_db, ds_id=1000, oid=1, create_by=1, total_tables=10,
        )

        assert second.reused_active_job is True
        assert second.job_id == first.job_id
        assert second.status == SyncJobStatus.PENDING

    def test_duplicate_submit_after_running_returns_reused(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        first = submit_datasource_sync_job(
            test_db, ds_id=1001, oid=1, create_by=1, total_tables=5,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None
        update_sync_job_status(
            test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE,
        )

        second = submit_datasource_sync_job(
            test_db, ds_id=1001, oid=1, create_by=1, total_tables=5,
        )

        assert second.reused_active_job is True
        assert second.job_id == first.job_id
        assert second.status == SyncJobStatus.RUNNING

    def test_duplicate_submit_after_finalizing_returns_reused(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        first = submit_datasource_sync_job(
            test_db, ds_id=1002, oid=1, create_by=1, total_tables=3,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.FINALIZING,
            phase=SyncJobPhase.FINALIZE,
        )

        second = submit_datasource_sync_job(
            test_db, ds_id=1002, oid=1, create_by=1, total_tables=3,
        )

        assert second.reused_active_job is True
        assert second.status == SyncJobStatus.FINALIZING


# ---------------------------------------------------------------------------
# 2. Submit → cancel → submit new job succeeds
# ---------------------------------------------------------------------------


class TestCancelThenResubmit:
    """Verify that cancelling a job allows a fresh submit."""

    def test_cancel_pending_then_new_submit(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        first = submit_datasource_sync_job(
            test_db, ds_id=1100, oid=1, create_by=1, total_tables=5,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None

        cancel_sync_job(test_db, job=job)

        second = submit_datasource_sync_job(
            test_db, ds_id=1100, oid=1, create_by=1, total_tables=10,
        )
        assert second.reused_active_job is False
        assert second.job_id != first.job_id
        assert second.status == SyncJobStatus.PENDING

    def test_cancel_running_then_new_submit(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        first = submit_datasource_sync_job(
            test_db, ds_id=1101, oid=1, create_by=1, total_tables=5,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None
        update_sync_job_status(
            test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE,
        )

        cancel_sync_job(test_db, job=job)

        second = submit_datasource_sync_job(
            test_db, ds_id=1101, oid=1, create_by=1, total_tables=8,
        )
        assert second.reused_active_job is False
        assert second.job_id != first.job_id

    def test_cancel_then_submit_different_datasource_unaffected(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        first = submit_datasource_sync_job(
            test_db, ds_id=1102, oid=1, create_by=1, total_tables=5,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None
        cancel_sync_job(test_db, job=job)

        # Different datasource should be unaffected
        other = submit_datasource_sync_job(
            test_db, ds_id=1103, oid=1, create_by=1, total_tables=3,
        )
        assert other.reused_active_job is False
        assert other.datasource_id == 1103


# ---------------------------------------------------------------------------
# 3. Submit → stale recovery → new job succeeds
# ---------------------------------------------------------------------------


class TestStaleRecovery:
    """Verify stale job recovery via recover_stale_sync_jobs."""

    def test_stale_running_job_recovered_then_new_submit(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        tables = [SelectedTablePayload(table_name="orders", table_comment="Orders")]
        job = create_sync_job(test_db, ds_id=1200, oid=1, create_by=1, total_tables=1)
        job.requested_tables = dump_selected_tables_payload(tables)
        test_db.add(job)
        test_db.commit()
        test_db.refresh(job)

        update_sync_job_status(
            test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.INTROSPECT,
        )
        # Make it stale
        job.update_time = datetime.now() - timedelta(hours=2)
        test_db.add(job)
        test_db.commit()

        class FakeSessionFactory:
            def __init__(self, session: Session) -> None:
                self.session = session
                self.remove_calls = 0

            def __call__(self) -> Session:
                return self.session

            def remove(self) -> None:
                self.remove_calls += 1

        sf = FakeSessionFactory(test_db)
        recovered = sync_job_runtime.recover_stale_sync_jobs(sf)
        assert cast(int, job.id) in recovered

        loaded = get_sync_job_by_id(test_db, cast(int, job.id))
        assert loaded is not None
        assert loaded.status == SyncJobStatus.FAILED
        assert "stale timeout" in (loaded.error_summary or "")

        # New submit should succeed
        second = submit_datasource_sync_job(
            test_db, ds_id=1200, oid=1, create_by=1, total_tables=1,
        )
        assert second.reused_active_job is False
        assert second.status == SyncJobStatus.PENDING

    def test_fresh_running_job_not_recovered(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        tables = [SelectedTablePayload(table_name="orders", table_comment="Orders")]
        job = create_sync_job(test_db, ds_id=1201, oid=1, create_by=1, total_tables=1)
        job.requested_tables = dump_selected_tables_payload(tables)
        test_db.add(job)
        test_db.commit()
        test_db.refresh(job)

        update_sync_job_status(
            test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE,
        )
        # Keep it fresh
        job.update_time = datetime.now()
        test_db.add(job)
        test_db.commit()

        class FakeSessionFactory:
            def __init__(self, session: Session) -> None:
                self.session = session
                self.remove_calls = 0

            def __call__(self) -> Session:
                return self.session

            def remove(self) -> None:
                self.remove_calls += 1

        sf = FakeSessionFactory(test_db)
        recovered = sync_job_runtime.recover_stale_sync_jobs(sf)
        assert cast(int, job.id) not in recovered

        loaded = get_sync_job_by_id(test_db, cast(int, job.id))
        assert loaded is not None
        assert loaded.status == SyncJobStatus.RUNNING

    def test_stale_timeout_constant_value(self) -> None:
        assert SYNC_JOB_STALE_TIMEOUT_SECONDS == 3600


# ---------------------------------------------------------------------------
# 4. Flag on → submit succeeds → flag off → submit rejected
# ---------------------------------------------------------------------------


class TestFeatureFlagOnOff:
    """Verify feature flag controls async submit eligibility at the routing level."""

    def test_flag_on_submits_async(
        self,
        monkeypatch: pytest.MonkeyPatch,
        test_app: Any,
        auth_headers: dict[str, str],
    ) -> None:
        from apps.datasource.api import sync_job as sync_job_api
        from apps.datasource.models.datasource import CoreDatasource

        monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", True)
        monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 1)

        fake_ds = CoreDatasource(id=1, name="test", oid=1)  # pyright: ignore[reportCallIssue]

        monkeypatch.setattr(
            sync_job_api,
            "submit_datasource_sync_job",
            lambda *a, **kw: sync_job_api.DatasourceSyncJobSubmitResponse(
                job_id=42,
                datasource_id=1,
                status=SyncJobStatus.PENDING,
                phase=SyncJobPhase.SUBMIT,
                reused_active_job=False,
            ),
        )
        monkeypatch.setattr(sync_job_api, "dispatch_sync_job", lambda job_id: None)

        def fake_exec(self: Session, statement: Any, **kw: Any) -> Any:
            class _FakeResult:
                def first(self) -> CoreDatasource:
                    return fake_ds

            return _FakeResult()

        monkeypatch.setattr(Session, "exec", fake_exec)

        response = test_app.post(
            "/api/v1/sync-jobs",
            headers=auth_headers,
            json={"datasource_id": 1, "tables": ["orders"]},
        )
        assert response.status_code == 202

    def test_flag_off_rejects_async(
        self,
        monkeypatch: pytest.MonkeyPatch,
        test_app: Any,
        auth_headers: dict[str, str],
    ) -> None:
        monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", False)
        monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 1)

        response = test_app.post(
            "/api/v1/sync-jobs",
            headers=auth_headers,
            json={"datasource_id": 1, "tables": ["orders"]},
        )
        assert response.status_code == 422
        assert "async sync not available" in response.text

    def test_flag_on_below_threshold_rejected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        test_app: Any,
        auth_headers: dict[str, str],
    ) -> None:
        monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_ENABLED", True)
        monkeypatch.setattr(settings, "DATASOURCE_ASYNC_SYNC_TABLE_THRESHOLD", 100)

        response = test_app.post(
            "/api/v1/sync-jobs",
            headers=auth_headers,
            json={"datasource_id": 1, "tables": ["orders"]},
        )
        assert response.status_code == 422

    def test_routing_decision_matches_flag(self) -> None:
        # Flag off → always sync regardless of table count
        assert should_route_async(flag_enabled=False, selected_table_count=5000) is False
        # Flag on + enough tables → async
        assert should_route_async(flag_enabled=True, selected_table_count=100) is True

    def test_feature_flag_key_constant(self) -> None:
        assert SYNC_FEATURE_FLAG_KEY == "DATASOURCE_ASYNC_SYNC_ENABLED"


# ---------------------------------------------------------------------------
# 5. Visibility: job running → schema unchanged → job succeeded → schema updated
# ---------------------------------------------------------------------------


class TestVisibilityRuleEnforcement:
    """Verify schema only updates when job reaches SUCCEEDED."""

    def test_only_succeeded_publishes_schema(self) -> None:
        assert should_publish_datasource_sync_result(SyncJobStatus.SUCCEEDED) is True

    @pytest.mark.parametrize(
        "status",
        [
            SyncJobStatus.PENDING,
            SyncJobStatus.RUNNING,
            SyncJobStatus.FINALIZING,
            SyncJobStatus.FAILED,
            SyncJobStatus.PARTIAL,
            SyncJobStatus.CANCELLED,
        ],
    )
    def test_non_succeeded_does_not_publish(
        self, status: SyncJobStatus,
    ) -> None:
        assert should_publish_datasource_sync_result(status) is False

    def test_active_job_does_not_block_datasource_query(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        """Schema should remain queryable while a sync job is running."""
        _ = resilience_tables
        # Pre-existing schema
        test_db.add(
            CoreTable(
                id=100,
                ds_id=2000,
                checked=True,
                table_name="orders",
                table_comment="old orders",
                custom_comment="old orders",
                embedding=None,
            )
        )
        test_db.add(
            CoreField(
                id=200,
                ds_id=2000,
                table_id=100,
                checked=True,
                field_name="id",
                field_type="bigint",
                field_comment="pk",
                custom_comment="pk",
                field_index=0,
            )
        )
        test_db.commit()

        # Start a sync job
        submit_datasource_sync_job(
            test_db, ds_id=2000, oid=1, create_by=1, total_tables=10,
        )
        active = get_active_sync_job(test_db, 2000)
        assert active is not None
        update_sync_job_status(
            test_db,
            job=active,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
        )

        # Old schema should still be readable
        table = test_db.exec(
            select(CoreTable).where(col(CoreTable.ds_id) == 2000)
        ).first()
        assert table is not None
        assert table.table_comment == "old orders"

        fields = list(
            test_db.exec(
                select(CoreField).where(col(CoreField.ds_id) == 2000)
            ).all()
        )
        assert len(fields) == 1
        assert fields[0].field_name == "id"


# ---------------------------------------------------------------------------
# 6. Large table count simulation (1000 tables) → submit returns quickly
# ---------------------------------------------------------------------------


class TestLargeListBehavior:
    """Verify submit handles large table counts without performance issues."""

    def test_1000_tables_submit_completes_quickly(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        large_table_list = [
            SelectedTablePayload(
                table_name=f"table_{i}",
                table_comment=f"Table {i}",
            )
            for i in range(1000)
        ]

        start = time.monotonic()
        result = submit_datasource_sync_job(
            test_db,
            ds_id=3000,
            oid=1,
            create_by=1,
            total_tables=1000,
            requested_tables=large_table_list,
        )
        elapsed = time.monotonic() - start

        assert result.reused_active_job is False
        assert result.status == SyncJobStatus.PENDING
        assert result.datasource_id == 3000
        # Must complete in well under 5 seconds even on slow CI
        assert elapsed < 5.0, f"submit took {elapsed:.2f}s for 1000 tables"

    def test_1000_tables_duplicate_submit_returns_reused(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        large_table_list = [
            SelectedTablePayload(table_name=f"t_{i}")
            for i in range(1000)
        ]

        first = submit_datasource_sync_job(
            test_db,
            ds_id=3001,
            oid=1,
            create_by=1,
            total_tables=1000,
            requested_tables=large_table_list,
        )

        second = submit_datasource_sync_job(
            test_db,
            ds_id=3001,
            oid=1,
            create_by=1,
            total_tables=1000,
            requested_tables=large_table_list,
        )

        assert second.reused_active_job is True
        assert second.job_id == first.job_id

    def test_large_table_payload_round_trips(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        large_table_list = [
            SelectedTablePayload(
                table_name=f"table_{i}",
                table_comment=f"Comment {i}" if i % 10 == 0 else "",
            )
            for i in range(500)
        ]

        result = submit_datasource_sync_job(
            test_db,
            ds_id=3002,
            oid=1,
            create_by=1,
            total_tables=500,
            requested_tables=large_table_list,
        )

        job = get_sync_job_by_id(test_db, result.job_id)
        assert job is not None

        from apps.datasource.models.sync_job import load_selected_tables_payload

        loaded = load_selected_tables_payload(job.requested_tables)
        assert len(loaded) == 500
        assert loaded[0].table_name == "table_0"
        assert loaded[0].table_comment == "Comment 0"
        assert loaded[1].table_comment == ""

    def test_threshold_at_100_tables_routes_async(self) -> None:
        assert should_route_async(flag_enabled=True, selected_table_count=100) is True

    def test_threshold_above_1000_routes_async(self) -> None:
        assert should_route_async(flag_enabled=True, selected_table_count=1000) is True


# ---------------------------------------------------------------------------
# 7. Failed job → retry → succeeds
# ---------------------------------------------------------------------------


class TestFailedJobRetry:
    """Verify full failed → retry → succeeds lifecycle."""

    def test_failed_job_retry_creates_new_pending(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        tables = [
            SelectedTablePayload(table_name="orders", table_comment="Orders"),
            SelectedTablePayload(table_name="customers", table_comment="Customers"),
        ]
        first = submit_datasource_sync_job(
            test_db,
            ds_id=4000,
            oid=1,
            create_by=1,
            total_tables=2,
            requested_tables=tables,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None

        # Simulate failure
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.FAILED,
            phase=SyncJobPhase.STAGE,
            error_summary="connection timeout",
        )

        # Retry
        retry_result = retry_sync_job(test_db, job=job, oid=1, create_by=2)
        assert retry_result.reused_active_job is False
        assert retry_result.status == SyncJobStatus.PENDING
        assert retry_result.datasource_id == 4000
        assert retry_result.job_id != first.job_id

    def test_partial_job_retry_creates_new(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        tables = [SelectedTablePayload(table_name="orders")]
        first = submit_datasource_sync_job(
            test_db,
            ds_id=4001,
            oid=1,
            create_by=1,
            total_tables=1,
            requested_tables=tables,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None

        update_sync_job_status(
            test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE,
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.PARTIAL,
            phase=SyncJobPhase.FINALIZE,
            completed_tables=0,
            failed_tables=1,
            error_summary="1 of 1 tables failed",
        )

        retry_result = retry_sync_job(test_db, job=job, oid=1, create_by=1)
        assert retry_result.reused_active_job is False
        assert retry_result.job_id != first.job_id

    def test_cancelled_job_retry_creates_new(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        tables = [SelectedTablePayload(table_name="orders")]
        first = submit_datasource_sync_job(
            test_db,
            ds_id=4002,
            oid=1,
            create_by=1,
            total_tables=1,
            requested_tables=tables,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None

        cancel_sync_job(test_db, job=job)

        retry_result = retry_sync_job(test_db, job=job, oid=1, create_by=1)
        assert retry_result.reused_active_job is False
        assert retry_result.job_id != first.job_id

    def test_retry_then_succeed_lifecycle(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        """Full lifecycle: submit → fail → retry → run → succeed."""
        _ = resilience_tables
        tables = [
            SelectedTablePayload(table_name="orders", table_comment="Orders"),
        ]
        first = submit_datasource_sync_job(
            test_db,
            ds_id=4003,
            oid=1,
            create_by=1,
            total_tables=1,
            requested_tables=tables,
        )
        job = get_sync_job_by_id(test_db, first.job_id)
        assert job is not None

        # Fail
        update_sync_job_status(
            test_db, job=job, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE,
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.FAILED,
            phase=SyncJobPhase.STAGE,
            error_summary="timeout",
        )

        # Retry
        retry_result = retry_sync_job(test_db, job=job, oid=1, create_by=1)
        new_job = get_sync_job_by_id(test_db, retry_result.job_id)
        assert new_job is not None

        # Simulate success
        update_sync_job_status(
            test_db,
            job=new_job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.INTROSPECT,
            total_tables=1,
        )
        update_sync_job_status(
            test_db,
            job=new_job,
            status=SyncJobStatus.FINALIZING,
            phase=SyncJobPhase.FINALIZE,
            completed_tables=1,
            total_fields=5,
        )
        final = update_sync_job_status(
            test_db,
            job=new_job,
            status=SyncJobStatus.SUCCEEDED,
            phase=SyncJobPhase.POST_PROCESS,
            completed_tables=1,
            completed_fields=5,
        )

        assert final.status == SyncJobStatus.SUCCEEDED
        assert final.finish_time is not None
        assert final.start_time is not None
        assert final.completed_tables == 1

        # Original job should still be FAILED
        original = get_sync_job_by_id(test_db, first.job_id)
        assert original is not None
        assert original.status == SyncJobStatus.FAILED

    @pytest.mark.parametrize(
        "status",
        [
            SyncJobStatus.PENDING,
            SyncJobStatus.RUNNING,
            SyncJobStatus.FINALIZING,
            SyncJobStatus.SUCCEEDED,
        ],
    )
    def test_retry_rejects_non_retryable_states(
        self,
        resilience_tables: None,
        test_db: Session,
        status: SyncJobStatus,
    ) -> None:
        _ = resilience_tables
        job = create_sync_job(test_db, ds_id=4010, oid=1, create_by=1)
        update_sync_job_status(test_db, job=job, status=status)

        with pytest.raises(ValueError, match="not retryable"):
            retry_sync_job(test_db, job=job, oid=1, create_by=1)


# ---------------------------------------------------------------------------
# 8. Multiple datasources can have concurrent active jobs
# ---------------------------------------------------------------------------


class TestConcurrentMultiDatasource:
    """Verify independent datasources can each have an active sync job."""

    def test_two_datasources_each_have_active_job(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        ds_a = submit_datasource_sync_job(
            test_db, ds_id=5000, oid=1, create_by=1, total_tables=10,
        )
        ds_b = submit_datasource_sync_job(
            test_db, ds_id=5001, oid=1, create_by=1, total_tables=20,
        )

        assert ds_a.reused_active_job is False
        assert ds_b.reused_active_job is False
        assert ds_a.job_id != ds_b.job_id

        # Both should be active
        active_a = get_active_sync_job(test_db, 5000)
        active_b = get_active_sync_job(test_db, 5001)
        assert active_a is not None
        assert active_b is not None
        assert active_a.id == ds_a.job_id
        assert active_b.id == ds_b.job_id

    def test_three_datasources_independent_lifecycle(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        # DS A: submit → succeed → can submit again
        result_a = submit_datasource_sync_job(
            test_db, ds_id=5100, oid=1, create_by=1, total_tables=5,
        )
        job_a = get_sync_job_by_id(test_db, result_a.job_id)
        assert job_a is not None
        update_sync_job_status(
            test_db, job=job_a, status=SyncJobStatus.SUCCEEDED, phase=SyncJobPhase.FINALIZE,
        )

        # DS B: submit → keep running
        result_b = submit_datasource_sync_job(
            test_db, ds_id=5101, oid=1, create_by=1, total_tables=10,
        )
        job_b = get_sync_job_by_id(test_db, result_b.job_id)
        assert job_b is not None
        update_sync_job_status(
            test_db, job=job_b, status=SyncJobStatus.RUNNING, phase=SyncJobPhase.STAGE,
        )

        # DS C: submit → pending
        result_c = submit_datasource_sync_job(
            test_db, ds_id=5102, oid=1, create_by=1, total_tables=3,
        )

        # Verify isolation
        assert get_active_sync_job(test_db, 5100) is None
        active_b = get_active_sync_job(test_db, 5101)
        assert active_b is not None
        assert active_b.id == result_b.job_id
        active_c = get_active_sync_job(test_db, 5102)
        assert active_c is not None
        assert active_c.id == result_c.job_id

        # DS A can submit a new job since previous succeeded
        new_a = submit_datasource_sync_job(
            test_db, ds_id=5100, oid=1, create_by=1, total_tables=8,
        )
        assert new_a.reused_active_job is False
        assert new_a.job_id != result_a.job_id

    def test_cancel_one_datasource_does_not_affect_others(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        submit_datasource_sync_job(
            test_db, ds_id=5200, oid=1, create_by=1, total_tables=5,
        )
        result_b = submit_datasource_sync_job(
            test_db, ds_id=5201, oid=1, create_by=1, total_tables=10,
        )
        submit_datasource_sync_job(
            test_db, ds_id=5202, oid=1, create_by=1, total_tables=3,
        )

        # Cancel DS B
        job_b = get_sync_job_by_id(test_db, result_b.job_id)
        assert job_b is not None
        cancel_sync_job(test_db, job=job_b)

        # DS A and C still active
        assert get_active_sync_job(test_db, 5200) is not None
        assert get_active_sync_job(test_db, 5201) is None
        assert get_active_sync_job(test_db, 5202) is not None

    def test_duplicate_submit_per_datasource_isolation(
        self,
        resilience_tables: None,
        test_db: Session,
    ) -> None:
        _ = resilience_tables
        # DS 5300: first submit
        first_5300 = submit_datasource_sync_job(
            test_db, ds_id=5300, oid=1, create_by=1, total_tables=5,
        )
        # DS 5301: first submit
        first_5301 = submit_datasource_sync_job(
            test_db, ds_id=5301, oid=1, create_by=1, total_tables=3,
        )

        # Duplicate on DS 5300 → reused
        dup_5300 = submit_datasource_sync_job(
            test_db, ds_id=5300, oid=1, create_by=1, total_tables=5,
        )
        assert dup_5300.reused_active_job is True
        assert dup_5300.job_id == first_5300.job_id

        # Duplicate on DS 5301 → reused (different job)
        dup_5301 = submit_datasource_sync_job(
            test_db, ds_id=5301, oid=1, create_by=1, total_tables=3,
        )
        assert dup_5301.reused_active_job is True
        assert dup_5301.job_id == first_5301.job_id
        assert dup_5301.job_id != dup_5300.job_id


# ---------------------------------------------------------------------------
# 9. Constant and contract lock verification
# ---------------------------------------------------------------------------


class TestConstantLocks:
    """Verify key constants haven't drifted."""

    def test_threshold_default(self) -> None:
        assert SYNC_ASYNC_THRESHOLD_TABLES == 100

    def test_stale_timeout_default(self) -> None:
        assert SYNC_JOB_STALE_TIMEOUT_SECONDS == 3600

    def test_active_states_are_active(self) -> None:
        expected = frozenset(
            {SyncJobStatus.PENDING, SyncJobStatus.RUNNING, SyncJobStatus.FINALIZING}
        )
        assert ACTIVE_DATASOURCE_SYNC_JOB_STATUSES == expected
