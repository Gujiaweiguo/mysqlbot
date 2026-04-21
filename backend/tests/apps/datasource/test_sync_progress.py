"""DSYNC-006: Progress persistence, polling contract, and SSE event adapter.

Tests the integrated behavior of:
1. Polling progress snapshots — advancing job phases and verifying counts are
   durably persisted and readable from a fresh DB session.
2. Progress write frequency bounded — increment_sync_job_progress throttles
   commits to avoid write amplification.
3. SSE payload format — iter_sync_job_events produces data:{json}\\n\\n frames
   consistent with chat event style, including field-level validation.
"""
from __future__ import annotations

import json
from collections.abc import Generator
from itertools import islice
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel

from apps.datasource.api.sync_job_streaming import iter_sync_job_events
from apps.datasource.crud.sync_job import (
    build_sync_job_status_response,
    create_sync_job,
    get_sync_job_by_id,
    increment_sync_job_progress,
    update_sync_job_status,
)
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    SyncJobStatus,
)


@pytest.fixture
def progress_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [cast(Any, DatasourceSyncJob).__table__]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeSessionFactory:
    """Minimal session factory matching SyncJobSessionFactory protocol."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.remove_calls = 0

    def __call__(self) -> Session:
        return self.session

    def remove(self) -> None:
        self.remove_calls += 1


def _parse_sse_event(raw: str) -> dict[str, Any]:
    """Parse a single SSE data frame into a dict."""
    assert raw.startswith("data:"), f"expected 'data:' prefix, got: {raw!r}"
    assert raw.endswith("\n\n"), f"expected '\\n\\n' suffix, got: {raw!r}"
    return json.loads(raw[5:].strip())


# ===========================================================================
# 1. Polling progress snapshots
# ===========================================================================


class TestPollingProgressSnapshots:
    """Verify that polling reads durable DB state, not ephemeral in-memory."""

    def test_fresh_read_reflects_committed_progress(
        self,
        progress_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _ = progress_tables
        # Ensure commits happen immediately for deterministic behavior
        monkeypatch.setattr(
            "apps.datasource.crud.sync_job.settings"
            ".DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
            0,
        )

        job = create_sync_job(
            test_db, ds_id=100, oid=1, create_by=1, total_tables=10, total_fields=200
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.INTROSPECT,
        )

        # Increment progress across multiple calls
        increment_sync_job_progress(
            test_db,
            job=job,
            completed_tables_delta=3,
            completed_fields_delta=60,
            current_table_name="orders",
        )
        increment_sync_job_progress(
            test_db,
            job=job,
            completed_tables_delta=2,
            completed_fields_delta=40,
            current_table_name="products",
        )

        # Fresh read from DB simulates a polling request
        fresh_job = get_sync_job_by_id(test_db, cast(int, job.id))
        assert fresh_job is not None
        assert fresh_job.completed_tables == 5
        assert fresh_job.completed_fields == 100
        assert fresh_job.current_table_name == "products"

    def test_phase_advancement_with_durable_counts(
        self,
        progress_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _ = progress_tables
        monkeypatch.setattr(
            "apps.datasource.crud.sync_job.settings"
            ".DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
            0,
        )

        job = create_sync_job(
            test_db, ds_id=101, oid=1, create_by=1, total_tables=8, total_fields=160
        )

        # Phase 1: INTROSPECT
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.INTROSPECT,
            total_fields=160,
        )

        # Phase 2: STAGE — increment progress during staging
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
        )
        increment_sync_job_progress(
            test_db,
            job=job,
            completed_tables_delta=4,
            completed_fields_delta=80,
            current_table_name="users",
        )

        # Verify snapshot at STAGE phase
        refreshed = get_sync_job_by_id(test_db, cast(int, job.id))
        assert refreshed is not None  # pyright: ignore[reportUnnecessaryComparison]
        snapshot = build_sync_job_status_response(refreshed)
        assert snapshot.phase == SyncJobPhase.STAGE
        assert snapshot.status == SyncJobStatus.RUNNING
        assert snapshot.completed_tables == 4
        assert snapshot.completed_fields == 80

        # Phase 3: FINALIZE
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.FINALIZING,
            phase=SyncJobPhase.FINALIZE,
        )
        increment_sync_job_progress(
            test_db,
            job=job,
            completed_tables_delta=4,
            completed_fields_delta=80,
            current_table_name=None,
        )

        # Final snapshot
        refreshed2 = get_sync_job_by_id(test_db, cast(int, job.id))
        assert refreshed2 is not None  # pyright: ignore[reportUnnecessaryComparison]
        final = build_sync_job_status_response(refreshed2)
        assert final.completed_tables == 8
        assert final.completed_fields == 160

    def test_status_response_excludes_staged_row_details(
        self,
        progress_tables: None,
        test_db: Session,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=102, oid=1, create_by=1, total_tables=5, total_fields=50
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            completed_tables=3,
            completed_fields=30,
            current_table_name="orders",
        )

        resp = build_sync_job_status_response(job)
        payload = resp.model_dump(mode="json")

        # Status response has only job-level aggregate counts
        assert "completed_tables" in payload
        assert "total_tables" in payload
        assert "completed_fields" in payload
        assert "total_fields" in payload
        assert "current_table_name" in payload
        # No per-table row detail fields leak into the polling response
        assert "staged_rows" not in payload
        assert "table_details" not in payload


# ===========================================================================
# 2. Progress write frequency bounded
# ===========================================================================


class TestProgressWriteFrequencyBounded:
    """Verify increment_sync_job_progress throttles DB writes."""

    def test_rapid_increments_commit_at_most_once_per_threshold(
        self,
        progress_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=200, oid=1, create_by=1, total_tables=100
        )

        # Set a very high threshold so NO commits happen from throttling
        monkeypatch.setattr(
            "apps.datasource.crud.sync_job.settings"
            ".DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
            9999,
        )
        commit_count = 0
        original_commit = test_db.commit

        def counting_commit() -> None:
            nonlocal commit_count
            commit_count += 1
            original_commit()

        monkeypatch.setattr(test_db, "commit", counting_commit)

        # Call increment 10 times — all should be absorbed in-memory
        for i in range(10):
            increment_sync_job_progress(
                test_db,
                job=job,
                completed_tables_delta=1,
                completed_fields_delta=5,
                current_table_name=f"table_{i}",
            )

        # No commits should have happened (throttled)
        assert commit_count == 0
        # But in-memory accumulates all deltas
        assert job.completed_tables == 10
        assert job.completed_fields == 50

    def test_force_commit_overrides_throttle(
        self,
        progress_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=201, oid=1, create_by=1, total_tables=50
        )

        monkeypatch.setattr(
            "apps.datasource.crud.sync_job.settings"
            ".DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
            9999,
        )
        commit_count = 0
        original_commit = test_db.commit

        def counting_commit() -> None:
            nonlocal commit_count
            commit_count += 1
            original_commit()

        monkeypatch.setattr(test_db, "commit", counting_commit)

        increment_sync_job_progress(
            test_db,
            job=job,
            completed_tables_delta=3,
            completed_fields_delta=15,
        )
        assert commit_count == 0

        increment_sync_job_progress(
            test_db,
            job=job,
            completed_tables_delta=2,
            completed_fields_delta=10,
            force_commit=True,
        )
        assert commit_count == 1
        assert job.completed_tables == 5
        assert job.completed_fields == 25

    def test_zero_threshold_commits_every_call(
        self,
        progress_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=202, oid=1, create_by=1, total_tables=20
        )
        commit_count = 0
        original_commit = test_db.commit

        def counting_commit() -> None:
            nonlocal commit_count
            commit_count += 1
            original_commit()

        monkeypatch.setattr(test_db, "commit", counting_commit)
        monkeypatch.setattr(
            "apps.datasource.crud.sync_job.settings"
            ".DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
            0,
        )

        for _ in range(5):
            increment_sync_job_progress(
                test_db,
                job=job,
                completed_tables_delta=1,
            )

        assert commit_count == 5

    def test_mixed_delta_types_accumulate_correctly(
        self,
        progress_tables: None,
        test_db: Session,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=203, oid=1, create_by=1, total_tables=30
        )
        monkeypatch.setattr(
            "apps.datasource.crud.sync_job.settings"
            ".DATASOURCE_SYNC_JOB_PROGRESS_INTERVAL_SECONDS",
            0,
        )

        increment_sync_job_progress(
            test_db,
            job=job,
            completed_tables_delta=5,
            failed_tables_delta=1,
            skipped_tables_delta=2,
            completed_fields_delta=50,
            total_fields_delta=100,
        )
        increment_sync_job_progress(
            test_db,
            job=job,
            completed_tables_delta=3,
            failed_tables_delta=1,
            skipped_tables_delta=1,
            completed_fields_delta=30,
            total_fields_delta=20,
        )

        fresh = get_sync_job_by_id(test_db, cast(int, job.id))
        assert fresh is not None
        assert fresh.completed_tables == 8
        assert fresh.failed_tables == 2
        assert fresh.skipped_tables == 3
        assert fresh.completed_fields == 80
        assert fresh.total_fields == 120


# ===========================================================================
# 3. SSE payload format
# ===========================================================================


class TestSSEPayloadFormat:
    """Verify SSE events use data:{json}\\n\\n framing consistent with chat events."""

    def test_progress_event_framing(
        self,
        progress_tables: None,
        test_db: Session,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=300, oid=1, create_by=1, total_tables=10, total_fields=100
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            completed_tables=5,
            completed_fields=50,
            current_table_name="orders",
        )

        sf = FakeSessionFactory(test_db)
        first_event = next(
            iter_sync_job_events(sf, cast(int, job.id), poll_interval_seconds=0)
        )

        # Verify SSE framing: data:{json}\n\n
        assert first_event.startswith("data:")
        assert first_event.endswith("\n\n")

        # Parse the JSON payload
        payload = _parse_sse_event(first_event)

        # Must have type field matching chat event pattern
        assert "type" in payload
        assert payload["type"] == "sync_progress"

        # Must have all SyncJobStatusResponse fields
        assert payload["job_id"] == cast(int, job.id)
        assert payload["datasource_id"] == 300
        assert payload["status"] == "running"
        assert payload["phase"] == "stage"
        assert payload["total_tables"] == 10
        assert payload["completed_tables"] == 5
        assert payload["completed_fields"] == 50
        assert payload["current_table_name"] == "orders"

    def test_finish_event_format(
        self,
        progress_tables: None,
        test_db: Session,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=301, oid=1, create_by=1, total_tables=5
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.SUCCEEDED,
            phase=SyncJobPhase.FINALIZE,
            completed_tables=5,
        )

        sf = FakeSessionFactory(test_db)
        events = list(
            iter_sync_job_events(sf, cast(int, job.id), poll_interval_seconds=0)
        )
        # Terminal: exactly 2 events — progress + finish
        assert len(events) == 2

        finish = _parse_sse_event(events[1])
        assert finish == {"type": "finish"}

    def test_error_event_format_for_missing_job(
        self,
        progress_tables: None,
        test_db: Session,
    ) -> None:
        _ = progress_tables
        sf = FakeSessionFactory(test_db)
        events = list(iter_sync_job_events(sf, 99999, poll_interval_seconds=0))

        assert len(events) == 2
        error_event = _parse_sse_event(events[0])
        assert error_event["type"] == "error"
        assert error_event["content"] == "sync job not found"

        finish_event = _parse_sse_event(events[1])
        assert finish_event == {"type": "finish"}

    def test_sse_events_are_parseable_by_json(
        self,
        progress_tables: None,
        test_db: Session,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=302, oid=1, create_by=1, total_tables=3, total_fields=30
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.PARTIAL,
            phase=SyncJobPhase.FINALIZE,
            completed_tables=2,
            failed_tables=1,
            completed_fields=20,
            error_summary="1 of 3 tables failed",
        )

        sf = FakeSessionFactory(test_db)
        events = list(
            iter_sync_job_events(sf, cast(int, job.id), poll_interval_seconds=0)
        )

        # Every event must be valid JSON after stripping data: prefix
        for raw_event in events:
            payload = _parse_sse_event(raw_event)
            assert isinstance(payload, dict)
            assert "type" in payload

    def test_sse_progress_event_includes_all_status_fields(
        self,
        progress_tables: None,
        test_db: Session,
    ) -> None:
        _ = progress_tables
        job = create_sync_job(
            test_db, ds_id=303, oid=1, create_by=1, total_tables=6, total_fields=60
        )
        update_sync_job_status(
            test_db,
            job=job,
            status=SyncJobStatus.RUNNING,
            phase=SyncJobPhase.STAGE,
            completed_tables=3,
            failed_tables=1,
            skipped_tables=1,
            completed_fields=30,
            current_table_name="products",
        )

        sf = FakeSessionFactory(test_db)
        first_event = next(
            iter_sync_job_events(sf, cast(int, job.id), poll_interval_seconds=0)
        )
        payload = _parse_sse_event(first_event)

        expected_fields = {
            "job_id",
            "datasource_id",
            "status",
            "phase",
            "total_tables",
            "completed_tables",
            "failed_tables",
            "skipped_tables",
            "total_fields",
            "completed_fields",
            "current_table_name",
            "embedding_followup_status",
            "error_summary",
            "create_time",
            "update_time",
            "start_time",
            "finish_time",
        }
        assert expected_fields.issubset(set(payload.keys()))
        assert "type" in payload
        assert payload["type"] == "sync_progress"
