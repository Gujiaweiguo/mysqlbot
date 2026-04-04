from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from langchain_core.messages import AIMessageChunk, BaseMessage

from apps.ai_model.model_factory import BaseLLM, LLMConfig

if TYPE_CHECKING:
    from langchain.chat_models.base import BaseChatModel
else:
    BaseChatModel = Any

CI_DETERMINISTIC_MODEL_TYPE = "ci_deterministic"


@dataclass(frozen=True)
class DeterministicSQLCase:
    match_text: str
    sql: str
    tables: tuple[str, ...]
    brief: str
    chart_title: str
    chart_columns: tuple[tuple[str, str], ...]


DEMO_SALES_SQL_CASES: tuple[DeterministicSQLCase, ...] = (
    DeterministicSQLCase(
        match_text="最近订单总金额是多少",
        sql='SELECT SUM("t1"."order_amount") AS "total_amount" FROM "demo_sales"."orders" "t1" LIMIT 1000',
        tables=("orders",),
        brief="订单总金额",
        chart_title="订单总金额",
        chart_columns=(("总金额", "total_amount"),),
    ),
    DeterministicSQLCase(
        match_text="每个客户的订单金额汇总，按金额降序",
        sql='SELECT "t2"."customer_name" AS "customer_name", SUM("t1"."order_amount") AS "total_amount" FROM "demo_sales"."orders" "t1" JOIN "demo_sales"."customers" "t2" ON "t1"."customer_id" = "t2"."customer_id" GROUP BY "t2"."customer_name" ORDER BY "total_amount" DESC LIMIT 1000',
        tables=("orders", "customers"),
        brief="客户订单金额汇总",
        chart_title="客户订单金额汇总",
        chart_columns=(("客户", "customer_name"), ("金额汇总", "total_amount")),
    ),
    DeterministicSQLCase(
        match_text="订单状态分别有多少条",
        sql='SELECT "t1"."order_status" AS "order_status", COUNT("t1"."order_id") AS "order_count" FROM "demo_sales"."orders" "t1" GROUP BY "t1"."order_status" ORDER BY "order_count" DESC LIMIT 1000',
        tables=("orders",),
        brief="订单状态分布",
        chart_title="订单状态分布",
        chart_columns=(("订单状态", "order_status"), ("数量", "order_count")),
    ),
)


def _message_texts(messages: Sequence[BaseMessage]) -> list[str]:
    return [str(getattr(message, "content", "") or "") for message in messages]


def _extract_question(messages: Sequence[BaseMessage]) -> str:
    for content in reversed(_message_texts(messages)):
        for case in DEMO_SALES_SQL_CASES:
            if case.match_text in content:
                return case.match_text
    joined = "\n".join(_message_texts(messages))
    return joined


def _match_case(question_text: str) -> DeterministicSQLCase | None:
    for case in DEMO_SALES_SQL_CASES:
        if (
            case.match_text in question_text
            or case.sql in question_text
            or case.brief in question_text
            or case.chart_title in question_text
        ):
            return case
    return None


def _is_chart_stage(messages: Sequence[BaseMessage]) -> bool:
    return any("<chart-type>" in content for content in _message_texts(messages))


def _build_sql_payload(case: DeterministicSQLCase | None) -> str:
    if case is None:
        return json.dumps(
            {
                "success": False,
                "message": "抱歉，当前 CI 确定性模型未覆盖该 demo_sales 用例。",
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "success": True,
            "sql": case.sql,
            "tables": list(case.tables),
            "chart-type": "table",
            "brief": case.brief,
        },
        ensure_ascii=False,
    )


def _build_chart_payload(case: DeterministicSQLCase | None) -> str:
    columns = [
        {"name": name, "value": value}
        for name, value in (
            case.chart_columns if case is not None else (("结果", "result"),)
        )
    ]
    title = case.chart_title if case is not None else "查询结果"
    return json.dumps(
        {
            "type": "table",
            "title": title,
            "columns": columns,
        },
        ensure_ascii=False,
    )


def build_deterministic_response(messages: Sequence[BaseMessage]) -> str:
    question_text = _extract_question(messages)
    case = _match_case(question_text)
    if _is_chart_stage(messages):
        return _build_chart_payload(case)
    return _build_sql_payload(case)


class DeterministicCIChatModel:
    def stream(self, messages: Sequence[BaseMessage]) -> Iterator[AIMessageChunk]:
        yield AIMessageChunk(content=build_deterministic_response(messages))


class DeterministicCILLM(BaseLLM):
    def _init_llm(self) -> BaseChatModel:
        _ = self.config
        return cast(BaseChatModel, cast(object, DeterministicCIChatModel()))


def build_ci_deterministic_config(config: LLMConfig) -> LLMConfig:
    return LLMConfig(
        model_id=config.model_id,
        model_type=CI_DETERMINISTIC_MODEL_TYPE,
        model_name=config.model_name,
        api_key=config.api_key,
        api_base_url=config.api_base_url,
        additional_params=dict(config.additional_params),
    )


def llm_class() -> type[BaseLLM]:
    return cast(type[BaseLLM], DeterministicCILLM)
