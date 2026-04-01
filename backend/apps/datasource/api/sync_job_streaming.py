from __future__ import annotations

from collections.abc import Iterator
from time import sleep

from apps.chat.streaming.events import (
    emit_chat_error,
    emit_chat_event,
    emit_finish_event,
)
from apps.datasource.crud.sync_job import (
    build_sync_job_status_response,
    get_sync_job_by_id,
)
from apps.datasource.models.sync_job import TERMINAL_DATASOURCE_SYNC_JOB_STATUSES
from common.utils.sync_job_runtime import SyncJobSessionFactory


def iter_sync_job_events(
    session_factory: SyncJobSessionFactory,
    job_id: int,
    *,
    poll_interval_seconds: int,
) -> Iterator[str]:
    while True:
        session = session_factory()
        try:
            job = get_sync_job_by_id(session, job_id)
            if job is None:
                yield emit_chat_error("sync job not found")
                yield emit_finish_event()
                return
            payload = build_sync_job_status_response(job).model_dump(mode="json")
            yield emit_chat_event("sync_progress", **payload)
            if job.status in TERMINAL_DATASOURCE_SYNC_JOB_STATUSES:
                yield emit_finish_event()
                return
        finally:
            session.close()
            session_factory.remove()
        sleep(poll_interval_seconds)
