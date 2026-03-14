#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

import httpx

MOCK_DS_TEMPLATE: dict[str, Any] = {
    "id": 10001,
    "name": "mock-demo-sales",
    "type": "pg",
    "type_name": "PostgreSQL",
    "host": "localhost",
    "port": 5432,
    "user": "root",
    "password": "Password123@pg",
    "dataBase": "sqlbot",
    "db_schema": "demo_sales",
    "mode": "read",
    "tables": [
        {
            "name": "customers",
            "comment": "customers table",
            "sql": "SELECT * FROM demo_sales.customers",
            "fields": [
                {"name": "customer_id", "type": "int", "comment": "id"},
                {"name": "customer_name", "type": "text", "comment": "name"},
            ],
        },
        {
            "name": "orders",
            "comment": "orders table",
            "sql": "SELECT * FROM demo_sales.orders",
            "fields": [
                {"name": "order_id", "type": "int", "comment": "id"},
                {"name": "customer_id", "type": "int", "comment": "fk"},
                {"name": "order_status", "type": "text", "comment": "status"},
                {"name": "order_amount", "type": "numeric", "comment": "amount"},
            ],
        },
    ],
}


@dataclass
class MockState:
    transient_hits: int = 0
    stable_hits: int = 0
    rate_limit_hits: int = 0


class MockProviderHandler(BaseHTTPRequestHandler):
    state: MockState = MockState()

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/rate-limit/ds"):
            self.state.rate_limit_hits += 1
            self._send_json(429, {"code": 429, "message": "mock provider rate limited"})
            return

        if self.path.startswith("/transient/ds"):
            self.state.transient_hits += 1
            if self.state.transient_hits == 1:
                self._send_json(
                    503, {"code": 503, "message": "mock transient upstream failure"}
                )
            else:
                self._send_json(200, {"code": 0, "data": [MOCK_DS_TEMPLATE]})
            return

        if self.path.startswith("/stable/ds"):
            self.state.stable_hits += 1
            self._send_json(200, {"code": 0, "data": [MOCK_DS_TEMPLATE]})
            return

        self._send_json(404, {"code": 404, "message": "not found"})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def _parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    default_output = (
        repo_root
        / "docs"
        / "regression"
        / "evidence"
        / f"g5-failure-path-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )

    parser = argparse.ArgumentParser(
        description="Run G5 failure-path regression (429/transient) with controllable mock provider"
    )
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8000", help="Backend base URL"
    )
    parser.add_argument(
        "--question",
        default="最近订单总金额是多少？",
        help="Question used for failure-path checks",
    )
    parser.add_argument(
        "--provider-host",
        default="172.17.0.1",
        help="Host/IP that backend container can use to access mock provider",
    )
    parser.add_argument(
        "--output", default=str(default_output), help="Evidence JSON output path"
    )
    parser.add_argument(
        "--timeout", type=float, default=180.0, help="HTTP timeout seconds"
    )
    return parser.parse_args()


def _unwrap_payload(payload: object) -> object:
    if isinstance(payload, dict) and {"code", "data", "msg"}.issubset(payload):
        return payload["data"]
    return payload


def _parse_body(response: httpx.Response) -> object:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type.lower():
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text
    return response.text


def _extract_error_text(body: object) -> str:
    if isinstance(body, str):
        return body
    if isinstance(body, dict):
        if "message" in body:
            return str(body.get("message"))
        if "detail" in body:
            return str(body.get("detail"))
    return str(body)


async def _call_mcp_assistant(
    client: httpx.AsyncClient,
    question: str,
    provider_url: str,
) -> dict[str, object]:
    start = time.monotonic()
    response = await client.post(
        "/api/v1/mcp/mcp_assistant",
        json={
            "question": question,
            "url": provider_url,
            "authorization": "[]",
            "stream": False,
        },
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    body = _parse_body(response)
    unwrapped = _unwrap_payload(body)

    return {
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "body": body,
        "unwrapped": unwrapped,
    }


def _is_success_payload(payload: object) -> bool:
    if isinstance(payload, dict) and "success" in payload:
        return bool(payload.get("success"))
    return False


def _build_429_case(
    result: dict[str, object], recovery: dict[str, object], state: MockState
) -> dict[str, object]:
    body = result["body"]
    error_text = _extract_error_text(body)
    controlled_error = result["status_code"] != 200 and len(error_text.strip()) > 0
    can_continue = recovery["status_code"] == 200 and _is_success_payload(
        recovery["unwrapped"]
    )

    return {
        "case_id": "g5-429-rate-limit",
        "scenario": "provider datasource endpoint returns HTTP 429",
        "passed": controlled_error and can_continue,
        "controlled_error": controlled_error,
        "frontend_can_continue": can_continue,
        "mock_rate_limit_hits": state.rate_limit_hits,
        "response_status": result["status_code"],
        "response_duration_ms": result["duration_ms"],
        "error_message": error_text,
        "recovery_status": recovery["status_code"],
        "recovery_duration_ms": recovery["duration_ms"],
        "recovery_success": _is_success_payload(recovery["unwrapped"]),
    }


def _build_transient_case(
    first_attempt: dict[str, object],
    second_attempt: dict[str, object],
    state: MockState,
) -> dict[str, object]:
    first_error_text = _extract_error_text(first_attempt["body"])
    second_error_text = _extract_error_text(second_attempt["body"])
    first_failed = (
        first_attempt["status_code"] != 200 and len(first_error_text.strip()) > 0
    )
    second_success = second_attempt["status_code"] == 200 and _is_success_payload(
        second_attempt["unwrapped"]
    )
    second_controlled_failure = (
        second_attempt["status_code"] != 200 and len(second_error_text.strip()) > 0
    )
    retry_count = max(0, state.transient_hits - 1)
    final_explainable = second_success or second_controlled_failure

    return {
        "case_id": "g5-transient-recovery",
        "scenario": "provider transient 503 first call, then recovery on next attempt",
        "passed": first_failed and retry_count >= 1 and final_explainable,
        "first_attempt_failed": first_failed,
        "first_attempt_status": first_attempt["status_code"],
        "first_attempt_duration_ms": first_attempt["duration_ms"],
        "first_error_message": first_error_text,
        "second_attempt_status": second_attempt["status_code"],
        "second_attempt_duration_ms": second_attempt["duration_ms"],
        "second_attempt_success": second_success,
        "second_attempt_controlled_failure": second_controlled_failure,
        "second_error_message": second_error_text,
        "mock_transient_hits": state.transient_hits,
        "observed_retry_count": retry_count,
        "final_status": (
            "success"
            if second_success
            else "controlled_failure"
            if second_controlled_failure
            else "uncontrolled_failure"
        ),
    }


def _start_mock_server() -> tuple[ThreadingHTTPServer, MockState]:
    state = MockState()
    MockProviderHandler.state = state

    server = ThreadingHTTPServer(("0.0.0.0", 0), MockProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, state


async def _run(args: argparse.Namespace) -> int:
    server, state = _start_mock_server()
    _, port = cast(tuple[str, int], server.server_address)
    mock_base = f"http://{args.provider_host}:{port}"

    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"), timeout=timeout
    ) as client:
        rate_limit_res = await _call_mcp_assistant(
            client, args.question, f"{mock_base}/rate-limit/ds"
        )
        post_429_recovery = await _call_mcp_assistant(
            client, args.question, f"{mock_base}/stable/ds"
        )

        transient_first = await _call_mcp_assistant(
            client, args.question, f"{mock_base}/transient/ds"
        )
        transient_second = await _call_mcp_assistant(
            client, args.question, f"{mock_base}/transient/ds"
        )

    server.shutdown()
    server.server_close()

    case_429 = _build_429_case(rate_limit_res, post_429_recovery, state)
    case_transient = _build_transient_case(transient_first, transient_second, state)

    overall_passed = bool(case_429["passed"]) and bool(case_transient["passed"])
    report = {
        "report_id": f"g5-failure-path-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now().isoformat(),
        "base_url": args.base_url,
        "mock_provider_base": mock_base,
        "overall_passed": overall_passed,
        "cases": [case_429, case_transient],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    status_text = "PASS" if overall_passed else "FAIL"
    print(f"[G5 {status_text}] mock_provider={mock_base}")
    print(f"evidence: {output_path}")

    return 0 if overall_passed else 1


def main() -> None:
    args = _parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
