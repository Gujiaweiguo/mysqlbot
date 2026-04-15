#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    script_path = Path(__file__).resolve().parent / "setup_mallbi_demo.py"
    repo_root = script_path.parents[2]

    command = [
        sys.executable,
        str(script_path),
        "--workspace-name",
        "scrm",
        "--datasource-name",
        "GS SCRM",
        "--datasource-description",
        "GS SCRM analytics datasource",
        "--database-name",
        "gs_scrm",
        "--db-schema",
        "public",
        "--schema-file",
        str(repo_root / "gs_scrm_pg.sql"),
        "--seed-file",
        str(
            repo_root
            / "backend"
            / "scripts"
            / "regression"
            / "gs_scrm_member_analytics_seed.sql"
        ),
        *sys.argv[1:],
    ]

    if any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
        _ = subprocess.run(command, check=True)
        return

    completed = subprocess.run(command, check=True, capture_output=True, text=True)

    if completed.stdout.strip() != "":
        print(completed.stdout, end="")
    if completed.stderr.strip() != "":
        print(completed.stderr, end="", file=sys.stderr)

    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Failed to parse setup summary JSON") from exc

    datasource_ok = bool(summary.get("datasource_ok"))
    available_table_count = int(summary.get("available_table_count", 0))
    synced_table_count = int(summary.get("synced_table_count", 0))
    if not datasource_ok:
        raise RuntimeError("gs_scrm datasource check failed")
    if available_table_count <= 0:
        raise RuntimeError("gs_scrm datasource has zero available tables")
    if synced_table_count != available_table_count:
        raise RuntimeError(
            "gs_scrm datasource table sync incomplete: "
            f"{synced_table_count}/{available_table_count}"
        )


if __name__ == "__main__":
    main()
