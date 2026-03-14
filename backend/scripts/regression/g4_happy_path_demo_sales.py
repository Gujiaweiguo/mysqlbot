#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

import httpx


@dataclass(frozen=True)
class PromptCase:
    case_id: str
    question: str
    expectation: str


PROMPT_CASES: tuple[PromptCase, ...] = (
    PromptCase(
        "g4-aggregation",
        "最近订单总金额是多少？",
        "SQL executes and returns a single aggregate result",
    ),
    PromptCase(
        "g4-group-stat",
        "每个客户的订单金额汇总，按金额降序",
        "Grouped rows are returned and sorted by amount descending",
    ),
    PromptCase(
        "g4-status-dist",
        "订单状态分别有多少条？",
        "Status dimension count rows are returned",
    ),
)

_runtime_root = Path(__file__).resolve().parents[2] / ".runtime"
os.environ.setdefault("BASE_DIR", str(_runtime_root))
os.environ.setdefault("UPLOAD_DIR", str(_runtime_root / "data" / "file"))
os.environ.setdefault("LOG_DIR", str(_runtime_root / "logs"))


def _parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    default_output = (
        repo_root
        / "docs"
        / "regression"
        / "evidence"
        / f"g4-happy-path-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )

    parser = argparse.ArgumentParser(
        description="Run G4 demo_sales happy-path regression via API"
    )
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000", help="Backend base URL"
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Optional pre-issued JWT token; skips login if provided",
    )
    parser.add_argument("--username", default="admin", help="Login username")
    parser.add_argument("--password", default="mySQLBot@123456", help="Login password")
    parser.add_argument(
        "--schema", default="demo_sales", help="Target datasource schema"
    )
    parser.add_argument(
        "--datasource-id",
        type=int,
        default=None,
        help="Optional explicit datasource id",
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="HTTP timeout seconds"
    )
    parser.add_argument(
        "--output", default=str(default_output), help="Evidence JSON output path"
    )
    return parser.parse_args()


def _unwrap_payload(payload: object) -> object:
    if isinstance(payload, dict) and {"code", "data", "msg"}.issubset(payload):
        return payload["data"]
    return payload


def _expect_dict(payload: object, name: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{name} expected dict payload, got {type(payload).__name__}"
        )
    return cast(dict[str, object], payload)


def _expect_list(payload: object, name: str) -> list[object]:
    if not isinstance(payload, list):
        raise RuntimeError(
            f"{name} expected list payload, got {type(payload).__name__}"
        )
    return cast(list[object], payload)


def _to_int(value: object, name: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise RuntimeError(f"{name} expected int-like value, got {value!r}")


async def _login_token(
    client: httpx.AsyncClient,
    username: str,
    password: str,
    token_override: str | None,
) -> str:
    if isinstance(token_override, str) and token_override.strip():
        return token_override.strip()

    response = await client.post(
        "/api/v1/mcp/mcp_start",
        json={"username": username, "password": password},
    )
    response.raise_for_status()
    payload = _expect_dict(_unwrap_payload(response.json()), "login response")
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("login response missing access_token")
    return token


def _parse_config_schema(configuration: object) -> str | None:
    if not isinstance(configuration, str) or not configuration.strip():
        return None
    try:
        config_obj = json.loads(configuration)
    except json.JSONDecodeError:
        return None
    if not isinstance(config_obj, dict):
        return None
    db_schema = config_obj.get("dbSchema")
    return db_schema if isinstance(db_schema, str) and db_schema else None


async def _resolve_datasource_id(
    client: httpx.AsyncClient,
    token_header: dict[str, str],
    schema: str,
    preferred_id: int | None,
) -> int:
    response = await client.get("/api/v1/datasource/list", headers=token_header)
    response.raise_for_status()
    raw_list = _expect_list(_unwrap_payload(response.json()), "datasource list")

    candidates: list[dict[str, object]] = []
    for item in raw_list:
        if isinstance(item, dict):
            candidates.append(cast(dict[str, object], item))

    if preferred_id is not None:
        for ds in candidates:
            if _to_int(ds.get("id"), "datasource.id") == preferred_id:
                return preferred_id
        raise RuntimeError(
            f"datasource id {preferred_id} not found in /datasource/list"
        )

    for ds in candidates:
        config_schema = _parse_config_schema(ds.get("configuration"))
        if config_schema == schema:
            return _to_int(ds.get("id"), "datasource.id")

    for ds in candidates:
        name = ds.get("name")
        if isinstance(name, str) and schema in name:
            return _to_int(ds.get("id"), "datasource.id")

    if len(candidates) == 1:
        return _to_int(candidates[0].get("id"), "datasource.id")

    raise RuntimeError(
        f"cannot resolve datasource for schema={schema!r}; pass --datasource-id explicitly"
    )


async def _start_chat(
    client: httpx.AsyncClient,
    token_header: dict[str, str],
    datasource_id: int,
) -> int:
    response = await client.post(
        "/api/v1/chat/start",
        headers=token_header,
        json={"datasource": datasource_id, "origin": 0},
    )
    response.raise_for_status()
    payload = _expect_dict(_unwrap_payload(response.json()), "chat start response")
    return _to_int(payload.get("id"), "chat.id")


async def _get_chat_records(
    client: httpx.AsyncClient,
    token_header: dict[str, str],
    chat_id: int,
) -> list[dict[str, object]]:
    response = await client.get(
        f"/api/v1/chat/{chat_id}/with_data", headers=token_header
    )
    response.raise_for_status()
    payload = _expect_dict(_unwrap_payload(response.json()), "chat detail response")
    raw_records = _expect_list(payload.get("records"), "chat records")
    records: list[dict[str, object]] = []
    for record in raw_records:
        if isinstance(record, dict):
            records.append(cast(dict[str, object], record))
    return records


def _extract_sql_like_fragments(events: list[dict[str, object]]) -> list[str]:
    fragments: list[str] = []
    for event in events:
        sql_value = event.get("sql")
        if isinstance(sql_value, str) and sql_value.strip():
            fragments.append(sql_value.strip())
            continue

        content = event.get("content")
        if isinstance(content, str) and re.search(
            r"\bselect\b", content, re.IGNORECASE
        ):
            fragments.append(content.strip())
    return fragments


async def _ask_question_sse(
    client: httpx.AsyncClient,
    token_header: dict[str, str],
    chat_id: int,
    question: str,
) -> dict[str, object]:
    events: list[dict[str, object]] = []

    async with client.stream(
        "POST",
        "/api/v1/chat/question",
        headers=token_header,
        json={"chat_id": chat_id, "question": question},
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            try:
                event_obj = json.loads(payload)
            except json.JSONDecodeError:
                events.append({"type": "raw", "content": payload})
                continue
            if isinstance(event_obj, dict):
                events.append(cast(dict[str, object], event_obj))
            else:
                events.append({"type": "raw", "content": event_obj})

    event_types: list[str] = []
    for event in events:
        event_type = event.get("type")
        if isinstance(event_type, str):
            event_types.append(event_type)

    error_messages: list[str] = []
    for event in events:
        event_type = event.get("type")
        content = event.get("content")
        if event_type == "error":
            error_messages.append(str(content))

    return {
        "events": events,
        "event_types": sorted(set(event_types)),
        "event_count": len(events),
        "errors": error_messages,
        "sql_fragments": _extract_sql_like_fragments(events),
    }


def _truncate(value: str, limit: int = 280) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


async def _run(args: argparse.Namespace) -> int:
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"), timeout=timeout
    ) as client:
        token = await _login_token(client, args.username, args.password, args.token)
        token_header = {"X-SQLBOT-TOKEN": f"Bearer {token}"}

        datasource_id = await _resolve_datasource_id(
            client, token_header, args.schema, args.datasource_id
        )
        chat_id = await _start_chat(client, token_header, datasource_id)

        case_results: list[dict[str, object]] = []

        for case in PROMPT_CASES:
            records_before = await _get_chat_records(client, token_header, chat_id)
            sse_result = await _ask_question_sse(
                client, token_header, chat_id, case.question
            )
            records_after = await _get_chat_records(client, token_header, chat_id)

            latest_record = records_after[-1] if records_after else {}
            latest_sql = (
                latest_record.get("sql") if isinstance(latest_record, dict) else None
            )
            latest_data = (
                latest_record.get("data") if isinstance(latest_record, dict) else None
            )

            has_error = bool(sse_result["errors"])
            new_record_count = max(0, len(records_after) - len(records_before))
            has_sql = isinstance(latest_sql, str) and latest_sql.strip() != ""
            has_data = isinstance(latest_data, str) and latest_data.strip() != ""
            passed = (not has_error) and new_record_count > 0 and has_sql

            case_results.append(
                {
                    "case_id": case.case_id,
                    "question": case.question,
                    "expectation": case.expectation,
                    "passed": passed,
                    "new_record_count": new_record_count,
                    "has_sql": has_sql,
                    "has_data": has_data,
                    "event_count": sse_result["event_count"],
                    "event_types": sse_result["event_types"],
                    "errors": sse_result["errors"],
                    "sample_sql": _truncate(latest_sql)
                    if isinstance(latest_sql, str)
                    else None,
                    "sample_data": _truncate(latest_data)
                    if isinstance(latest_data, str)
                    else None,
                    "sse_sql_fragments": sse_result["sql_fragments"],
                }
            )

    overall_passed = all(bool(case["passed"]) for case in case_results)
    report = {
        "report_id": f"g4-happy-path-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now().isoformat(),
        "base_url": args.base_url,
        "schema": args.schema,
        "datasource_id": datasource_id,
        "chat_id": chat_id,
        "overall_passed": overall_passed,
        "cases": case_results,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    status_text = "PASS" if overall_passed else "FAIL"
    print(
        f"[G4 {status_text}] schema={args.schema} datasource_id={datasource_id} chat_id={chat_id}"
    )
    print(f"evidence: {output_path}")

    return 0 if overall_passed else 1


def main() -> None:
    args = _parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
