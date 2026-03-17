import json
from typing import Any, cast

import pytest
from _pytest.monkeypatch import MonkeyPatch
from sqlmodel import Session

import apps.chat.task.llm as llm_module
from apps.chat.models.chat_model import ChatLog
from apps.chat.models.chat_model import OperationEnum
from apps.chat.task.llm import LLMService
from apps.chat.task.llm import _is_llm_quota_error
from apps.chat.task.llm import _normalize_llm_stream_error
from apps.datasource.models.datasource import CoreDatasource
from common.error import SingleMessageError


def _noop_trigger_log_error(session: object, log: object) -> None:
    _ = session
    _ = log


def _accept_select_1(sql: str, ds: object) -> bool:
    _ = ds
    return sql == "SELECT 1"


def _accept_all_read_only(sql: str, ds: object) -> bool:
    _ = sql
    _ = ds
    return True


def _reject_all_read_only(sql: str, ds: object) -> bool:
    _ = sql
    _ = ds
    return False


def _fake_datasource() -> CoreDatasource:
    return cast(CoreDatasource, object())


def build_llm_service() -> LLMService:
    service = object.__new__(LLMService)
    service.current_logs = {OperationEnum.GENERATE_SQL: cast(ChatLog, object())}
    return service


class _BoomingLlm:
    def stream(self, messages: object) -> object:
        _ = messages

        def _gen() -> object:
            raise Exception(
                "Error code: 403 - {'error': {'message': 'not enough quota', 'code': '20031'}}"
            )
            yield None

        return _gen()


class TestLlmSqlAnswerParsing:
    def test_detects_llm_quota_error_from_provider_message(self) -> None:
        exc = Exception(
            "Error code: 403 - {'error': {'message': 'not enough quota', 'code': '20031'}}"
        )

        assert _is_llm_quota_error(exc) is True

    def test_normalize_llm_quota_error_returns_single_message_error(self) -> None:
        exc = Exception(
            "Error code: 403 - {'error': {'message': 'not enough quota', 'code': '20031'}}"
        )

        normalized = _normalize_llm_stream_error(exc)

        assert isinstance(normalized, SingleMessageError)
        assert "llm-quota-err" in str(normalized)

    def test_normalize_llm_quota_error_sanitizes_provider_details(self) -> None:
        exc = Exception(
            "Error code: 403 - {'error': {'message': 'not enough quota', 'code': '20031'}}"
        )

        normalized = _normalize_llm_stream_error(exc)
        payload = json.loads(str(normalized))

        assert payload == {
            "message": "模型服务额度不足，请检查模型供应商余额/配额后重试",
            "type": "llm-quota-err",
            "retryable": False,
        }
        assert "not enough quota" not in str(normalized)
        assert "20031" not in str(normalized)

    def test_iter_llm_stream_wraps_quota_error_as_single_message_error(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        service = build_llm_service()
        setattr(service, "llm", _BoomingLlm())
        triggered: list[bool] = []

        def _track_trigger(session: object, log: object) -> None:
            _ = session
            _ = log
            triggered.append(True)

        monkeypatch.setattr(llm_module, "trigger_log_error", _track_trigger)

        with pytest.raises(SingleMessageError, match="llm-quota-err"):
            list(
                service._iter_llm_stream(
                    cast(Session, object()),
                    [],
                    {},
                    OperationEnum.GENERATE_SQL,
                )
            )

        assert triggered == [True]

    def test_get_chart_type_accepts_success_string_payload(self) -> None:
        result = LLMService.get_chart_type_from_sql_answer(
            '{"success":"true","sql":"SELECT 1","chart-type":"table"}'
        )

        assert result == "table"

    def test_get_brief_accepts_payload_without_success_field(self) -> None:
        result = LLMService.get_brief_from_sql_answer(
            '{"sql":"SELECT 1","brief":"项目经营概览"}'
        )

        assert result == "项目经营概览"

    def test_get_chart_type_ignores_failed_payload(self) -> None:
        result = LLMService.get_chart_type_from_sql_answer(
            '{"success":false,"message":"cannot generate sql","chart-type":"table"}'
        )

        assert result is None

    def test_get_brief_ignores_blank_sql_without_success(self) -> None:
        result = LLMService.get_brief_from_sql_answer(
            '{"sql":"   ","brief":"项目经营概览"}'
        )

        assert result is None

    def test_get_chart_type_ignores_message_and_sql_without_success(self) -> None:
        result = LLMService.get_chart_type_from_sql_answer(
            '{"message":"cannot generate sql","sql":"SELECT 1","chart-type":"table"}'
        )

        assert result is None

    def test_get_brief_ignores_unrecognized_success_value(self) -> None:
        result = LLMService.get_brief_from_sql_answer(
            '{"success":"ok","sql":"SELECT 1","brief":"项目经营概览"}'
        )

        assert result is None

    def test_check_sql_accepts_missing_success_with_sql_only(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        service = build_llm_service()

        sql, tables = service.check_sql(
            session=cast(Session, object()),
            res='{"sql":"SELECT 1","tables":["demo_table"]}',
            operate=OperationEnum.GENERATE_SQL,
        )

        assert sql == "SELECT 1"
        assert tables == ["demo_table"]

    def test_check_sql_rejects_message_and_sql_without_success(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        service = build_llm_service()

        with pytest.raises(SingleMessageError, match="cannot generate sql"):
            _ = service.check_sql(
                session=cast(Session, object()),
                res='{"message":"cannot generate sql","sql":"SELECT 1"}',
                operate=OperationEnum.GENERATE_SQL,
            )

    def test_check_sql_rejects_unrecognized_success_value(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        service = build_llm_service()

        with pytest.raises(SingleMessageError, match="Cannot parse sql from answer"):
            _ = service.check_sql(
                session=cast(Session, object()),
                res='{"success":"ok","sql":"SELECT 1"}',
                operate=OperationEnum.GENERATE_SQL,
            )

    def test_get_chart_type_prefers_last_sql_payload(self) -> None:
        result = LLMService.get_chart_type_from_sql_answer(
            '{"success":false,"message":"first payload"}\n'
            + '{"success":true,"sql":"SELECT 1","chart-type":"table"}'
        )

        assert result == "table"

    def test_get_brief_prefers_last_sql_payload(self) -> None:
        result = LLMService.get_brief_from_sql_answer(
            '{"success":true,"sql":"SELECT 0","brief":"旧标题"}\n'
            + '{"success":true,"sql":"SELECT 1","brief":"项目经营摘要"}'
        )

        assert result == "项目经营摘要"

    def test_check_sql_prefers_last_sql_payload(self, monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        service = build_llm_service()

        sql, tables = service.check_sql(
            session=cast(Session, object()),
            res='{"success":false,"message":"first payload"}\n'
            + '{"success":true,"sql":"SELECT 1","tables":["demo_table"]}',
            operate=OperationEnum.GENERATE_SQL,
        )

        assert sql == "SELECT 1"
        assert tables == ["demo_table"]

    def test_check_sql_accepts_plain_sql_fallback(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        monkeypatch.setattr(llm_module, "check_sql_read", _accept_select_1)
        service = build_llm_service()
        service.ds = _fake_datasource()

        sql, tables = service.check_sql(
            session=cast(Session, object()),
            res="SELECT 1",
            operate=OperationEnum.GENERATE_SQL,
        )

        assert sql == "SELECT 1"
        assert tables is None

    def test_check_sql_accepts_sql_code_fence_fallback(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        monkeypatch.setattr(llm_module, "check_sql_read", _accept_select_1)
        service = build_llm_service()
        service.ds = _fake_datasource()

        sql, tables = service.check_sql(
            session=cast(Session, object()),
            res="```sql\nSELECT 1\n```",
            operate=OperationEnum.GENERATE_SQL,
        )

        assert sql == "SELECT 1"
        assert tables is None

    def test_check_sql_rejects_prose_wrapped_plain_sql(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        monkeypatch.setattr(llm_module, "check_sql_read", _accept_all_read_only)
        service = build_llm_service()
        service.ds = _fake_datasource()

        with pytest.raises(
            SingleMessageError, match="SQL answer is not a valid json object"
        ):
            _ = service.check_sql(
                session=cast(Session, object()),
                res="下面是 SQL:\nSELECT 1",
                operate=OperationEnum.GENERATE_SQL,
            )

    def test_check_sql_rejects_prose_wrapped_sql_code_fence(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        monkeypatch.setattr(llm_module, "check_sql_read", _accept_all_read_only)
        service = build_llm_service()
        service.ds = _fake_datasource()

        with pytest.raises(
            SingleMessageError, match="SQL answer is not a valid json object"
        ):
            _ = service.check_sql(
                session=cast(Session, object()),
                res="这是结果：\n```sql\nSELECT 1\n```",
                operate=OperationEnum.GENERATE_SQL,
            )

    def test_check_sql_rejects_non_read_only_sql_fallback(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        monkeypatch.setattr(llm_module, "check_sql_read", _reject_all_read_only)
        service = build_llm_service()
        service.ds = _fake_datasource()

        with pytest.raises(
            SingleMessageError, match="SQL answer is not a valid json object"
        ):
            _ = service.check_sql(
                session=cast(Session, object()),
                res="DELETE FROM demo_table",
                operate=OperationEnum.GENERATE_SQL,
            )

    def test_check_sql_rejects_multiple_statements_sql_fallback(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(llm_module, "trigger_log_error", _noop_trigger_log_error)
        monkeypatch.setattr(llm_module, "check_sql_read", _accept_all_read_only)
        service = build_llm_service()
        service.ds = _fake_datasource()

        with pytest.raises(
            SingleMessageError, match="SQL answer is not a valid json object"
        ):
            _ = service.check_sql(
                session=cast(Session, object()),
                res="SELECT 1; SELECT 2",
                operate=OperationEnum.GENERATE_SQL,
            )
