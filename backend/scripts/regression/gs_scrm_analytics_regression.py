#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

from scripts.regression.g4_happy_path_demo_sales import (
    _ask_question_with_retry,
    _get_chat_records,
    _has_meaningful_data,
    _login_token,
    _resolve_datasource_id,
    _serialize_sample_data,
    _start_chat,
    _truncate,
)


@dataclass(frozen=True)
class PromptCase:
    case_id: str
    question: str
    expectation: str


@dataclass(frozen=True)
class CompareCase:
    case_id: str
    original_question: str
    recommended_question: str
    expectation: str


STANDARD_CASES: tuple[PromptCase, ...] = (
    PromptCase(
        "member-growth-daily",
        "请基于 em_member_statisticals 表，查询最近30天每日新增会员人数(member_increase)，返回 date 和 member_increase。",
        "Daily member growth should read em_member_statisticals.date and member_increase directly.",
    ),
    PromptCase(
        "member-active-trend",
        "请统计最近30天活跃会员人数的变化趋势。",
        "Active member trend should return grouped rows by day.",
    ),
    PromptCase(
        "activity-applies",
        "请统计各会员活动的报名人数，并按报名人数从高到低排序。",
        "Activity apply counts should return grouped rows.",
    ),
    PromptCase(
        "marketing-effect-v2",
        "请基于营销计划日志统计各营销计划的触发次数、触发金额和发放积分，并显示营销计划名称。",
        "Marketing effect should join marketing plan logs and plan names.",
    ),
    PromptCase(
        "shop-consume-aov-30d",
        "请基于销售流水表按店铺统计消费总金额、消费笔数和客单价。",
        "Shop AOV should use trades + writeoff joins and return amount/member/aov by store.",
    ),
    PromptCase(
        "member-points-source",
        "请基于会员积分日志统计不同积分来源(source_type)的积分发放次数和累计积分。",
        "Points source analysis should group by source_type from member integral logs.",
    ),
    PromptCase(
        "member-profile-gender-age",
        "请基于 em_members 统计会员画像：按性别和年龄段分布会员人数（年龄基于 birthday 计算，birthday 为空归为未知）。",
        "Member profile chart should include gender and age-group distribution using birthday.",
    ),
    PromptCase(
        "member-visit-frequency",
        "请基于会员活跃记录统计最近30天到店最频繁的会员，显示会员ID和到店天数。",
        "Visit frequency chart should rank members by active-day counts from em_member_actives.",
    ),
)


ADVANCED_CASES: tuple[PromptCase, ...] = (
    PromptCase(
        "adv-grade-consume",
        "请结合会员表和交易表，统计不同会员等级的消费总额、消费人数和客单价，并按消费总额从高到低排序。",
        "Grade-level consumption summary should join members, trades, and grades.",
    ),
    PromptCase(
        "adv-new-member-channel-source",
        "请基于 em_members 表的 source 字段，统计最近30天新增会员中各注册渠道的人数分布，并按人数从高到低排序。",
        "Recent new-member channel distribution should use em_members.source.",
    ),
    PromptCase(
        "adv-activity-consume-members",
        "请基于活动报名表和交易表，统计参与活动且发生过消费的会员人数。",
        "Activity participants with purchases should return a non-empty aggregate.",
    ),
    PromptCase(
        "adv-grade57-vs13-fixed",
        "请基于 em_members.grade_id 和 em_trades.member_id，比较 grade_id 为 5、6、7 的会员与 grade_id 为 1、2、3 的会员在交易表中的消费总额和消费人数。",
        "High-grade versus normal-member comparison should return grouped totals.",
    ),
    PromptCase(
        "adv-marketing-shop",
        "请基于营销计划日志统计各店铺触发营销计划的次数和触发金额，并显示店铺名称。",
        "Marketing-by-shop summary should join market plan logs and shops.",
    ),
    PromptCase(
        "adv-member-points-ranking",
        "请基于会员积分日志统计积分获取最多的会员TOP10，显示会员ID和累计积分。",
        "Points ranking should aggregate add-type integral logs by member.",
    ),
)


COMPARE_CASES: tuple[CompareCase, ...] = ()


def _parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[3]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    default_output = (
        repo_root
        / "docs"
        / "regression"
        / "evidence"
        / f"g4-gs-scrm-analytics-{timestamp}.json"
    )
    parser = argparse.ArgumentParser(
        description="Run gs_scrm analytics regression via API"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default=None)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="mySQLBot@123456")
    parser.add_argument("--schema", default="gs_scrm")
    parser.add_argument("--datasource-id", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--output", default=str(default_output))
    parser.add_argument(
        "--case-id",
        action="append",
        default=None,
        help="Optional case_id filter; repeat to run multiple specific cases",
    )
    parser.add_argument(
        "--profile",
        choices=("standard", "advanced", "compare", "all"),
        default="all",
    )
    parser.add_argument("--case-delay-seconds", type=float, default=2.0)
    parser.add_argument("--rate-limit-retries", type=int, default=2)
    parser.add_argument("--rate-limit-backoff-seconds", type=float, default=5.0)
    return parser.parse_args()


def _filter_prompt_cases(
    cases: tuple[PromptCase, ...], case_ids: list[str] | None
) -> tuple[PromptCase, ...]:
    if not case_ids:
        return cases
    selected_ids = {case_id.strip() for case_id in case_ids if case_id.strip() != ""}
    return tuple(case for case in cases if case.case_id in selected_ids)


def _filter_compare_cases(
    cases: tuple[CompareCase, ...], case_ids: list[str] | None
) -> tuple[CompareCase, ...]:
    if not case_ids:
        return cases
    selected_ids = {case_id.strip() for case_id in case_ids if case_id.strip() != ""}
    return tuple(case for case in cases if case.case_id in selected_ids)


def _nested_passed(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(value.get("passed"))


async def _run_prompt_case(
    client: httpx.AsyncClient,
    token_header: dict[str, str],
    datasource_id: int,
    case: PromptCase,
    *,
    retries: int,
    backoff_seconds: float,
) -> dict[str, object]:
    chat_id = await _start_chat(client, token_header, datasource_id)
    result = await _ask_question_with_retry(
        client,
        token_header,
        chat_id,
        case.question,
        retries=retries,
        backoff_seconds=backoff_seconds,
    )
    records = await _get_chat_records(client, token_header, chat_id)
    latest_record = records[-1] if records else {}
    latest_sql = latest_record.get("sql") if isinstance(latest_record, dict) else None
    latest_data = latest_record.get("data") if isinstance(latest_record, dict) else None
    serialized_data = _serialize_sample_data(latest_data)
    has_sql = isinstance(latest_sql, str) and latest_sql.strip() != ""
    has_data = _has_meaningful_data(latest_data)
    passed = (not result["errors"]) and has_sql and has_data and len(records) > 0
    return {
        "case_id": case.case_id,
        "question": case.question,
        "expectation": case.expectation,
        "passed": passed,
        "chat_id": chat_id,
        "record_count": len(records),
        "has_sql": has_sql,
        "has_data": has_data,
        "event_count": result["event_count"],
        "event_types": result["event_types"],
        "errors": result["errors"],
        "sample_sql": _truncate(latest_sql) if isinstance(latest_sql, str) else None,
        "sample_data": _truncate(serialized_data)
        if isinstance(serialized_data, str)
        else None,
        "sse_sql_fragments": result["sql_fragments"],
    }


async def _run_prompt_group(
    client: httpx.AsyncClient,
    token_header: dict[str, str],
    datasource_id: int,
    cases: tuple[PromptCase, ...],
    *,
    delay_seconds: float,
    retries: int,
    backoff_seconds: float,
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for index, case in enumerate(cases):
        if index > 0 and delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        results.append(
            await _run_prompt_case(
                client,
                token_header,
                datasource_id,
                case,
                retries=retries,
                backoff_seconds=backoff_seconds,
            )
        )
    return {
        "case_count": len(cases),
        "passed_count": sum(1 for item in results if bool(item["passed"])),
        "overall_passed": all(bool(item["passed"]) for item in results),
        "cases": results,
    }


async def _run_compare_group(
    client: httpx.AsyncClient,
    token_header: dict[str, str],
    datasource_id: int,
    cases: tuple[CompareCase, ...],
    *,
    delay_seconds: float,
    retries: int,
    backoff_seconds: float,
) -> dict[str, object]:
    compare_results: list[dict[str, object]] = []
    for index, case in enumerate(cases):
        if index > 0 and delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        original_result = await _run_prompt_case(
            client,
            token_header,
            datasource_id,
            PromptCase(
                f"{case.case_id}-original",
                case.original_question,
                case.expectation,
            ),
            retries=retries,
            backoff_seconds=backoff_seconds,
        )
        if delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
        recommended_result = await _run_prompt_case(
            client,
            token_header,
            datasource_id,
            PromptCase(
                f"{case.case_id}-recommended",
                case.recommended_question,
                case.expectation,
            ),
            retries=retries,
            backoff_seconds=backoff_seconds,
        )
        compare_results.append(
            {
                "case_id": case.case_id,
                "expectation": case.expectation,
                "original": original_result,
                "recommended": recommended_result,
                "improved": (not _nested_passed(original_result))
                and _nested_passed(recommended_result),
            }
        )
    return {
        "case_count": len(cases),
        "improved_count": sum(1 for item in compare_results if bool(item["improved"])),
        "recommended_passed_count": sum(
            1 for item in compare_results if _nested_passed(item.get("recommended"))
        ),
        "overall_recommended_passed": all(
            _nested_passed(item.get("recommended")) for item in compare_results
        ),
        "cases": compare_results,
    }


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

        report: dict[str, object] = {
            "report_id": f"g4-gs-scrm-analytics-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "base_url": args.base_url,
            "schema": args.schema,
            "datasource_id": datasource_id,
            "profile": args.profile,
            "selected_case_ids": args.case_id,
        }

        selected_standard_cases = _filter_prompt_cases(STANDARD_CASES, args.case_id)
        selected_advanced_cases = _filter_prompt_cases(ADVANCED_CASES, args.case_id)
        selected_compare_cases = _filter_compare_cases(COMPARE_CASES, args.case_id)

        if args.profile in ("standard", "all"):
            report["standard"] = await _run_prompt_group(
                client,
                token_header,
                datasource_id,
                selected_standard_cases,
                delay_seconds=args.case_delay_seconds,
                retries=args.rate_limit_retries,
                backoff_seconds=args.rate_limit_backoff_seconds,
            )

        if args.profile in ("advanced", "all"):
            report["advanced"] = await _run_prompt_group(
                client,
                token_header,
                datasource_id,
                selected_advanced_cases,
                delay_seconds=args.case_delay_seconds,
                retries=args.rate_limit_retries,
                backoff_seconds=args.rate_limit_backoff_seconds,
            )

        if args.profile in ("compare", "all"):
            report["compare"] = await _run_compare_group(
                client,
                token_header,
                datasource_id,
                selected_compare_cases,
                delay_seconds=args.case_delay_seconds,
                retries=args.rate_limit_retries,
                backoff_seconds=args.rate_limit_backoff_seconds,
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    overall_sections: list[bool] = []
    for key in ("standard", "advanced"):
        section = report.get(key)
        if isinstance(section, dict) and "overall_passed" in section:
            overall_sections.append(bool(section["overall_passed"]))
    compare_section = report.get("compare")
    if (
        isinstance(compare_section, dict)
        and "overall_recommended_passed" in compare_section
    ):
        overall_sections.append(bool(compare_section["overall_recommended_passed"]))
    overall_passed = all(overall_sections) if overall_sections else False

    status_text = "PASS" if overall_passed else "FAIL"
    print(f"[G4 {status_text}] schema={args.schema} datasource_id={datasource_id}")
    print(f"evidence: {output_path}")
    return 0 if overall_passed else 1


def main() -> None:
    raise SystemExit(asyncio.run(_run(_parse_args())))


if __name__ == "__main__":
    main()
