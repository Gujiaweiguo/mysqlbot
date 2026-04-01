#!/usr/bin/env python3
"""Run performance baseline test for async datasource sync."""

from __future__ import annotations

import sys

from sqlmodel import Session

from apps.datasource.crud.datasource import getTables
from apps.datasource.crud.sync_job import (
    get_sync_job_by_id,
    submit_datasource_sync_job,
)
from apps.datasource.models.datasource import (
    CoreDatasource,
    SelectedTablePayload,
)
from common.core.db import engine
from common.utils.sync_job_runtime import dispatch_sync_job


def main(ds_id: int) -> None:
    with Session(engine) as session:
        ds = session.get(CoreDatasource, ds_id)
        if ds is None:
            print(f"ERROR: datasource {ds_id} not found")
            sys.exit(1)

        raw_tables = getTables(session, ds_id)
        if not raw_tables:
            print("ERROR: no tables found")
            sys.exit(1)

        tables = [
            SelectedTablePayload(
                table_name=item.tableName,
                table_comment=item.tableComment or "",
            )
            for item in raw_tables
        ]
        total = len(tables)
        print(f"Submitting sync job for {total} tables on datasource {ds_id}...")

        resp = submit_datasource_sync_job(
            session,
            ds_id=ds_id,
            oid=ds.oid,
            create_by=1,
            total_tables=total,
            requested_tables=tables,
        )
        job_id = resp.job_id
        print(f"Job {job_id} submitted (status={resp.status.value})")

        future = dispatch_sync_job(job_id)
        print("Dispatched, waiting for completion...")

        future.result(timeout=600)

        job = get_sync_job_by_id(session, job_id)
        if job is None:
            print("ERROR: job vanished")
            sys.exit(1)

        elapsed = 0.0
        if job.start_time and job.finish_time:
            elapsed = (job.finish_time - job.start_time).total_seconds()

        print(
            f"\nJob {job_id} finished: status={job.status.value} "
            f"tables={job.total_tables} fields={job.total_fields} "
            f"elapsed={elapsed:.1f}s"
        )


if __name__ == "__main__":
    ds_id = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    main(ds_id)
