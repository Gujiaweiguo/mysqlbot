import datetime
from collections.abc import Mapping
from typing import Any, Protocol, cast

import orjson
import sqlparse
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.orm import aliased
from sqlmodel import col

from apps.chat.models.chat_model import (
    Chat,
    ChatInfo,
    ChatLog,
    ChatLogHistory,
    ChatLogHistoryItem,
    ChatQuestion,
    ChatRecord,
    ChatRecordResult,
    CreateChat,
    OperationEnum,
    RenameChat,
    TypeEnum,
)
from apps.datasource.crud.datasource import get_ds
from apps.datasource.crud.recommended_problem import get_datasource_recommended_chart
from apps.datasource.models.datasource import CoreDatasource
from apps.db.constant import DB
from apps.db.db import exec_sql
from apps.system.crud.assistant import AssistantOutDs, AssistantOutDsFactory
from apps.system.schemas.system_schema import AssistantOutDsSchema
from common.core.deps import CurrentAssistant, CurrentUser, SessionDep, Trans
from common.utils.data_format import DataFormat
from common.utils.utils import SQLBotLogUtil, extract_nested_json

ObjectDict = dict[str, object]
MessagePayload = dict[str, object]


class ChatRecordRowBase(Protocol):
    id: int
    chat_id: int | None
    create_time: datetime.datetime | None
    finish_time: datetime.datetime | None
    question: str | None
    sql_answer: str | None
    sql: str | None
    datasource: int | None
    chart_answer: str | None
    chart: str | None
    analysis: str | None
    predict: str | None
    datasource_select_answer: str | None
    analysis_record_id: int | None
    predict_record_id: int | None
    regenerate_record_id: int | None
    recommended_question: str | None
    first_chat: bool
    finish: bool
    error: str | None


class ChatRecordRowWithReasoning(ChatRecordRowBase, Protocol):
    sql_reasoning_content: str | None
    chart_reasoning_content: str | None
    analysis_reasoning_content: str | None
    predict_reasoning_content: str | None


class ChatRecordRowWithData(ChatRecordRowBase, Protocol):
    data: str | None
    predict_data: str | None


class ChatLogProtocol(Protocol):
    start_time: datetime.datetime | None
    finish_time: datetime.datetime | None
    token_usage: object | None
    operate: OperationEnum | str | None
    local_operation: bool
    error: bool
    messages: str | None


def _as_object_dict(value: object) -> ObjectDict | None:
    return cast(ObjectDict, value) if isinstance(value, dict) else None


def _as_object_list(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return cast(list[object], value)


def _as_object_dict_list(value: object) -> list[ObjectDict]:
    object_list = _as_object_list(value)
    return [cast(ObjectDict, item) for item in object_list if isinstance(item, dict)]


def _get_str(mapping: Mapping[str, object], key: str) -> str | None:
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _parse_json_object(raw_json: str) -> ObjectDict | None:
    parsed = cast(object, orjson.loads(raw_json))
    return _as_object_dict(parsed)


def _get_total_tokens(token_usage: object | None) -> int:
    if isinstance(token_usage, dict):
        token_usage_dict = cast(dict[str, object], token_usage)
        token_value = token_usage_dict.get("total_tokens")
        if isinstance(token_value, (int, float)):
            return int(token_value)
        return 0
    if isinstance(token_usage, (int, float)):
        return int(token_usage)
    return 0


def _safe_duration(
    start_time: datetime.datetime | None, finish_time: datetime.datetime | None
) -> float | None:
    if start_time and finish_time:
        try:
            time_diff = finish_time - start_time
            return time_diff.total_seconds()
        except Exception:
            return None
    return None


def _safe_rounded_duration(
    start_time: datetime.datetime | None, finish_time: datetime.datetime | None
) -> float | None:
    duration = _safe_duration(start_time, finish_time)
    if duration is None:
        return None
    return round(duration, 2)


def _parse_json_value(raw_json: str | None) -> ObjectDict | list[object] | str | None:
    if not raw_json or raw_json.strip() == "":
        return None
    try:
        parsed = cast(object, orjson.loads(raw_json))
    except Exception:
        return None
    parsed_dict = _as_object_dict(parsed)
    if parsed_dict is not None:
        return parsed_dict
    if isinstance(parsed, list):
        return _as_object_list(cast(object, parsed))
    if isinstance(parsed, str):
        return parsed
    return None


def _get_operate_name(operate: OperationEnum | str | None) -> str | None:
    if operate is None:
        return None
    if isinstance(operate, OperationEnum):
        return operate.name
    for enum_item in OperationEnum:
        if enum_item.value == operate:
            return enum_item.name
    return operate


def _parse_log_message(log: ChatLogProtocol) -> str | ObjectDict | list[object] | None:
    if log.messages is None:
        return None
    if log.operate == OperationEnum.CHOOSE_TABLE:
        return log.messages
    parsed = _parse_json_value(log.messages)
    if isinstance(parsed, (dict, list, str)):
        return parsed
    return log.messages


def _row_to_record_result(
    row: ChatRecordRowBase,
    *,
    duration: float | None,
    total_tokens: int,
    with_data: bool,
) -> ChatRecordResult:
    payload: dict[str, object] = {
        "id": row.id,
        "chat_id": row.chat_id,
        "create_time": row.create_time,
        "finish_time": row.finish_time,
        "duration": duration,
        "total_tokens": total_tokens,
        "question": row.question,
        "sql_answer": row.sql_answer,
        "sql": row.sql,
        "datasource": row.datasource,
        "chart_answer": row.chart_answer,
        "chart": row.chart,
        "analysis": row.analysis,
        "predict": row.predict,
        "datasource_select_answer": row.datasource_select_answer,
        "analysis_record_id": row.analysis_record_id,
        "predict_record_id": row.predict_record_id,
        "regenerate_record_id": row.regenerate_record_id,
        "recommended_question": row.recommended_question,
        "first_chat": row.first_chat,
        "finish": row.finish,
        "error": row.error,
    }
    if with_data:
        row_with_data = cast(ChatRecordRowWithData, row)
        payload["data"] = row_with_data.data
        payload["predict_data"] = row_with_data.predict_data
    else:
        row_with_reasoning = cast(ChatRecordRowWithReasoning, row)
        payload["sql_reasoning_content"] = row_with_reasoning.sql_reasoning_content
        payload["chart_reasoning_content"] = row_with_reasoning.chart_reasoning_content
        payload["analysis_reasoning_content"] = (
            row_with_reasoning.analysis_reasoning_content
        )
        payload["predict_reasoning_content"] = (
            row_with_reasoning.predict_reasoning_content
        )
    return ChatRecordResult.model_validate(payload)


def get_chat_record_by_id(session: SessionDep, record_id: int) -> ChatRecord | None:
    return session.get(ChatRecord, record_id)


def get_chat(session: SessionDep, chat_id: int) -> Chat | None:
    chat = session.get(Chat, chat_id)
    return chat


def list_chats(session: SessionDep, current_user: CurrentUser) -> list[Chat]:
    oid = current_user.oid or 1
    chart_list = list(
        session.scalars(
            select(Chat)
            .where(and_(col(Chat.create_by) == current_user.id, col(Chat.oid) == oid))
            .order_by(col(Chat.create_time).desc())
        ).all()
    )
    return chart_list


def list_recent_questions(
    session: SessionDep, current_user: CurrentUser, datasource_id: int
) -> list[str]:
    chat_records = cast(
        list[object],
        list(
            session.scalars(
                select(col(ChatRecord.question))
                .join(Chat, col(ChatRecord.chat_id) == col(Chat.id))
                .where(
                    col(Chat.datasource) == datasource_id,
                    col(ChatRecord.question).isnot(None),
                    col(ChatRecord.create_by) == current_user.id,
                )
                .group_by(col(ChatRecord.question))
                .order_by(desc(func.max(col(ChatRecord.create_time))))
                .limit(10)
            ).all()
        ),
    )
    return [record for record in chat_records if isinstance(record, str)]


def rename_chat_with_user(
    session: SessionDep, current_user: CurrentUser, rename_object: RenameChat
) -> str:
    chat = session.get(Chat, rename_object.id)
    if not chat:
        raise Exception(f"Chat with id {rename_object.id} not found")
    if chat.create_by != current_user.id:
        raise Exception(
            f"Chat with id {rename_object.id} not Owned by the current user"
        )
    chat.brief = rename_object.brief.strip()[:20]
    chat.brief_generate = rename_object.brief_generate
    session.add(chat)
    session.flush()
    session.refresh(chat)

    brief = chat.brief
    session.commit()
    return brief


def rename_chat(session: SessionDep, rename_object: RenameChat) -> str:
    chat = session.get(Chat, rename_object.id)
    if not chat:
        raise Exception(f"Chat with id {rename_object.id} not found")

    chat.brief = rename_object.brief.strip()[:20]
    chat.brief_generate = rename_object.brief_generate
    session.add(chat)
    session.flush()
    session.refresh(chat)

    brief = chat.brief
    session.commit()
    return brief


def delete_chat(session: SessionDep, chart_id: int) -> str:
    chat = session.get(Chat, chart_id)
    if not chat:
        return f"Chat with id {chart_id} has been deleted"

    session.delete(chat)
    session.commit()

    return f"Chat with id {chart_id} has been deleted"


def delete_chat_with_user(
    session: SessionDep, current_user: CurrentUser, chart_id: int
) -> str:
    chat = session.get(Chat, chart_id)
    if not chat:
        return f"Chat with id {chart_id} has been deleted"
    if chat.create_by != current_user.id:
        raise Exception(f"Chat with id {chart_id} not Owned by the current user")
    session.delete(chat)
    session.commit()

    return f"Chat with id {chart_id} has been deleted"


def get_chart_config(session: SessionDep, chart_record_id: int) -> ObjectDict:
    stmt = select(col(ChatRecord.chart)).where(
        and_(col(ChatRecord.id) == chart_record_id)
    )
    chart_value = session.scalar(stmt)
    if isinstance(chart_value, str):
        try:
            parsed = _parse_json_object(chart_value)
            if parsed is not None:
                return parsed
        except Exception:
            pass
    return {}


def _format_column(column: Mapping[str, object]) -> str:
    """格式化单个column字段"""
    value = column.get("value", "")
    name = column.get("name", "")
    if value != name and name:
        return f"{value}({name})"
    return str(value)


def format_chart_fields(chart_info: ObjectDict) -> list[str]:
    fields: list[str] = []

    # 处理 columns
    for column in _as_object_dict_list(chart_info.get("columns")):
        fields.append(_format_column(column))

    # 处理 axis
    axis = _as_object_dict(chart_info.get("axis"))
    if axis is not None:
        # 处理 x 轴
        x_axis = _as_object_dict(axis.get("x"))
        if x_axis is not None:
            fields.append(_format_column(x_axis))

        # 处理 y 轴
        y_axis = axis.get("y")
        if y_axis:
            if isinstance(y_axis, list):
                for column in _as_object_dict_list(cast(object, y_axis)):
                    fields.append(_format_column(column))
            else:
                y_axis_mapping = _as_object_dict(y_axis)
                if y_axis_mapping is not None:
                    fields.append(_format_column(y_axis_mapping))

        # 处理 series
        series = _as_object_dict(axis.get("series"))
        if series is not None:
            fields.append(_format_column(series))

    return [field for field in fields if field]  # 过滤空字符串


def get_last_execute_sql_error(session: SessionDep, chart_id: int) -> str | None:
    stmt = (
        select(col(ChatRecord.error))
        .where(and_(col(ChatRecord.chat_id) == chart_id))
        .order_by(col(ChatRecord.create_time).desc())
        .limit(1)
    )
    res = session.scalar(stmt)
    if res:
        try:
            obj = _parse_json_object(res)
            if (
                obj is not None
                and obj.get("type")
                and obj.get("type") == "exec-sql-err"
            ):
                return _get_str(obj, "traceback")
        except Exception:
            pass

    return None


def format_json_data(origin_data: ObjectDict) -> ObjectDict:
    result: ObjectDict = {
        "fields": origin_data.get("fields") if origin_data.get("fields") else []
    }
    raw_data = origin_data.get("data")
    _list = _as_object_dict_list(raw_data)
    data = format_json_list_data(_list)
    result["data"] = data

    return result


def format_json_list_data(origin_data: list[ObjectDict]) -> list[ObjectDict]:
    data: list[ObjectDict] = []
    for _data in origin_data if origin_data else []:
        _row: ObjectDict = {}
        for key, value in _data.items():
            if value is not None:
                # 检查是否为数字且需要特殊处理
                if isinstance(value, (int, float)):
                    # 整数且超过15位 → 转字符串并标记为文本列
                    if isinstance(value, int) and len(str(abs(value))) > 15:
                        value = str(value)
                    # 小数且超过15位有效数字 → 转字符串并标记为文本列
                    elif isinstance(value, float):
                        decimal_str = format(value, ".16f").rstrip("0").rstrip(".")
                        if len(decimal_str) > 15:
                            value = str(value)
            _row[key] = value
        data.append(_row)

    return data


def get_chat_chart_config(session: SessionDep, chat_record_id: int) -> ObjectDict:
    stmt = select(col(ChatRecord.chart)).where(
        and_(col(ChatRecord.id) == chat_record_id)
    )
    chart_value = session.scalar(stmt)
    if isinstance(chart_value, str):
        try:
            parsed = _parse_json_object(chart_value)
            if parsed is not None:
                return parsed
        except Exception:
            pass
    return {}


def get_chart_data_with_user(
    session: SessionDep, current_user: CurrentUser, chat_record_id: int
) -> ObjectDict:
    stmt = select(col(ChatRecord.data)).where(
        and_(
            col(ChatRecord.id) == chat_record_id,
            col(ChatRecord.create_by) == current_user.id,
        )
    )
    data_value = session.scalar(stmt)
    if isinstance(data_value, str):
        try:
            parsed = _parse_json_object(data_value)
            if parsed is not None:
                return parsed
        except Exception:
            pass
    return {}


def get_chart_data_with_user_live(
    session: SessionDep, current_user: CurrentUser, chat_record_id: int
) -> ObjectDict:
    stmt = select(col(ChatRecord.datasource), col(ChatRecord.sql)).where(
        and_(
            col(ChatRecord.id) == chat_record_id,
            col(ChatRecord.create_by) == current_user.id,
        )
    )
    row = session.execute(stmt).first()
    if row is None:
        return {}
    row_tuple = cast(tuple[object, object], tuple(row))
    ds_id, sql_text = row_tuple
    if ds_id is None or sql_text is None:
        return {}
    if not isinstance(ds_id, int) or not isinstance(sql_text, str):
        return {}
    return get_chart_data_ds(session, ds_id, sql_text)


def get_chart_data_ds(session: SessionDep, ds_id: int, sql: str) -> ObjectDict:
    json_result: ObjectDict = {"status": "success", "data": [], "message": ""}
    try:
        datasource = get_ds(session, ds_id)
        if datasource is None:
            json_result["status"] = "failed"
            json_result["message"] = "Datasource not found"
            return json_result
        else:
            result = cast(
                ObjectDict, exec_sql(ds=datasource, sql=sql, origin_column=False)
            )
            object_array = _as_object_dict_list(result.get("data"))
            _data = DataFormat.convert_large_numbers_in_object_array(object_array)
            json_result["data"] = _data
            return json_result
    except Exception as e:
        SQLBotLogUtil.error(f"Function failed: {e}")
        json_result["status"] = "failed"
        json_result["message"] = f"{e}"
        pass
    return json_result


def get_chat_chart_data(session: SessionDep, chat_record_id: int) -> ObjectDict:
    stmt = select(col(ChatRecord.data)).where(
        and_(col(ChatRecord.id) == chat_record_id)
    )
    data_value = session.scalar(stmt)
    if isinstance(data_value, str):
        try:
            parsed = _parse_json_object(data_value)
            if parsed is not None:
                return parsed
        except Exception:
            pass
    return {}


def get_chat_predict_data_with_user(
    session: SessionDep, current_user: CurrentUser, chat_record_id: int
) -> ObjectDict:
    stmt = select(col(ChatRecord.predict_data)).where(
        and_(
            col(ChatRecord.id) == chat_record_id,
            col(ChatRecord.create_by) == current_user.id,
        )
    )
    predict_data_value = session.scalar(stmt)
    if isinstance(predict_data_value, str):
        try:
            parsed = _parse_json_object(predict_data_value)
            if parsed is not None:
                return parsed
        except Exception:
            pass
    return {}


def get_chat_predict_data(session: SessionDep, chat_record_id: int) -> ObjectDict:
    stmt = select(col(ChatRecord.predict_data)).where(
        and_(col(ChatRecord.id) == chat_record_id)
    )
    predict_data_value = session.scalar(stmt)
    if isinstance(predict_data_value, str):
        try:
            parsed = _parse_json_object(predict_data_value)
            if parsed is not None:
                return parsed
        except Exception:
            pass
    return {}


def get_chat_with_records_with_data(
    session: SessionDep,
    chart_id: int,
    current_user: CurrentUser,
    current_assistant: CurrentAssistant,
) -> ChatInfo:
    return get_chat_with_records(
        session, chart_id, current_user, current_assistant, True
    )


dynamic_ds_types = [1, 3]


def get_chat_with_records(
    session: SessionDep,
    chart_id: int,
    current_user: CurrentUser,
    current_assistant: CurrentAssistant,
    with_data: bool = False,
    trans: Trans | None = None,
) -> ChatInfo:
    chat = session.get(Chat, chart_id)
    if not chat:
        raise Exception(f"Chat with id {chart_id} not found")
    if chat.create_by != current_user.id:
        raise Exception(f"Chat with id {chart_id} not Owned by the current user")
    chat_info = ChatInfo.model_validate(chat.model_dump())

    ds: CoreDatasource | AssistantOutDsSchema | None
    if current_assistant and current_assistant.type in dynamic_ds_types:
        out_ds_instance = AssistantOutDsFactory.get_instance(current_assistant)
        ds = (
            out_ds_instance.get_ds(chat.datasource, trans)
            if chat.datasource is not None
            else None
        )
    else:
        ds = session.get(CoreDatasource, chat.datasource) if chat.datasource else None

    if not ds:
        chat_info.datasource_exists = False
        chat_info.datasource_name = "Datasource not exist"
    else:
        chat_info.datasource_exists = True
        chat_info.datasource_name = ds.name
        chat_info.ds_type = ds.type if ds.type is not None else ""

    sql_alias_log = aliased(ChatLog)
    chart_alias_log = aliased(ChatLog)
    analysis_alias_log = aliased(ChatLog)
    predict_alias_log = aliased(ChatLog)

    stmt = (
        select(
            col(ChatRecord.id),
            col(ChatRecord.chat_id),
            col(ChatRecord.create_time),
            col(ChatRecord.finish_time),
            col(ChatRecord.question),
            col(ChatRecord.sql_answer),
            col(ChatRecord.sql),
            col(ChatRecord.datasource),
            col(ChatRecord.chart_answer),
            col(ChatRecord.chart),
            col(ChatRecord.analysis),
            col(ChatRecord.predict),
            col(ChatRecord.datasource_select_answer),
            col(ChatRecord.analysis_record_id),
            col(ChatRecord.predict_record_id),
            col(ChatRecord.regenerate_record_id),
            col(ChatRecord.recommended_question),
            col(ChatRecord.first_chat),
            col(ChatRecord.finish),
            col(ChatRecord.error),
            col(sql_alias_log.reasoning_content).label("sql_reasoning_content"),
            col(chart_alias_log.reasoning_content).label("chart_reasoning_content"),
            col(analysis_alias_log.reasoning_content).label(
                "analysis_reasoning_content"
            ),
            col(predict_alias_log.reasoning_content).label("predict_reasoning_content"),
        )
        .outerjoin(
            sql_alias_log,
            and_(
                col(sql_alias_log.pid) == col(ChatRecord.id),
                col(sql_alias_log.type) == TypeEnum.CHAT,
                col(sql_alias_log.operate) == OperationEnum.GENERATE_SQL,
            ),
        )
        .outerjoin(
            chart_alias_log,
            and_(
                col(chart_alias_log.pid) == col(ChatRecord.id),
                col(chart_alias_log.type) == TypeEnum.CHAT,
                col(chart_alias_log.operate) == OperationEnum.GENERATE_CHART,
            ),
        )
        .outerjoin(
            analysis_alias_log,
            and_(
                col(analysis_alias_log.pid) == col(ChatRecord.id),
                col(analysis_alias_log.type) == TypeEnum.CHAT,
                col(analysis_alias_log.operate) == OperationEnum.ANALYSIS,
            ),
        )
        .outerjoin(
            predict_alias_log,
            and_(
                col(predict_alias_log.pid) == col(ChatRecord.id),
                col(predict_alias_log.type) == TypeEnum.CHAT,
                col(predict_alias_log.operate) == OperationEnum.PREDICT_DATA,
            ),
        )
        .where(
            and_(
                col(ChatRecord.create_by) == current_user.id,
                col(ChatRecord.chat_id) == chart_id,
            )
        )
        .order_by(col(ChatRecord.create_time))
    )
    if with_data:
        stmt = (
            select(
                col(ChatRecord.id),
                col(ChatRecord.chat_id),
                col(ChatRecord.create_time),
                col(ChatRecord.finish_time),
                col(ChatRecord.question),
                col(ChatRecord.sql_answer),
                col(ChatRecord.sql),
                col(ChatRecord.datasource),
                col(ChatRecord.chart_answer),
                col(ChatRecord.chart),
                col(ChatRecord.analysis),
                col(ChatRecord.predict),
                col(ChatRecord.datasource_select_answer),
                col(ChatRecord.analysis_record_id),
                col(ChatRecord.predict_record_id),
                col(ChatRecord.regenerate_record_id),
                col(ChatRecord.recommended_question),
                col(ChatRecord.first_chat),
                col(ChatRecord.finish),
                col(ChatRecord.error),
                col(ChatRecord.data),
                col(ChatRecord.predict_data),
            )
            .where(
                and_(
                    col(ChatRecord.create_by) == current_user.id,
                    col(ChatRecord.chat_id) == chart_id,
                )
            )
            .order_by(col(ChatRecord.create_time))
        )

    query_rows = cast(list[ChatRecordRowBase], session.execute(stmt).all())
    record_list: list[ChatRecordResult] = []

    # 批量获取所有ChatRecord的token消耗
    record_ids = [row.id for row in query_rows]
    token_usage_map: dict[int, int] = {}

    if record_ids:
        # 查询所有相关ChatLog的token_usage
        log_stmt = select(col(ChatLog.pid), col(ChatLog.token_usage)).where(
            and_(
                col(ChatLog.pid).in_(record_ids),
                col(ChatLog.local_operation).is_(False),
                col(ChatLog.operate) != OperationEnum.GENERATE_RECOMMENDED_QUESTIONS,
                col(ChatLog.token_usage).is_not(None),
            )
        )
        log_results = cast(
            list[tuple[int | None, object | None]],
            session.execute(log_stmt).all(),
        )

        # 按pid分组计算total_tokens总和
        for pid, token_usage in log_results:
            if pid and token_usage is not None:
                tokens_to_add = _get_total_tokens(token_usage)
                if tokens_to_add > 0:
                    if pid not in token_usage_map:
                        token_usage_map[pid] = 0
                    token_usage_map[pid] += tokens_to_add

    for row in query_rows:
        # 计算耗时
        duration = _safe_duration(row.create_time, row.finish_time)

        # 获取token总消耗
        total_tokens = token_usage_map.get(row.id, 0)

        record_list.append(
            _row_to_record_result(
                row,
                duration=duration,
                total_tokens=total_tokens,
                with_data=with_data,
            )
        )

    formatted_result: list[ObjectDict] = [
        format_record(record) for record in record_list
    ]

    for item in formatted_result:
        try:
            data_value = item.get("data")
            data_dict = _as_object_dict(data_value)
            if data_dict is not None:
                item["data"] = format_json_data(data_dict)
        except Exception:
            pass

    formatted_records: list[ChatRecord | ObjectDict] = list(formatted_result)
    chat_info.records = formatted_records

    return chat_info


def format_record(record: ChatRecordResult) -> ObjectDict:
    _dict = cast(ObjectDict, record.model_dump())

    if (
        record.sql_answer
        and record.sql_answer.strip() != ""
        and record.sql_answer.strip()[0] == "{"
        and record.sql_answer.strip()[-1] == "}"
    ):
        parsed = _parse_json_object(record.sql_answer)
        if parsed is not None:
            _dict["sql_answer"] = parsed.get("reasoning_content")
    if record.sql_reasoning_content and record.sql_reasoning_content.strip() != "":
        _dict["sql_answer"] = record.sql_reasoning_content
    if (
        record.chart_answer
        and record.chart_answer.strip() != ""
        and record.chart_answer.strip()[0] == "{"
        and record.chart_answer.strip()[-1] == "}"
    ):
        parsed = _parse_json_object(record.chart_answer)
        if parsed is not None:
            _dict["chart_answer"] = parsed.get("reasoning_content")
    if record.chart_reasoning_content and record.chart_reasoning_content.strip() != "":
        _dict["chart_answer"] = record.chart_reasoning_content
    if (
        record.analysis
        and record.analysis.strip() != ""
        and record.analysis.strip()[0] == "{"
        and record.analysis.strip()[-1] == "}"
    ):
        parsed = _parse_json_object(record.analysis)
        if parsed is not None:
            _dict["analysis_thinking"] = parsed.get("reasoning_content")
            _dict["analysis"] = parsed.get("content")
    if (
        record.analysis_reasoning_content
        and record.analysis_reasoning_content.strip() != ""
    ):
        _dict["analysis_thinking"] = record.analysis_reasoning_content
    if (
        record.predict
        and record.predict.strip() != ""
        and record.predict.strip()[0] == "{"
        and record.predict.strip()[-1] == "}"
    ):
        parsed = _parse_json_object(record.predict)
        if parsed is not None:
            _dict["predict"] = parsed.get("reasoning_content")
            _dict["predict_content"] = parsed.get("content")
    if (
        record.predict_reasoning_content
        and record.predict_reasoning_content.strip() != ""
    ):
        _dict["predict"] = record.predict_reasoning_content
    if record.data and record.data.strip() != "":
        try:
            parsed_value = _parse_json_value(record.data)
            if parsed_value is not None:
                _dict["data"] = parsed_value
        except Exception:
            pass
    if record.predict_data and record.predict_data.strip() != "":
        try:
            parsed_value = _parse_json_value(record.predict_data)
            if parsed_value is not None:
                _dict["predict_data"] = parsed_value
        except Exception:
            pass
    if record.sql and record.sql.strip() != "":
        try:
            _dict["sql"] = sqlparse.format(record.sql, reindent=True)
        except Exception:
            pass

    # 格式化duration字段，保留2位小数
    duration_value = _dict.get("duration")
    if isinstance(duration_value, (int, float)):
        try:
            _dict["duration"] = round(duration_value, 2)
        except Exception:
            pass

    # 格式化total_tokens字段
    total_tokens_value = _dict.get("total_tokens")
    if isinstance(total_tokens_value, (int, float)):
        try:
            _dict["total_tokens"] = int(total_tokens_value) if total_tokens_value else 0
        except Exception:
            _dict["total_tokens"] = 0

    # 去除返回前端多余的字段
    _ = _dict.pop("sql_reasoning_content", None)
    _ = _dict.pop("chart_reasoning_content", None)
    _ = _dict.pop("analysis_reasoning_content", None)
    _ = _dict.pop("predict_reasoning_content", None)

    return _dict


def get_chat_log_history(
    session: SessionDep,
    chat_record_id: int,
    current_user: CurrentUser,
    without_steps: bool = False,
) -> ChatLogHistory:
    """
    获取ChatRecord的详细历史记录

    Args:
        session: 数据库会话
        chat_record_id: ChatRecord的ID
        current_user: 当前用户
        without_steps

    Returns:
        ChatLogHistory: 包含历史步骤和时间信息的对象
    """
    # 1. 首先验证ChatRecord存在且属于当前用户
    chat_record = session.get(ChatRecord, chat_record_id)
    if not chat_record:
        raise Exception(f"ChatRecord with id {chat_record_id} not found")

    if chat_record.create_by != current_user.id:
        raise Exception(
            f"ChatRecord with id {chat_record_id} not owned by the current user"
        )

    # 2. 查询与该ChatRecord相关的所有ChatLog记录
    chat_logs = list(
        session.scalars(
            select(ChatLog)
            .where(
                col(ChatLog.pid) == chat_record_id,
                col(ChatLog.operate) != OperationEnum.GENERATE_RECOMMENDED_QUESTIONS,
            )
            .order_by(col(ChatLog.start_time))
        ).all()
    )

    # 3. 计算总的时间和token信息
    total_tokens = 0
    steps: list[ChatLogHistoryItem | ObjectDict] = []

    for log in cast(list[ChatLogProtocol], chat_logs):
        # 计算单条记录的token消耗
        log_tokens = _get_total_tokens(log.token_usage)

        # 累加到总token消耗
        total_tokens += log_tokens

        if not without_steps:
            # 计算单条记录的耗时
            duration = _safe_rounded_duration(log.start_time, log.finish_time)

            # 获取操作类型的枚举名称
            operate_name = _get_operate_name(log.operate)
            message = _parse_log_message(log)

            # 创建ChatLogHistoryItem
            history_item = ChatLogHistoryItem(
                start_time=log.start_time,
                finish_time=log.finish_time,
                duration=duration,
                total_tokens=int(log_tokens),
                operate=operate_name,
                local_operation=log.local_operation,
                error=log.error,
                message=message,
            )

            steps.append(history_item)

    # 4. 计算总耗时（使用ChatRecord的时间）
    total_duration = None
    if chat_record.create_time and chat_record.finish_time:
        try:
            time_diff = chat_record.finish_time - chat_record.create_time
            total_duration = round(time_diff.total_seconds(), 2)
        except Exception:
            total_duration = None

    # 5. 创建并返回ChatLogHistory对象
    chat_log_history = ChatLogHistory(
        start_time=chat_record.create_time,  # 使用ChatRecord的create_time
        finish_time=chat_record.finish_time,  # 使用ChatRecord的finish_time
        duration=total_duration,
        total_tokens=int(total_tokens),
        steps=steps,
    )

    return chat_log_history


def get_chat_brief_generate(session: SessionDep, chat_id: int) -> bool:
    chat = get_chat(session=session, chat_id=chat_id)
    if chat is not None:
        return chat.brief_generate
    else:
        return False


def list_generate_sql_logs(session: SessionDep, chart_id: int) -> list[ChatLog]:
    stmt = (
        select(ChatLog)
        .where(
            and_(
                col(ChatLog.pid).in_(
                    select(col(ChatRecord.id)).where(
                        and_(col(ChatRecord.chat_id) == chart_id)
                    )
                ),
                col(ChatLog.type) == TypeEnum.CHAT,
                col(ChatLog.operate) == OperationEnum.GENERATE_SQL,
                col(ChatLog.finish_time).is_not(None),
            )
        )
        .order_by(col(ChatLog.start_time))
    )
    result = list(session.scalars(stmt).all())
    return [ChatLog.model_validate(row.model_dump()) for row in result]


def list_generate_chart_logs(session: SessionDep, chart_id: int) -> list[ChatLog]:
    stmt = (
        select(ChatLog)
        .where(
            and_(
                col(ChatLog.pid).in_(
                    select(col(ChatRecord.id)).where(
                        and_(col(ChatRecord.chat_id) == chart_id)
                    )
                ),
                col(ChatLog.type) == TypeEnum.CHAT,
                col(ChatLog.operate) == OperationEnum.GENERATE_CHART,
                col(ChatLog.finish_time).is_not(None),
            )
        )
        .order_by(col(ChatLog.start_time))
    )
    result = list(session.scalars(stmt).all())
    return [ChatLog.model_validate(row.model_dump()) for row in result]


def create_chat(
    session: SessionDep,
    current_user: CurrentUser,
    create_chat_obj: CreateChat,
    require_datasource: bool = True,
    current_assistant: CurrentAssistant | None = None,
) -> ChatInfo:
    if not create_chat_obj.datasource and require_datasource:
        raise Exception("Datasource cannot be None")

    if not create_chat_obj.question or create_chat_obj.question.strip() == "":
        create_chat_obj.question = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    chat_payload: dict[str, Any] = {
        "id": None,
        "create_time": datetime.datetime.now(),
        "create_by": current_user.id,
        "oid": current_user.oid,
        "brief": create_chat_obj.question.strip()[:20],
        "origin": create_chat_obj.origin if create_chat_obj.origin is not None else 0,
        "datasource": create_chat_obj.datasource,
        "engine_type": "",
        "recommended_question_answer": None,
        "recommended_question": None,
    }
    chat = Chat(**chat_payload)
    ds: CoreDatasource | AssistantOutDsSchema | None = None
    if create_chat_obj.datasource:
        chat.datasource = create_chat_obj.datasource
        if current_assistant and current_assistant.type == 1:
            out_ds_instance: AssistantOutDs = AssistantOutDsFactory.get_instance(
                current_assistant
            )
            ds = out_ds_instance.get_ds(chat.datasource)
            if ds and ds.type:
                ds.type_name = DB.get_db(ds.type).type
        else:
            ds = session.get(CoreDatasource, create_chat_obj.datasource)
            if ds and ds.oid != current_user.oid:
                raise Exception(
                    f"Datasource with id {create_chat_obj.datasource} does not belong to current workspace"
                )

        if not ds:
            raise Exception(
                f"Datasource with id {create_chat_obj.datasource} not found"
            )

        chat.engine_type = ds.type_name if ds.type_name is not None else ""
    else:
        chat.engine_type = ""

    chat_info = ChatInfo.model_validate(chat.model_dump())

    session.add(chat)
    session.flush()
    session.refresh(chat)
    chat_info.id = chat.id
    session.commit()

    if ds:
        chat_info.datasource_exists = True
        chat_info.datasource_name = ds.name
        chat_info.ds_type = ds.type if ds.type is not None else ""

    if require_datasource and ds:
        # generate first empty record
        record_payload: dict[str, Any] = {
            "id": None,
            "chat_id": chat.id,
            "ai_modal_id": None,
            "first_chat": True,
            "create_time": datetime.datetime.now(),
            "finish_time": None,
            "create_by": current_user.id,
            "datasource": ds.id,
            "engine_type": ds.type_name,
            "question": None,
            "sql_answer": None,
            "sql": None,
            "sql_exec_result": None,
            "data": None,
            "chart_answer": None,
            "chart": None,
            "analysis": None,
            "predict": None,
            "predict_data": None,
            "recommended_question_answer": None,
            "recommended_question": None,
            "datasource_select_answer": None,
            "finish": True,
            "error": None,
            "analysis_record_id": None,
            "predict_record_id": None,
            "regenerate_record_id": None,
        }
        record = ChatRecord(**record_payload)
        if chat.id is None or ds.id is None or ds.type_name is None:
            raise Exception("Invalid chat or datasource data")
        if isinstance(ds, CoreDatasource) and ds.recommended_config == 2:
            questions = get_datasource_recommended_chart(session, ds.id)
            record.recommended_question = orjson.dumps(questions).decode()
            record.recommended_question_answer = orjson.dumps(
                {"content": questions}
            ).decode()

        _record = record.model_copy(deep=True)

        session.add(record)
        session.flush()
        session.refresh(record)
        _record.id = record.id
        session.commit()

        chat_info.records.append(_record)

    return chat_info


def save_question(
    session: SessionDep, current_user: CurrentUser, question: ChatQuestion
) -> ChatRecord:
    if not question.chat_id:
        raise Exception("ChatId cannot be None")
    if not question.question or question.question.strip() == "":
        raise Exception("Question cannot be Empty")

    # chat = session.query(Chat).filter(Chat.id == question.chat_id).first()
    chat = session.get(Chat, question.chat_id)
    if not chat:
        raise Exception(f"Chat with id {question.chat_id} not found")

    record_payload: dict[str, Any] = {
        "id": None,
        "chat_id": chat.id,
        "ai_modal_id": question.ai_modal_id,
        "first_chat": False,
        "create_time": datetime.datetime.now(),
        "finish_time": None,
        "create_by": current_user.id,
        "datasource": chat.datasource,
        "engine_type": chat.engine_type,
        "question": question.question,
        "sql_answer": None,
        "sql": None,
        "sql_exec_result": None,
        "data": None,
        "chart_answer": None,
        "chart": None,
        "analysis": None,
        "predict": None,
        "predict_data": None,
        "recommended_question_answer": None,
        "recommended_question": None,
        "datasource_select_answer": None,
        "finish": False,
        "error": None,
        "analysis_record_id": None,
        "predict_record_id": None,
        "regenerate_record_id": question.regenerate_record_id,
    }
    record = ChatRecord(**record_payload)
    if chat.id is None:
        raise Exception(f"Chat with id {question.chat_id} not found")

    result = record.model_copy(deep=True)

    session.add(record)
    session.flush()
    session.refresh(record)
    result.id = record.id
    session.commit()

    return result


def save_analysis_predict_record(
    session: SessionDep, base_record: ChatRecord, action_type: str
) -> ChatRecord:
    record_payload: dict[str, Any] = {
        "id": None,
        "chat_id": base_record.chat_id,
        "ai_modal_id": base_record.ai_modal_id,
        "first_chat": False,
        "create_time": datetime.datetime.now(),
        "finish_time": None,
        "create_by": base_record.create_by,
        "datasource": base_record.datasource,
        "engine_type": base_record.engine_type,
        "question": base_record.question,
        "sql_answer": None,
        "sql": None,
        "sql_exec_result": None,
        "data": base_record.data,
        "chart_answer": None,
        "chart": base_record.chart,
        "analysis": None,
        "predict": None,
        "predict_data": None,
        "recommended_question_answer": None,
        "recommended_question": None,
        "datasource_select_answer": None,
        "finish": False,
        "error": None,
        "analysis_record_id": None,
        "predict_record_id": None,
        "regenerate_record_id": None,
    }
    record = ChatRecord(**record_payload)

    if action_type == "analysis":
        if base_record.id is not None:
            record.analysis_record_id = base_record.id
    elif action_type == "predict":
        if base_record.id is not None:
            record.predict_record_id = base_record.id

    result = record.model_copy(deep=True)

    session.add(record)
    session.flush()
    session.refresh(record)
    result.id = record.id
    session.commit()

    return result


def start_log(
    session: SessionDep,
    ai_modal_id: int | None = None,
    ai_modal_name: str | None = None,
    operate: OperationEnum | None = None,
    record_id: int | None = None,
    full_message: list[MessagePayload] | MessagePayload | None = None,
    local_operation: bool = False,
) -> ChatLog:
    log_payload: dict[str, Any] = {
        "id": None,
        "type": TypeEnum.CHAT,
        "operate": operate,
        "pid": record_id,
        "ai_modal_id": ai_modal_id,
        "base_modal": ai_modal_name,
        "messages": full_message,
        "reasoning_content": None,
        "start_time": datetime.datetime.now(),
        "finish_time": None,
        "token_usage": None,
        "local_operation": local_operation,
        "error": False,
    }
    log = ChatLog(**log_payload)

    result = log.model_copy(deep=True)

    session.add(log)
    session.flush()
    session.refresh(log)
    result.id = log.id
    session.commit()

    return result


def end_log(
    session: SessionDep,
    log: ChatLog,
    full_message: list[MessagePayload] | MessagePayload,
    reasoning_content: str | None = None,
    token_usage: ObjectDict | int | None = None,
) -> ChatLog:
    if token_usage is None:
        token_usage = {}
    log.messages = [full_message] if isinstance(full_message, dict) else full_message
    log.token_usage = token_usage
    log.finish_time = datetime.datetime.now()
    log.reasoning_content = (
        reasoning_content
        if reasoning_content and len(reasoning_content.strip()) > 0
        else None
    )

    stmt = (
        update(ChatLog)
        .where(and_(col(ChatLog.id) == log.id))
        .values(
            messages=log.messages,
            token_usage=log.token_usage,
            finish_time=log.finish_time,
            reasoning_content=log.reasoning_content,
        )
    )
    _ = session.exec(stmt)
    session.commit()

    return log


def trigger_log_error(session: SessionDep, log: ChatLog) -> ChatLog:
    log.error = True
    stmt = update(ChatLog).where(and_(col(ChatLog.id) == log.id)).values(error=True)
    _ = session.exec(stmt)
    session.commit()

    return log


def save_sql_answer(session: SessionDep, record_id: int, answer: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record_id))
        .values(
            sql_answer=answer,
        )
    )

    _ = session.exec(stmt)

    session.commit()

    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    return record


def save_analysis_answer(
    session: SessionDep, record_id: int, answer: str = ""
) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record_id))
        .values(
            analysis=answer,
        )
    )

    _ = session.exec(stmt)

    session.commit()

    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    return record


def save_predict_answer(session: SessionDep, record_id: int, answer: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record_id))
        .values(
            predict=answer,
        )
    )

    _ = session.exec(stmt)

    session.commit()

    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    return record


def save_select_datasource_answer(
    session: SessionDep,
    record_id: int,
    answer: str,
    datasource: int | None = None,
    engine_type: str | None = None,
) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    record.datasource_select_answer = answer

    if datasource:
        record.datasource = datasource
        record.engine_type = engine_type if engine_type is not None else ""

    result = record.model_copy(deep=True)

    if datasource:
        stmt = (
            update(ChatRecord)
            .where(and_(col(ChatRecord.id) == record.id))
            .values(
                datasource_select_answer=record.datasource_select_answer,
                datasource=record.datasource,
                engine_type=record.engine_type,
            )
        )
    else:
        stmt = (
            update(ChatRecord)
            .where(and_(col(ChatRecord.id) == record.id))
            .values(
                datasource_select_answer=record.datasource_select_answer,
            )
        )

    _ = session.exec(stmt)

    session.commit()

    return result


def save_recommend_question_answer(
    session: SessionDep,
    record_id: int,
    answer: MessagePayload | None = None,
    articles_number: int | None = 4,
) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")

    recommended_question_answer = orjson.dumps(answer).decode()

    json_str = "[]"
    if answer and answer.get("content") and answer.get("content") != "":
        try:
            content_text = answer.get("content")
            if isinstance(content_text, str):
                nested_json = extract_nested_json(content_text)
                if nested_json is not None:
                    json_str = nested_json

            if not json_str:
                json_str = "[]"
        except Exception:
            pass
    recommended_question = json_str

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record_id))
        .values(
            recommended_question_answer=recommended_question_answer,
            recommended_question=recommended_question,
        )
    )

    _ = session.exec(stmt)
    session.commit()

    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")
    record.recommended_question_answer = recommended_question_answer
    record.recommended_question = recommended_question
    if (articles_number or 0) > 4:
        stmt_chat = (
            update(Chat)
            .where(and_(col(Chat.id) == record.chat_id))
            .values(
                recommended_question_answer=recommended_question_answer,
                recommended_question=recommended_question,
                recommended_generate=True,
            )
        )
        _ = session.exec(stmt_chat)
        session.commit()

    return record


def save_sql(session: SessionDep, record_id: int, sql: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")

    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    record.sql = sql

    result = record.model_copy(deep=True)

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record.id))
        .values(sql=record.sql)
    )

    _ = session.exec(stmt)

    session.commit()

    return result


def save_chart_answer(session: SessionDep, record_id: int, answer: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record_id))
        .values(
            chart_answer=answer,
        )
    )

    _ = session.exec(stmt)

    session.commit()

    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    return record


def save_chart(session: SessionDep, record_id: int, chart: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    record.chart = chart

    result = record.model_copy(deep=True)

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record.id))
        .values(chart=record.chart)
    )

    _ = session.exec(stmt)

    session.commit()

    return result


def save_predict_data(
    session: SessionDep, record_id: int, data: str = ""
) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    record.predict_data = data

    result = record.model_copy(deep=True)

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record.id))
        .values(predict_data=record.predict_data)
    )

    _ = session.exec(stmt)

    session.commit()

    return result


def save_error_message(session: SessionDep, record_id: int, message: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    record.error = message
    record.finish = True
    record.finish_time = datetime.datetime.now()

    result = record.model_copy(deep=True)

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record.id))
        .values(
            error=record.error, finish=record.finish, finish_time=record.finish_time
        )
    )

    _ = session.exec(stmt)

    session.commit()

    # log error finish
    stmt = (
        update(ChatLog)
        .where(and_(col(ChatLog.pid) == record.id, col(ChatLog.finish_time).is_(None)))
        .values(finish_time=record.finish_time, error=True)
    )
    _ = session.exec(stmt)
    session.commit()

    return result


def save_sql_exec_data(session: SessionDep, record_id: int, data: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    record.data = data

    result = record.model_copy(deep=True)

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record.id))
        .values(
            data=record.data,
        )
    )

    _ = session.exec(stmt)

    session.commit()

    return result


def finish_record(session: SessionDep, record_id: int) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)
    if record is None:
        raise Exception(f"ChatRecord with id {record_id} not found")

    record.finish = True
    record.finish_time = datetime.datetime.now()

    result = record.model_copy(deep=True)

    stmt = (
        update(ChatRecord)
        .where(and_(col(ChatRecord.id) == record.id))
        .values(finish=record.finish, finish_time=record.finish_time)
    )

    _ = session.exec(stmt)

    session.commit()

    return result


def get_old_questions(session: SessionDep, datasource: int) -> list[str]:
    records: list[str] = []
    if not datasource:
        return records
    stmt = (
        select(col(ChatRecord.question))
        .where(
            and_(
                col(ChatRecord.datasource) == datasource,
                col(ChatRecord.question).isnot(None),
                col(ChatRecord.error).is_(None),
            )
        )
        .order_by(col(ChatRecord.create_time).desc())
        .limit(20)
    )
    result = cast(list[object], session.scalars(stmt).all())
    for question in result:
        if isinstance(question, str):
            records.append(question)
    return records
