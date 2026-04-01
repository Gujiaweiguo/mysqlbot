#!/usr/bin/env python3
"""Generate test schemas with N tables for performance baseline testing."""

from __future__ import annotations

import argparse
import time

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

PG_HOST = "localhost"
PG_PORT = 15432
PG_USER = "sqlbot_user"
PG_PASSWORD = "DevOnly@123456"
PG_DB = "sqlbot"

COLUMN_TEMPLATES = [
    ("id", "bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY"),
    ("name", "text"),
    ("score", "numeric(12,2)"),
    ("is_active", "boolean"),
    ("created_at", "timestamp"),
]


def create_perf_schema(table_count: int) -> str:
    schema_name = f"perf_baseline_{table_count}"

    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    try:
        cur.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        cur.execute(f"CREATE SCHEMA {schema_name}")

        print(f"Creating {table_count} tables in schema `{schema_name}`...")

        start = time.time()
        for i in range(table_count):
            table_name = f"t_{i:04d}"
            cols = ", ".join(f"{name} {dtype}" for name, dtype in COLUMN_TEMPLATES)
            cur.execute(f"CREATE TABLE {schema_name}.{table_name} ({cols})")

            if (i + 1) % 100 == 0:
                elapsed = time.time() - start
                print(f"  Created {i + 1}/{table_count} tables ({elapsed:.1f}s)")

        total_elapsed = time.time() - start
        print(f"Done! Created {table_count} tables in {total_elapsed:.1f}s")

        print("\n--- Connection Info ---")
        print(f"Host: {PG_HOST}:{PG_PORT}")
        print(f"Database: {PG_DB}")
        print(f"Schema: {schema_name}")
        print(
            f"Connection string: postgresql://{PG_USER}:***@{PG_HOST}:{PG_PORT}/{PG_DB}"
        )

        return schema_name

    finally:
        cur.close()
        conn.close()


def drop_perf_schema(table_count: int) -> None:
    schema_name = f"perf_baseline_{table_count}"

    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    try:
        cur.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        print(f"Dropped schema `{schema_name}`")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate performance test schema")
    parser.add_argument(
        "--count",
        type=int,
        required=True,
        help="Number of tables to create (e.g., 500, 1000)",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop the schema instead of creating it",
    )
    args = parser.parse_args()

    if args.drop:
        drop_perf_schema(args.count)
    else:
        create_perf_schema(args.count)
