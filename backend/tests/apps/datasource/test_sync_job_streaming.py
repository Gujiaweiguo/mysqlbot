from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any, cast

import pytest
from sqlmodel import Session, SQLModel

from apps.datasource.api.sync_job_streaming import iter_sync_job_events
from apps.datasource.crud.sync_job import create_sync_job, update_sync_job_status
from apps.datasource.models.sync_job import (
    DatasourceSyncJob,
    SyncJobPhase,
    SyncJobStatus,
)


@pytest.fixture
def sync_job_stream_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [cast(Any, DatasourceSyncJob).__table__]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


class FakeSessionFactory:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.remove_calls = 0

    def __call__(self) -> Session:
        return self.session

    def remove(self) -> None:
        self.remove_calls += 1


def test_iter_sync_job_events_emits_terminal_progress_and_finish(
    sync_job_stream_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_stream_tables
    job = create_sync_job(test_db, ds_id=7, oid=1, create_by=1, total_tables=20)
    update_sync_job_status(
        test_db,
        job=job,
        status=SyncJobStatus.SUCCEEDED,
        phase=SyncJobPhase.FINALIZE,
        completed_tables=20,
        completed_fields=100,
    )
    session_factory = FakeSessionFactory(test_db)

    events = list(
        iter_sync_job_events(
            session_factory,
            cast(int, job.id),
            poll_interval_seconds=0,
        )
    )

    assert len(events) == 2
    assert events[0].startswith("data:")
    payload = json.loads(events[0][5:].strip())
    assert payload["type"] == "sync_progress"
    assert payload["job_id"] == cast(int, job.id)
    assert payload["status"] == "succeeded"
    assert payload["phase"] == "finalize"
    finish_payload = json.loads(events[1][5:].strip())
    assert finish_payload == {"type": "finish"}


def test_iter_sync_job_events_emits_error_for_missing_job(
    sync_job_stream_tables: None,
    test_db: Session,
) -> None:
    _ = sync_job_stream_tables
    session_factory = FakeSessionFactory(test_db)
    events = list(iter_sync_job_events(session_factory, 999, poll_interval_seconds=0))

    assert len(events) == 2
    error_payload = json.loads(events[0][5:].strip())
    assert error_payload["type"] == "error"
    assert error_payload["content"] == "sync job not found"
    finish_payload = json.loads(events[1][5:].strip())
    assert finish_payload == {"type": "finish"}
