#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import httpx
import psycopg
from psycopg import sql

from apps.datasource.utils.utils import aes_encrypt

_RUNTIME_ROOT = Path(__file__).resolve().parents[1] / ".runtime"
_ = os.environ.setdefault("BASE_DIR", str(_RUNTIME_ROOT))
_ = os.environ.setdefault("UPLOAD_DIR", str(_RUNTIME_ROOT / "data" / "file"))
_ = os.environ.setdefault("LOG_DIR", str(_RUNTIME_ROOT / "logs"))

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class SetupConfig:
    base_url: str
    admin_username: str
    admin_password: str
    admin_pg_host: str
    admin_pg_port: int
    admin_pg_user: str
    admin_pg_password: str
    datasource_pg_host: str
    datasource_pg_port: int
    datasource_pg_user: str
    datasource_pg_password: str
    database_name: str
    db_schema: str
    workspace_name: str
    datasource_name: str
    datasource_description: str
    schema_file: Path
    seed_file: Path
    pg_container: str | None
    restore_workspace: bool
    timeout: float


@dataclass(frozen=True)
class SetupSummary:
    workspace_id: int
    workspace_name: str
    workspace_created: bool
    datasource_id: int
    datasource_name: str
    datasource_created: bool
    datasource_ok: bool
    available_table_count: int
    synced_table_count: int
    original_workspace_id: int
    restored_workspace_id: int | None
    database_name: str
    db_schema: str


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "" or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _default_value(
    env_values: dict[str, str], keys: tuple[str, ...], fallback: str
) -> str:
    for key in keys:
        value = os.getenv(key) or env_values.get(key)
        if isinstance(value, str) and value.strip() != "":
            return value.strip()
    return fallback


def _require_identifier(name: str, label: str) -> None:
    if IDENTIFIER_RE.fullmatch(name) is None:
        raise ValueError(f"{label} must match {IDENTIFIER_RE.pattern}, got {name!r}")


def _unwrap_payload(payload: object) -> object:
    if isinstance(payload, dict) and {"code", "data", "msg"}.issubset(payload):
        payload_dict = cast(dict[str, object], payload)
        return payload_dict["data"]
    return payload


def _response_payload(response: httpx.Response) -> object:
    return cast(object, response.json())


def _expect_dict(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{label} expected dict payload, got {type(payload).__name__}"
        )
    return cast(dict[str, object], payload)


def _expect_list(payload: object, label: str) -> list[object]:
    if not isinstance(payload, list):
        raise RuntimeError(
            f"{label} expected list payload, got {type(payload).__name__}"
        )
    return cast(list[object], payload)


def _expect_int(value: object, label: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise RuntimeError(f"{label} expected int-like value, got {value!r}")


def _parse_args() -> SetupConfig:
    repo_root = Path(__file__).resolve().parents[2]
    env_values = _load_env_file(repo_root / ".env")

    parser = argparse.ArgumentParser(
        description="Initialize cre_bi_demo database and the mallbi datasource idempotently."
    )
    _ = parser.add_argument(
        "--base-url",
        default=_default_value(
            env_values, ("SQLBOT_BASE_URL",), "http://127.0.0.1:8000"
        ),
    )
    _ = parser.add_argument(
        "--admin-username",
        default=_default_value(env_values, ("SQLBOT_ADMIN_USERNAME",), "admin"),
    )
    _ = parser.add_argument(
        "--admin-password",
        default=_default_value(
            env_values, ("DEFAULT_PWD", "SQLBOT_DEFAULT_PWD"), "mySQLBot@123456"
        ),
    )
    _ = parser.add_argument(
        "--admin-pg-host",
        default=_default_value(
            env_values,
            ("DEMO_ADMIN_PG_HOST", "POSTGRES_SERVER", "SQLBOT_DEV_PG_HOST"),
            "localhost",
        ),
    )
    _ = parser.add_argument(
        "--admin-pg-port",
        type=int,
        default=int(
            _default_value(
                env_values,
                ("DEMO_ADMIN_PG_PORT", "POSTGRES_PORT", "SQLBOT_DEV_PG_PORT"),
                "15432",
            )
        ),
    )
    _ = parser.add_argument(
        "--admin-pg-user",
        default=_default_value(
            env_values,
            ("DEMO_ADMIN_PG_USER", "POSTGRES_USER", "SQLBOT_DEV_PG_USER"),
            "sqlbot_user",
        ),
    )
    _ = parser.add_argument(
        "--admin-pg-password",
        default=_default_value(
            env_values,
            ("DEMO_ADMIN_PG_PASSWORD", "POSTGRES_PASSWORD", "SQLBOT_DEV_PG_PASSWORD"),
            "DevOnly@123456",
        ),
    )
    _ = parser.add_argument("--datasource-pg-host", default=None)
    _ = parser.add_argument("--datasource-pg-port", type=int, default=None)
    _ = parser.add_argument("--datasource-pg-user", default=None)
    _ = parser.add_argument("--datasource-pg-password", default=None)
    _ = parser.add_argument("--database-name", default="cre_bi_demo")
    _ = parser.add_argument("--db-schema", default="cre_bi_demo")
    _ = parser.add_argument("--workspace-name", default="mallbi")
    _ = parser.add_argument("--datasource-name", default="CRE BI Demo")
    _ = parser.add_argument(
        "--datasource-description", default="CRE BI demo datasource"
    )
    _ = parser.add_argument(
        "--schema-file", type=Path, default=repo_root / "postgres_demo_schema.sql"
    )
    _ = parser.add_argument(
        "--seed-file", type=Path, default=repo_root / "postgres_demo_seed.sql"
    )
    _ = parser.add_argument("--pg-container", default=os.getenv("DEMO_PG_CONTAINER"))
    _ = parser.add_argument("--timeout", type=float, default=120.0)
    _ = parser.add_argument("--no-restore-workspace", action="store_true")
    args = parser.parse_args()

    datasource_pg_host = cast(str | None, args.datasource_pg_host) or _default_value(
        env_values,
        ("DEMO_DATASOURCE_PG_HOST", "POSTGRES_SERVER", "SQLBOT_DEV_PG_HOST"),
        cast(str, args.admin_pg_host),
    )
    datasource_pg_port = cast(int | None, args.datasource_pg_port)
    if datasource_pg_port is None:
        datasource_pg_port = int(
            _default_value(
                env_values,
                ("DEMO_DATASOURCE_PG_PORT", "POSTGRES_PORT", "SQLBOT_DEV_PG_PORT"),
                str(cast(int, args.admin_pg_port)),
            )
        )
    datasource_pg_user = cast(str | None, args.datasource_pg_user) or _default_value(
        env_values,
        ("DEMO_DATASOURCE_PG_USER", "POSTGRES_USER", "SQLBOT_DEV_PG_USER"),
        cast(str, args.admin_pg_user),
    )
    datasource_pg_password = cast(
        str | None, args.datasource_pg_password
    ) or _default_value(
        env_values,
        ("DEMO_DATASOURCE_PG_PASSWORD", "POSTGRES_PASSWORD", "SQLBOT_DEV_PG_PASSWORD"),
        cast(str, args.admin_pg_password),
    )

    schema_file = cast(Path, args.schema_file).resolve()
    seed_file = cast(Path, args.seed_file).resolve()
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    if not seed_file.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_file}")

    database_name = cast(str, args.database_name)
    db_schema = cast(str, args.db_schema)
    _require_identifier(database_name, "database_name")
    _require_identifier(db_schema, "db_schema")

    return SetupConfig(
        base_url=cast(str, args.base_url),
        admin_username=cast(str, args.admin_username),
        admin_password=cast(str, args.admin_password),
        admin_pg_host=cast(str, args.admin_pg_host),
        admin_pg_port=cast(int, args.admin_pg_port),
        admin_pg_user=cast(str, args.admin_pg_user),
        admin_pg_password=cast(str, args.admin_pg_password),
        datasource_pg_host=datasource_pg_host,
        datasource_pg_port=datasource_pg_port,
        datasource_pg_user=datasource_pg_user,
        datasource_pg_password=datasource_pg_password,
        database_name=database_name,
        db_schema=db_schema,
        workspace_name=cast(str, args.workspace_name),
        datasource_name=cast(str, args.datasource_name),
        datasource_description=cast(str, args.datasource_description),
        schema_file=schema_file,
        seed_file=seed_file,
        pg_container=cast(str | None, args.pg_container),
        restore_workspace=not cast(bool, args.no_restore_workspace),
        timeout=cast(float, args.timeout),
    )


def _run_psql_in_container(
    *,
    cfg: SetupConfig,
    database: str,
    sql_text: str,
    capture_output: bool,
) -> subprocess.CompletedProcess[str]:
    if not cfg.pg_container:
        raise RuntimeError(
            "pg_container is required for containerized PostgreSQL execution"
        )
    command = [
        "docker",
        "exec",
        "-i",
        "-e",
        f"PGPASSWORD={cfg.admin_pg_password}",
        cfg.pg_container,
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        cfg.admin_pg_user,
        "-d",
        database,
    ]
    return subprocess.run(
        command,
        input=sql_text,
        text=True,
        capture_output=capture_output,
        check=True,
    )


def _setup_database_via_container(cfg: SetupConfig) -> None:
    select_sql = f"SELECT 1 FROM pg_database WHERE datname = '{cfg.database_name}';"
    result = _run_psql_in_container(
        cfg=cfg,
        database="postgres",
        sql_text=select_sql,
        capture_output=True,
    )
    if "1" not in result.stdout.split():
        _ = _run_psql_in_container(
            cfg=cfg,
            database="postgres",
            sql_text=f"CREATE DATABASE {cfg.database_name};",
            capture_output=True,
        )

    _ = _run_psql_in_container(
        cfg=cfg,
        database=cfg.database_name,
        sql_text=cfg.schema_file.read_text(encoding="utf-8"),
        capture_output=True,
    )
    _ = _run_psql_in_container(
        cfg=cfg,
        database=cfg.database_name,
        sql_text=cfg.seed_file.read_text(encoding="utf-8"),
        capture_output=True,
    )


def _setup_database_via_connection(cfg: SetupConfig) -> None:
    with psycopg.connect(
        host=cfg.admin_pg_host,
        port=cfg.admin_pg_port,
        dbname="postgres",
        user=cfg.admin_pg_user,
        password=cfg.admin_pg_password,
        autocommit=True,
    ) as conn:
        with conn.cursor() as cur:
            _ = cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (cfg.database_name,)
            )
            exists = cur.fetchone() is not None
            if not exists:
                _ = cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(cfg.database_name)
                    )
                )

    schema_sql = cfg.schema_file.read_text(encoding="utf-8")
    seed_sql = cfg.seed_file.read_text(encoding="utf-8")
    with psycopg.connect(
        host=cfg.admin_pg_host,
        port=cfg.admin_pg_port,
        dbname=cfg.database_name,
        user=cfg.admin_pg_user,
        password=cfg.admin_pg_password,
        autocommit=False,
    ) as conn:
        with conn.cursor() as cur:
            execute_sql = cast(object, getattr(cur, "execute"))
            if not callable(execute_sql):
                raise RuntimeError("psycopg cursor.execute is not callable")
            _ = execute_sql(schema_sql)
            _ = execute_sql(seed_sql)
        conn.commit()


def _setup_database(cfg: SetupConfig) -> None:
    if cfg.pg_container:
        _setup_database_via_container(cfg)
        return
    _setup_database_via_connection(cfg)


async def _login_token(client: httpx.AsyncClient, cfg: SetupConfig) -> str:
    response = await client.post(
        "/api/v1/login/access-token",
        data={"username": cfg.admin_username, "password": cfg.admin_password},
    )
    response.raise_for_status()
    payload = _expect_dict(
        _unwrap_payload(_response_payload(response)), "login response"
    )
    token = payload.get("access_token")
    if not isinstance(token, str) or token == "":
        raise RuntimeError("login response missing access_token")
    return token


async def _ensure_workspace(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    workspace_name: str,
) -> tuple[int, bool]:
    response = await client.get("/api/v1/system/workspace", headers=headers)
    response.raise_for_status()
    workspace_list = _expect_list(
        _unwrap_payload(_response_payload(response)),
        "workspace list",
    )
    for item in workspace_list:
        workspace = _expect_dict(item, "workspace item")
        if workspace.get("name") == workspace_name:
            return _expect_int(workspace.get("id"), "workspace.id"), False

    response = await client.post(
        "/api/v1/system/workspace",
        headers=headers,
        json={"name": workspace_name},
    )
    response.raise_for_status()
    workspace = _expect_dict(
        _unwrap_payload(_response_payload(response)),
        "workspace create response",
    )
    return _expect_int(workspace.get("id"), "workspace.id"), True


async def _ensure_datasource(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    cfg: SetupConfig,
    workspace_id: int,
) -> tuple[int, bool, bool, int, int]:
    response = await client.get("/api/v1/datasource/list", headers=headers)
    response.raise_for_status()
    datasource_list = _expect_list(
        _unwrap_payload(_response_payload(response)),
        "datasource list",
    )

    datasource_id: int | None = None
    datasource_created = False
    for item in datasource_list:
        datasource = _expect_dict(item, "datasource item")
        if datasource.get("name") == cfg.datasource_name:
            datasource_id = _expect_int(datasource.get("id"), "datasource.id")
            break

    if datasource_id is None:
        config = {
            "host": cfg.datasource_pg_host,
            "port": cfg.datasource_pg_port,
            "username": cfg.datasource_pg_user,
            "password": cfg.datasource_pg_password,
            "database": cfg.database_name,
            "driver": "",
            "extraJdbc": "",
            "dbSchema": cfg.db_schema,
            "filename": "",
            "sheets": [],
            "mode": "",
            "timeout": 30,
            "lowVersion": False,
        }
        payload = {
            "name": cfg.datasource_name,
            "description": cfg.datasource_description,
            "type": "pg",
            "configuration": aes_encrypt(json.dumps(config, ensure_ascii=False)).decode(
                "utf-8"
            ),
            "oid": workspace_id,
            "tables": [],
        }
        response = await client.post(
            "/api/v1/datasource/add", headers=headers, json=payload
        )
        response.raise_for_status()
        datasource = _expect_dict(
            _unwrap_payload(_response_payload(response)),
            "datasource create response",
        )
        datasource_id = _expect_int(datasource.get("id"), "datasource.id")
        datasource_created = True

    response = await client.get(
        f"/api/v1/datasource/check/{datasource_id}", headers=headers
    )
    response.raise_for_status()
    datasource_ok_obj = _unwrap_payload(_response_payload(response))
    if not isinstance(datasource_ok_obj, bool):
        raise RuntimeError("datasource check response missing boolean payload")

    response = await client.post(
        f"/api/v1/datasource/getTables/{datasource_id}", headers=headers
    )
    response.raise_for_status()
    available_tables_raw = _expect_list(
        _unwrap_payload(_response_payload(response)),
        "available tables",
    )
    available_tables: list[dict[str, object]] = [
        _expect_dict(item, "available table item") for item in available_tables_raw
    ]

    response = await client.post(
        f"/api/v1/datasource/tableList/{datasource_id}", headers=headers
    )
    response.raise_for_status()
    synced_tables = _expect_list(
        _unwrap_payload(_response_payload(response)),
        "synced tables",
    )

    if len(synced_tables) < len(available_tables):
        choose_payload = [
            {
                "table_name": cast(str, item.get("tableName")),
                "table_comment": cast(str | None, item.get("tableComment")) or "",
            }
            for item in available_tables
        ]
        response = await client.post(
            f"/api/v1/datasource/chooseTables/{datasource_id}",
            headers=headers,
            json=choose_payload,
        )
        response.raise_for_status()
        response = await client.post(
            f"/api/v1/datasource/tableList/{datasource_id}", headers=headers
        )
        response.raise_for_status()
        synced_tables = _expect_list(
            _unwrap_payload(_response_payload(response)),
            "synced tables after sync",
        )

    return (
        datasource_id,
        datasource_created,
        datasource_ok_obj,
        len(available_tables),
        len(synced_tables),
    )


async def _run_setup(cfg: SetupConfig) -> SetupSummary:
    _setup_database(cfg)

    async with httpx.AsyncClient(base_url=cfg.base_url, timeout=cfg.timeout) as client:
        token = await _login_token(client, cfg)
        headers = {"X-SQLBOT-TOKEN": f"Bearer {token}"}

        response = await client.get("/api/v1/user/info", headers=headers)
        response.raise_for_status()
        current_user = _expect_dict(
            _unwrap_payload(_response_payload(response)),
            "current user",
        )
        original_workspace_id = _expect_int(current_user.get("oid"), "current_user.oid")

        workspace_id, workspace_created = await _ensure_workspace(
            client,
            headers,
            cfg.workspace_name,
        )

        restored_workspace_id: int | None = None
        switch_response = await client.put(
            f"/api/v1/user/ws/{workspace_id}", headers=headers
        )
        switch_response.raise_for_status()
        try:
            (
                datasource_id,
                datasource_created,
                datasource_ok,
                available_table_count,
                synced_table_count,
            ) = await _ensure_datasource(client, headers, cfg, workspace_id)
        finally:
            if cfg.restore_workspace and original_workspace_id != workspace_id:
                restore_response = await client.put(
                    f"/api/v1/user/ws/{original_workspace_id}",
                    headers=headers,
                )
                restore_response.raise_for_status()
                restored_workspace_id = original_workspace_id

    return SetupSummary(
        workspace_id=workspace_id,
        workspace_name=cfg.workspace_name,
        workspace_created=workspace_created,
        datasource_id=datasource_id,
        datasource_name=cfg.datasource_name,
        datasource_created=datasource_created,
        datasource_ok=datasource_ok,
        available_table_count=available_table_count,
        synced_table_count=synced_table_count,
        original_workspace_id=original_workspace_id,
        restored_workspace_id=restored_workspace_id,
        database_name=cfg.database_name,
        db_schema=cfg.db_schema,
    )


def main() -> None:
    cfg = _parse_args()
    summary = asyncio.run(_run_setup(cfg))
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
