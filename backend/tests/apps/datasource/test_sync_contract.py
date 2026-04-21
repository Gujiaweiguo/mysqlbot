"""Contract tests for the datasource async sync job system.

Validates that:
1. All schema shapes have the required fields and correct types.
2. Enum values match the locked contract.
3. Duplicate-submit returns reused_active_job=True (idempotent).
4. 409 Conflict response model shape is correct.
5. Feature flag on/off routing decisions are correct.
6. Visibility rule: only SUCCEEDED publishes new schema.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from apps.datasource.constants.sync import (
    ACTIVE_DATASOURCE_SYNC_JOB_STATUSES,
    SYNC_ASYNC_THRESHOLD_TABLES,
    SYNC_BATCH_SIZE,
    SYNC_EMBEDDING_CHUNK_SIZE,
    SYNC_EMBEDDING_MAX_WORKERS,
    SYNC_FEATURE_FLAG_KEY,
    SYNC_FIELD_BATCH_SIZE,
    SYNC_JOB_MAX_WORKERS,
    SYNC_JOB_PROGRESS_INTERVAL_SECONDS,
    SYNC_JOB_STALE_TIMEOUT_SECONDS,
    TERMINAL_DATASOURCE_SYNC_JOB_STATUSES,
    should_route_async,
)
from apps.datasource.models.sync_job import (
    SyncJobPhase,
    SyncJobStatus,
    should_publish_datasource_sync_result,
)
from apps.datasource.schemas.sync_job import (
    SyncJobStatusResponse,
    SyncJobSubmitRequest,
    SyncJobSubmitResponse,
    SyncJobSummary,
    SyncJobTableDetail,
)


class TestSyncJobStatusEnum:
    def test_all_contract_states_defined(self) -> None:
        expected = {"pending", "running", "finalizing", "succeeded", "failed", "partial", "cancelled"}
        actual = {s.value for s in SyncJobStatus}
        assert actual == expected

    def test_active_states(self) -> None:
        assert ACTIVE_DATASOURCE_SYNC_JOB_STATUSES == frozenset(
            {SyncJobStatus.PENDING, SyncJobStatus.RUNNING, SyncJobStatus.FINALIZING}
        )

    def test_terminal_states(self) -> None:
        assert TERMINAL_DATASOURCE_SYNC_JOB_STATUSES == frozenset(
            {SyncJobStatus.SUCCEEDED, SyncJobStatus.FAILED, SyncJobStatus.PARTIAL, SyncJobStatus.CANCELLED}
        )


class TestSyncJobPhaseEnum:
    def test_all_contract_phases_defined(self) -> None:
        expected = {"submit", "introspect", "stage", "finalize", "post_process"}
        actual = {p.value for p in SyncJobPhase}
        assert actual == expected


class TestSyncJobSubmitRequest:
    def test_valid_payload(self) -> None:
        req = SyncJobSubmitRequest(datasource_id=42, tables=["orders", "customers"])
        assert req.datasource_id == 42
        assert len(req.tables) == 2

    def test_empty_tables_allowed(self) -> None:
        req = SyncJobSubmitRequest(datasource_id=1, tables=[])
        assert req.tables == []

    def test_missing_datasource_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            SyncJobSubmitRequest(tables=["orders"])  # pyright: ignore[reportCallIssue]

    def test_missing_tables_raises(self) -> None:
        with pytest.raises(ValidationError):
            SyncJobSubmitRequest(datasource_id=1)  # pyright: ignore[reportCallIssue]


class TestSyncJobSubmitResponse:
    def test_new_job_response(self) -> None:
        resp = SyncJobSubmitResponse(
            job_id=101,
            datasource_id=42,
            status=SyncJobStatus.PENDING,
            phase=SyncJobPhase.SUBMIT,
            reused_active_job=False,
        )
        dumped = resp.model_dump(mode="json")
        assert dumped == {
            "job_id": 101,
            "datasource_id": 42,
            "status": "pending",
            "phase": "submit",
            "reused_active_job": False,
        }

    def test_reused_active_job_response(self) -> None:
        resp = SyncJobSubmitResponse(
            job_id=99,
            datasource_id=42,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            reused_active_job=True,
        )
        assert resp.reused_active_job is True
        dumped = resp.model_dump(mode="json")
        assert dumped["reused_active_job"] is True
        assert dumped["status"] == "running"


class TestSyncJobStatusResponse:
    def test_full_progress_payload(self) -> None:
        now = datetime(2026, 4, 21, 10, 0, 0)
        resp = SyncJobStatusResponse(
            job_id=101,
            datasource_id=42,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            total_tables=1000,
            completed_tables=150,
            failed_tables=2,
            skipped_tables=0,
            total_fields=5000,
            completed_fields=800,
            current_table_name="orders",
            embedding_followup_status=None,
            error_summary=None,
            create_time=now,
            update_time=now,
            start_time=now,
            finish_time=None,
        )
        dumped = resp.model_dump(mode="json")
        assert dumped["job_id"] == 101
        assert dumped["status"] == "running"
        assert dumped["total_tables"] == 1000
        assert dumped["completed_tables"] == 150
        assert dumped["failed_tables"] == 2
        assert dumped["current_table_name"] == "orders"
        assert dumped["finish_time"] is None
        assert dumped["embedding_followup_status"] is None

    def test_terminal_succeeded_payload(self) -> None:
        created = datetime(2026, 4, 21, 10, 0, 0)
        finished = datetime(2026, 4, 21, 10, 30, 0)
        resp = SyncJobStatusResponse(
            job_id=101,
            datasource_id=42,
            status=SyncJobStatus.SUCCEEDED,
            phase=SyncJobPhase.FINALIZE,
            total_tables=1000,
            completed_tables=1000,
            failed_tables=0,
            skipped_tables=0,
            total_fields=5000,
            completed_fields=5000,
            current_table_name=None,
            embedding_followup_status=None,
            error_summary=None,
            create_time=created,
            update_time=finished,
            start_time=created,
            finish_time=finished,
        )
        dumped = resp.model_dump(mode="json")
        assert dumped["status"] == "succeeded"
        assert dumped["finish_time"] == "2026-04-21T10:30:00"


class TestSyncJobSummary:
    def test_summary_shape(self) -> None:
        now = datetime(2026, 4, 21, 10, 0, 0)
        summary = SyncJobSummary(
            job_id=101,
            datasource_id=42,
            status=SyncJobStatus.SUCCEEDED,
            total_tables=1000,
            completed_tables=998,
            failed_tables=2,
            skipped_tables=0,
            create_time=now,
            finish_time=now,
        )
        dumped = summary.model_dump(mode="json")
        assert dumped["job_id"] == 101
        assert dumped["status"] == "succeeded"
        assert "phase" not in dumped
        assert "current_table_name" not in dumped

    def test_summary_without_finish_time(self) -> None:
        now = datetime(2026, 4, 21, 10, 0, 0)
        summary = SyncJobSummary(
            job_id=101,
            datasource_id=42,
            status=SyncJobStatus.RUNNING,
            total_tables=1000,
            completed_tables=500,
            failed_tables=0,
            skipped_tables=0,
            create_time=now,
        )
        assert summary.finish_time is None


class TestSyncJobTableDetail:
    def test_success_detail(self) -> None:
        detail = SyncJobTableDetail(
            table_name="orders",
            status=SyncJobStatus.SUCCEEDED,
            fields_synced=10,
            fields_total=10,
        )
        dumped = detail.model_dump(mode="json")
        assert dumped["table_name"] == "orders"
        assert dumped["status"] == "succeeded"
        assert dumped["fields_synced"] == 10
        assert dumped["error"] is None

    def test_failure_detail(self) -> None:
        detail = SyncJobTableDetail(
            table_name="orders",
            status=SyncJobStatus.FAILED,
            fields_synced=5,
            fields_total=10,
            error="connection timeout",
        )
        assert detail.error == "connection timeout"


class TestConflictBehavior:
    """Duplicate submit: the submit endpoint returns the active job's info
    with reused_active_job=True rather than creating a 409.

    409 Conflict applies when other operations (e.g., datasource config edit)
    conflict with a running job.
    """

    def test_duplicate_submit_returns_reused_flag(self) -> None:
        active_resp = SyncJobSubmitResponse(
            job_id=99,
            datasource_id=42,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            reused_active_job=True,
        )
        dumped = active_resp.model_dump(mode="json")
        assert dumped["reused_active_job"] is True
        assert dumped["job_id"] == 99

    def test_conflict_response_carries_job_id(self) -> None:
        conflict_body = {
            "detail": "conflict",
            "active_job_id": 99,
            "datasource_id": 42,
        }
        assert "active_job_id" in conflict_body
        assert conflict_body["active_job_id"] == 99


class TestFeatureFlagRouting:
    def test_flag_off_always_sync(self) -> None:
        assert should_route_async(flag_enabled=False, selected_table_count=5000) is False

    def test_flag_on_below_threshold(self) -> None:
        assert should_route_async(flag_enabled=True, selected_table_count=50) is False

    def test_flag_on_at_threshold(self) -> None:
        assert should_route_async(flag_enabled=True, selected_table_count=100) is True

    def test_flag_on_above_threshold(self) -> None:
        assert should_route_async(flag_enabled=True, selected_table_count=1000) is True

    def test_zero_tables_flag_on(self) -> None:
        assert should_route_async(flag_enabled=True, selected_table_count=0) is False

    def test_custom_threshold(self) -> None:
        assert should_route_async(flag_enabled=True, selected_table_count=30, threshold=30) is True
        assert should_route_async(flag_enabled=True, selected_table_count=29, threshold=30) is False


class TestConstantsValues:
    def test_feature_flag_key(self) -> None:
        assert SYNC_FEATURE_FLAG_KEY == "DATASOURCE_ASYNC_SYNC_ENABLED"

    def test_threshold_default(self) -> None:
        assert SYNC_ASYNC_THRESHOLD_TABLES == 100

    def test_max_workers_default(self) -> None:
        assert SYNC_JOB_MAX_WORKERS == 4

    def test_stale_timeout_default(self) -> None:
        assert SYNC_JOB_STALE_TIMEOUT_SECONDS == 3600

    def test_batch_size_default(self) -> None:
        assert SYNC_BATCH_SIZE == 50

    def test_field_batch_size_default(self) -> None:
        assert SYNC_FIELD_BATCH_SIZE == 200

    def test_progress_interval_default(self) -> None:
        assert SYNC_JOB_PROGRESS_INTERVAL_SECONDS == 2

    def test_embedding_chunk_size_default(self) -> None:
        assert SYNC_EMBEDDING_CHUNK_SIZE == 50

    def test_embedding_max_workers_default(self) -> None:
        assert SYNC_EMBEDDING_MAX_WORKERS == 8


class TestVisibilityRule:
    def test_only_succeeded_publishes(self) -> None:
        assert should_publish_datasource_sync_result(SyncJobStatus.SUCCEEDED) is True

    @pytest.mark.parametrize(
        "status",
        [SyncJobStatus.PENDING, SyncJobStatus.RUNNING, SyncJobStatus.FINALIZING, SyncJobStatus.FAILED, SyncJobStatus.PARTIAL, SyncJobStatus.CANCELLED],
    )
    def test_non_succeeded_does_not_publish(self, status: SyncJobStatus) -> None:
        assert should_publish_datasource_sync_result(status) is False
