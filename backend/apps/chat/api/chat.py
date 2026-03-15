import asyncio
import io
import traceback
from collections.abc import Iterator
from importlib import import_module
from typing import Any, cast

import orjson
import pandas as pd
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlmodel import col
from starlette.responses import JSONResponse

from apps.chat.curd.chat import (
    create_chat,
    delete_chat_with_user,
    format_json_data,
    format_json_list_data,
    get_chart_config,
    get_chart_data_with_user,
    get_chart_data_with_user_live,
    get_chat_chart_data,
    get_chat_log_history,
    get_chat_predict_data,
    get_chat_predict_data_with_user,
    get_chat_record_by_id,
    get_chat_with_records,
    get_chat_with_records_with_data,
    list_chats,
    list_recent_questions,
    rename_chat_with_user,
)
from apps.chat.models.chat_model import (
    AxisObj,
    Chat,
    ChatFinishStep,
    ChatInfo,
    ChatLogHistory,
    ChatQuestion,
    ChatRecord,
    CreateChat,
    QuickCommand,
    RenameChat,
)
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.audit.models.log_model import OperationModules, OperationType
from common.audit.schemas.logger_decorator import LogConfig, system_log
from common.core.deps import CurrentAssistant, CurrentUser, SessionDep, Trans
from common.utils.command_utils import parse_quick_command
from common.utils.data_format import DataFormat

router = APIRouter(tags=["Data Q&A"], prefix="/chat")


def _get_llm_service_class() -> type[Any]:
    module = import_module("apps.chat.task.llm")
    return cast(type[Any], module.LLMService)


@router.get(
    "/list", response_model=list[Chat], summary=f"{PLACEHOLDER_PREFIX}get_chat_list"
)
async def chats(session: SessionDep, current_user: CurrentUser) -> list[Chat]:
    return list_chats(session, current_user)


@router.get(
    "/{chart_id}", response_model=ChatInfo, summary=f"{PLACEHOLDER_PREFIX}get_chat"
)
async def get_chat(
    session: SessionDep,
    current_user: CurrentUser,
    chart_id: int,
    current_assistant: CurrentAssistant,
    trans: Trans,
) -> ChatInfo:
    def inner() -> ChatInfo:
        return get_chat_with_records(
            chart_id=chart_id,
            session=session,
            current_user=current_user,
            current_assistant=current_assistant,
            trans=trans,
        )

    return await asyncio.to_thread(inner)


@router.get(
    "/{chart_id}/with_data",
    response_model=ChatInfo,
    summary=f"{PLACEHOLDER_PREFIX}get_chat_with_data",
)
async def get_chat_with_data(
    session: SessionDep,
    current_user: CurrentUser,
    chart_id: int,
    current_assistant: CurrentAssistant,
) -> ChatInfo:
    def inner() -> ChatInfo:
        return get_chat_with_records_with_data(
            chart_id=chart_id,
            session=session,
            current_user=current_user,
            current_assistant=current_assistant,
        )

    return await asyncio.to_thread(inner)


""" @router.get("/record/{chat_record_id}/data", summary=f"{PLACEHOLDER_PREFIX}get_chart_data")
async def chat_record_data(session: SessionDep, chat_record_id: int):
    def inner():
        data = get_chat_chart_data(chat_record_id=chat_record_id, session=session)
        return format_json_data(data)

    return await asyncio.to_thread(inner)


@router.get("/record/{chat_record_id}/predict_data", summary=f"{PLACEHOLDER_PREFIX}get_chart_predict_data")
async def chat_predict_data(session: SessionDep, chat_record_id: int):
    def inner():
        data = get_chat_predict_data(chat_record_id=chat_record_id, session=session)
        return format_json_list_data(data)

    return await asyncio.to_thread(inner) """


@router.get(
    "/record/{chat_record_id}/data", summary=f"{PLACEHOLDER_PREFIX}get_chart_data"
)
async def chat_record_data(
    session: SessionDep, current_user: CurrentUser, chat_record_id: int
) -> dict[str, Any]:
    def inner() -> dict[str, Any]:
        data = get_chart_data_with_user(
            chat_record_id=chat_record_id, session=session, current_user=current_user
        )
        return format_json_data(data)

    return await asyncio.to_thread(inner)


@router.get(
    "/record/{chat_record_id}/data_live",
    summary=f"{PLACEHOLDER_PREFIX}get_chart_data_live",
)
async def chat_record_data_live(
    session: SessionDep, current_user: CurrentUser, chat_record_id: int
) -> dict[str, Any]:
    def inner() -> dict[str, Any]:
        data = get_chart_data_with_user_live(
            chat_record_id=chat_record_id, session=session, current_user=current_user
        )
        return format_json_data(data)

    return await asyncio.to_thread(inner)


@router.get(
    "/record/{chat_record_id}/predict_data",
    summary=f"{PLACEHOLDER_PREFIX}get_chart_predict_data",
)
async def chat_predict_data(
    session: SessionDep, current_user: CurrentUser, chat_record_id: int
) -> list[dict[str, Any]]:
    def inner() -> list[dict[str, Any]]:
        data = get_chat_predict_data_with_user(
            chat_record_id=chat_record_id, session=session, current_user=current_user
        )
        raw_items = data.get("data")
        list_items = (
            [item for item in raw_items if isinstance(item, dict)]
            if isinstance(raw_items, list)
            else []
        )
        return format_json_list_data(list_items)

    return await asyncio.to_thread(inner)


@router.get(
    "/record/{chat_record_id}/log", summary=f"{PLACEHOLDER_PREFIX}get_record_log"
)
async def chat_record_log(
    session: SessionDep, current_user: CurrentUser, chat_record_id: int
) -> ChatLogHistory:
    def inner() -> ChatLogHistory:
        return get_chat_log_history(session, chat_record_id, current_user)

    return await asyncio.to_thread(inner)


@router.get(
    "/record/{chat_record_id}/usage", summary=f"{PLACEHOLDER_PREFIX}get_record_usage"
)
async def chat_record_usage(
    session: SessionDep, current_user: CurrentUser, chat_record_id: int
) -> ChatLogHistory:
    def inner() -> ChatLogHistory:
        return get_chat_log_history(session, chat_record_id, current_user, True)

    return await asyncio.to_thread(inner)


""" @router.post("/rename", response_model=str, summary=f"{PLACEHOLDER_PREFIX}rename_chat")
@system_log(LogConfig(
    operation_type=OperationType.UPDATE,
    module=OperationModules.CHAT,
    resource_id_expr="chat.id"
))
async def rename(session: SessionDep, chat: RenameChat):
    try:
        return rename_chat(session=session, rename_object=chat)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) """


@router.post("/rename", response_model=str, summary=f"{PLACEHOLDER_PREFIX}rename_chat")
@system_log(
    LogConfig(
        operation_type=OperationType.UPDATE,
        module=OperationModules.CHAT,
        resource_id_expr="chat.id",
    )
)
async def rename(
    session: SessionDep, current_user: CurrentUser, chat: RenameChat
) -> str:
    try:
        return rename_chat_with_user(
            session=session, current_user=current_user, rename_object=chat
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


""" @router.delete("/{chart_id}/{brief}", response_model=str, summary=f"{PLACEHOLDER_PREFIX}delete_chat")
@system_log(LogConfig(
    operation_type=OperationType.DELETE,
    module=OperationModules.CHAT,
    resource_id_expr="chart_id",
    remark_expr="brief"
))
async def delete(session: SessionDep, chart_id: int, brief: str):
    try:
        return delete_chat(session=session, chart_id=chart_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        ) """


@router.delete(
    "/{chart_id}/{brief}",
    response_model=str,
    summary=f"{PLACEHOLDER_PREFIX}delete_chat",
)
@system_log(
    LogConfig(
        operation_type=OperationType.DELETE,
        module=OperationModules.CHAT,
        resource_id_expr="chart_id",
        remark_expr="brief",
    )
)
async def delete(
    session: SessionDep, current_user: CurrentUser, chart_id: int, brief: str
) -> str:
    try:
        _ = brief
        return delete_chat_with_user(
            session=session, current_user=current_user, chart_id=chart_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/start", response_model=ChatInfo, summary=f"{PLACEHOLDER_PREFIX}start_chat"
)
@require_permissions(
    permission=SqlbotPermission(type="ds", keyExpression="create_chat_obj.datasource")
)
@system_log(
    LogConfig(
        operation_type=OperationType.CREATE,
        module=OperationModules.CHAT,
        result_id_expr="id",
    )
)
async def start_chat(
    session: SessionDep, current_user: CurrentUser, create_chat_obj: CreateChat
) -> ChatInfo:
    try:
        return create_chat(session, current_user, create_chat_obj)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/assistant/start",
    response_model=ChatInfo,
    summary=f"{PLACEHOLDER_PREFIX}assistant_start_chat",
)
@system_log(
    LogConfig(
        operation_type=OperationType.CREATE,
        module=OperationModules.CHAT,
        result_id_expr="id",
    )
)
async def assistant_start_chat(
    session: SessionDep,
    current_user: CurrentUser,
    current_assistant: CurrentAssistant,
    create_chat_obj: CreateChat = CreateChat(origin=2),
) -> ChatInfo:
    try:
        return create_chat(
            session,
            current_user,
            create_chat_obj,
            create_chat_obj.datasource is not None,
            current_assistant,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/recommend_questions/{chat_record_id}",
    summary=f"{PLACEHOLDER_PREFIX}ask_recommend_questions",
)
async def ask_recommend_questions(
    session: SessionDep,
    current_user: CurrentUser,
    chat_record_id: int,
    current_assistant: CurrentAssistant,
    articles_number: int = 4,
) -> StreamingResponse:
    def _return_empty() -> Iterator[str]:
        yield (
            "data:"
            + orjson.dumps({"content": "[]", "type": "recommended_question"}).decode()
            + "\n\n"
        )

    try:
        record = get_chat_record_by_id(session, chat_record_id)

        if not record:
            return StreamingResponse(_return_empty(), media_type="text/event-stream")

        request_question = ChatQuestion(
            chat_id=record.chat_id, question=record.question if record.question else ""
        )

        llm_service = await cast(Any, _get_llm_service_class()).create(
            session, current_user, request_question, current_assistant, True
        )
        llm_service.set_record(record)
        llm_service.set_articles_number(articles_number)
        llm_service.run_recommend_questions_task_async()
    except Exception as e:
        traceback.print_exc()

        def _err(_e: Exception) -> Iterator[str]:
            yield (
                "data:"
                + orjson.dumps({"content": str(_e), "type": "error"}).decode()
                + "\n\n"
            )

        return StreamingResponse(_err(e), media_type="text/event-stream")

    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")


@router.get(
    "/recent_questions/{datasource_id}",
    response_model=list[str],
    summary=f"{PLACEHOLDER_PREFIX}get_recommend_questions",
)
# @require_permissions(permission=SqlbotPermission(type='ds', keyExpression="datasource_id"))
async def recommend_questions(
    session: SessionDep,
    current_user: CurrentUser,
    datasource_id: int = Path(..., description=f"{PLACEHOLDER_PREFIX}ds_id"),
) -> list[str]:
    return list_recent_questions(
        session=session, current_user=current_user, datasource_id=datasource_id
    )


def find_base_question(record_id: int, session: SessionDep) -> str:
    stmt = select(col(ChatRecord.question), col(ChatRecord.regenerate_record_id)).where(
        and_(col(ChatRecord.id) == record_id)
    )
    _record = session.execute(stmt).fetchone()
    if not _record:
        raise Exception("Cannot find base chat record")
    rec_question, rec_regenerate_record_id = _record
    base_question = rec_question if rec_question is not None else ""
    if rec_regenerate_record_id:
        return find_base_question(rec_regenerate_record_id, session)
    return base_question


@router.post(
    "/question", response_model=None, summary=f"{PLACEHOLDER_PREFIX}ask_question"
)
@require_permissions(
    permission=SqlbotPermission(type="chat", keyExpression="request_question.chat_id")
)
async def question_answer(
    session: SessionDep,
    current_user: CurrentUser,
    request_question: ChatQuestion,
    current_assistant: CurrentAssistant,
) -> StreamingResponse | JSONResponse:
    return await question_answer_inner(
        session, current_user, request_question, current_assistant, embedding=True
    )


async def question_answer_inner(
    session: SessionDep,
    current_user: CurrentUser,
    request_question: ChatQuestion,
    current_assistant: CurrentAssistant | None = None,
    in_chat: bool = True,
    stream: bool = True,
    finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART,
    embedding: bool = False,
) -> StreamingResponse | JSONResponse:
    try:
        command, text_before_command, record_id, warning_info = parse_quick_command(
            request_question.question or ""
        )
        _ = warning_info
        if command:
            # todo 对话界面下，暂不支持分析和预测，需要改造前端
            if in_chat and (
                command == QuickCommand.ANALYSIS or command == QuickCommand.PREDICT_DATA
            ):
                raise Exception(f"Command: {command.value} temporary not supported")

            if record_id is not None:
                # 排除analysis和predict
                last_stmt = (
                    select(
                        col(ChatRecord.id),
                        col(ChatRecord.chat_id),
                        col(ChatRecord.analysis_record_id),
                        col(ChatRecord.predict_record_id),
                        col(ChatRecord.regenerate_record_id),
                        col(ChatRecord.first_chat),
                    )
                    .where(and_(col(ChatRecord.id) == record_id))
                    .order_by(col(ChatRecord.create_time).desc())
                )
                _record = session.execute(last_stmt).fetchone()
                if not _record:
                    raise Exception(f"Record id: {record_id} does not exist")

                (
                    rec_id,
                    rec_chat_id,
                    rec_analysis_record_id,
                    rec_predict_record_id,
                    rec_regenerate_record_id,
                    rec_first_chat,
                ) = _record

                if rec_chat_id != request_question.chat_id:
                    raise Exception(
                        f"Record id: {record_id} does not belong to this chat"
                    )
                if rec_first_chat:
                    raise Exception(
                        f"Record id: {record_id} does not support this operation"
                    )

                if rec_analysis_record_id:
                    raise Exception("Analysis record does not support this operation")
                if rec_predict_record_id:
                    raise Exception(
                        "Predict data record does not support this operation"
                    )

            else:  # get last record id
                stmt = (
                    select(
                        col(ChatRecord.id),
                        col(ChatRecord.chat_id),
                        col(ChatRecord.regenerate_record_id),
                    )
                    .where(
                        and_(
                            col(ChatRecord.chat_id) == request_question.chat_id,
                            col(ChatRecord.first_chat).is_(False),
                            col(ChatRecord.analysis_record_id).is_(None),
                            col(ChatRecord.predict_record_id).is_(None),
                        )
                    )
                    .order_by(col(ChatRecord.create_time).desc())
                    .limit(1)
                )
                _record = session.execute(stmt).fetchone()

                if not _record:
                    raise Exception("You have not ask any question")

                rec_id, rec_chat_id, rec_regenerate_record_id = _record

            # 没有指定的，就查询上一个
            if not rec_regenerate_record_id:
                rec_regenerate_record_id = rec_id

            # 针对已经是重新生成的提问，需要找到原来的提问是什么
            base_question_text = find_base_question(rec_regenerate_record_id, session)
            text_before_command = (
                text_before_command
                + ("\n" if text_before_command else "")
                + base_question_text
            )

            if command == QuickCommand.REGENERATE:
                request_question.question = text_before_command
                request_question.regenerate_record_id = rec_id
                return await stream_sql(
                    session,
                    current_user,
                    request_question,
                    current_assistant,
                    in_chat,
                    stream,
                    finish_step,
                    embedding,
                )

            elif command == QuickCommand.ANALYSIS:
                return await analysis_or_predict(
                    session,
                    current_user,
                    rec_id,
                    "analysis",
                    current_assistant,
                    in_chat,
                    stream,
                )

            elif command == QuickCommand.PREDICT_DATA:
                return await analysis_or_predict(
                    session,
                    current_user,
                    rec_id,
                    "predict",
                    current_assistant,
                    in_chat,
                    stream,
                )
            else:
                raise Exception(f"Unknown command: {command.value}")
        else:
            return await stream_sql(
                session,
                current_user,
                request_question,
                current_assistant,
                in_chat,
                stream,
                finish_step,
                embedding,
            )
    except Exception as e:
        traceback.print_exc()

        if stream:

            def _err(_e: Exception) -> Iterator[str]:
                if in_chat:
                    yield (
                        "data:"
                        + orjson.dumps({"content": str(_e), "type": "error"}).decode()
                        + "\n\n"
                    )
                else:
                    yield "&#x274c; **ERROR:**\n"
                    yield f"> {str(_e)}\n"

            return StreamingResponse(_err(e), media_type="text/event-stream")
        else:
            return JSONResponse(
                content={"message": str(e)},
                status_code=500,
            )


async def stream_sql(
    session: SessionDep,
    current_user: CurrentUser,
    request_question: ChatQuestion,
    current_assistant: CurrentAssistant | None = None,
    in_chat: bool = True,
    stream: bool = True,
    finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART,
    embedding: bool = False,
) -> StreamingResponse | JSONResponse:
    try:
        llm_service = await cast(Any, _get_llm_service_class()).create(
            session,
            current_user,
            request_question,
            current_assistant,
            embedding=embedding,
        )
        llm_service.init_record(session=session)
        llm_service.run_task_async(
            in_chat=in_chat, stream=stream, finish_step=finish_step
        )
    except Exception as e:
        traceback.print_exc()

        if stream:

            def _err(_e: Exception) -> Iterator[str]:
                yield (
                    "data:"
                    + orjson.dumps({"content": str(_e), "type": "error"}).decode()
                    + "\n\n"
                )

            return StreamingResponse(_err(e), media_type="text/event-stream")
        else:
            return JSONResponse(
                content={"message": str(e)},
                status_code=500,
            )
    if stream:
        return StreamingResponse(
            llm_service.await_result(), media_type="text/event-stream"
        )
    else:
        res = llm_service.await_result()
        raw_data: dict[str, Any] = {}
        for chunk in res:
            if isinstance(chunk, dict):
                raw_data = chunk
        status_code = 200
        if not raw_data.get("success"):
            status_code = 500

        return JSONResponse(
            content=raw_data,
            status_code=status_code,
        )


@router.post(
    "/record/{chat_record_id}/{action_type}",
    response_model=None,
    summary=f"{PLACEHOLDER_PREFIX}analysis_or_predict",
)
async def analysis_or_predict_question(
    session: SessionDep,
    current_user: CurrentUser,
    current_assistant: CurrentAssistant,
    chat_record_id: int,
    action_type: str = Path(
        ..., description=f"{PLACEHOLDER_PREFIX}analysis_or_predict_action_type"
    ),
) -> StreamingResponse | JSONResponse:
    return await analysis_or_predict(
        session, current_user, chat_record_id, action_type, current_assistant
    )


async def analysis_or_predict(
    session: SessionDep,
    current_user: CurrentUser,
    chat_record_id: int,
    action_type: str,
    current_assistant: CurrentAssistant,
    in_chat: bool = True,
    stream: bool = True,
) -> StreamingResponse | JSONResponse:
    try:
        if action_type != "analysis" and action_type != "predict":
            raise Exception(f"Type {action_type} Not Found")
        record = session.get(ChatRecord, chat_record_id)

        if not record:
            raise Exception(f"Chat record with id {chat_record_id} not found")

        if not record.chart:
            raise Exception(
                f"Chat record with id {chat_record_id} has not generated chart, do not support to analyze it"
            )

        request_question = ChatQuestion(
            chat_id=record.chat_id, question=record.question
        )

        llm_service = await cast(Any, _get_llm_service_class()).create(
            session, current_user, request_question, current_assistant
        )
        llm_service.run_analysis_or_predict_task_async(
            session, action_type, record, in_chat, stream
        )
    except Exception as e:
        traceback.print_exc()
        if stream:

            def _err(_e: Exception) -> Iterator[str]:
                if in_chat:
                    yield (
                        "data:"
                        + orjson.dumps({"content": str(_e), "type": "error"}).decode()
                        + "\n\n"
                    )
                else:
                    yield "&#x274c; **ERROR:**\n"
                    yield f"> {str(_e)}\n"

            return StreamingResponse(_err(e), media_type="text/event-stream")
        else:
            return JSONResponse(
                content={"message": str(e)},
                status_code=500,
            )
    if stream:
        return StreamingResponse(
            llm_service.await_result(), media_type="text/event-stream"
        )
    else:
        res = llm_service.await_result()
        raw_data: dict[str, Any] = {}
        for chunk in res:
            if isinstance(chunk, dict):
                raw_data = chunk
        status_code = 200
        if not raw_data.get("success"):
            status_code = 500

        return JSONResponse(
            content=raw_data,
            status_code=status_code,
        )


@router.get(
    "/record/{chat_record_id}/excel/export/{chat_id}",
    summary=f"{PLACEHOLDER_PREFIX}export_chart_data",
)
@system_log(
    LogConfig(
        operation_type=OperationType.EXPORT,
        module=OperationModules.CHAT,
        resource_id_expr="chat_id",
    )
)
async def export_excel(
    session: SessionDep,
    current_user: CurrentUser,
    chat_record_id: int,
    chat_id: int,
    trans: Trans,
) -> StreamingResponse:
    _ = chat_id
    chat_record = session.get(ChatRecord, chat_record_id)
    if not chat_record:
        raise HTTPException(
            status_code=500, detail=f"ChatRecord with id {chat_record_id} not found"
        )
    if chat_record.create_by != current_user.id:
        raise HTTPException(
            status_code=500,
            detail=f"ChatRecord with id {chat_record_id} not Owned by the current user",
        )
    is_predict_data = chat_record.predict_record_id is not None

    _origin_data = format_json_data(
        get_chat_chart_data(chat_record_id=chat_record_id, session=session)
    )

    _base_field = _origin_data.get("fields")
    _data = _origin_data.get("data")
    base_data = (
        [item for item in _data if isinstance(item, dict)]
        if isinstance(_data, list)
        else []
    )

    if not _data:
        raise HTTPException(
            status_code=500, detail=trans("i18n_excel_export.data_is_empty")
        )

    chart_info = get_chart_config(session, chat_record_id)

    _title = chart_info.get("title") if chart_info.get("title") else "Excel"

    fields: list[AxisObj] = []
    columns = chart_info.get("columns")
    if isinstance(columns, list):
        for column in columns:
            if isinstance(column, dict):
                fields.append(
                    AxisObj(
                        name=str(column.get("name") or ""),
                        value=str(column.get("value") or ""),
                    )
                )
    # 处理 axis
    if axis := chart_info.get("axis"):
        # 处理 x 轴
        if (
            isinstance(axis, dict)
            and (x_axis := axis.get("x"))
            and isinstance(x_axis, dict)
        ):
            if "name" in x_axis or "value" in x_axis:
                fields.append(
                    AxisObj(
                        name=str(x_axis.get("name") or ""),
                        value=str(x_axis.get("value") or ""),
                    )
                )

        # 处理 y 轴 - 兼容数组和对象格式
        if isinstance(axis, dict) and (y_axis := axis.get("y")):
            if isinstance(y_axis, list):
                for column in y_axis:
                    if isinstance(column, dict) and (
                        "name" in column or "value" in column
                    ):
                        fields.append(
                            AxisObj(
                                name=str(column.get("name") or ""),
                                value=str(column.get("value") or ""),
                            )
                        )
            elif isinstance(y_axis, dict) and ("name" in y_axis or "value" in y_axis):
                fields.append(
                    AxisObj(
                        name=str(y_axis.get("name") or ""),
                        value=str(y_axis.get("value") or ""),
                    )
                )

        # 处理 series
        if (
            isinstance(axis, dict)
            and (series := axis.get("series"))
            and isinstance(series, dict)
        ):
            if "name" in series or "value" in series:
                fields.append(
                    AxisObj(
                        name=str(series.get("name") or ""),
                        value=str(series.get("value") or ""),
                    )
                )

    _predict_data = []
    if is_predict_data:
        predict_payload = get_chat_predict_data(
            chat_record_id=chat_record_id, session=session
        )
        predict_rows = predict_payload.get("data")
        predict_list = (
            [item for item in predict_rows if isinstance(item, dict)]
            if isinstance(predict_rows, list)
            else []
        )
        _predict_data = format_json_list_data(predict_list)

    def inner() -> io.BytesIO:
        data_list = DataFormat.convert_large_numbers_in_object_array(
            obj_array=base_data + _predict_data, int_threshold=1e11
        )

        md_data, _fields_list = DataFormat.convert_object_array_for_pandas(
            fields, data_list
        )

        # data, _fields_list, col_formats = LLMService.format_pd_data(fields, _data + _predict_data)

        df = pd.DataFrame(md_data, columns=_fields_list)

        buffer = io.BytesIO()

        with pd.ExcelWriter(
            buffer,
            engine="xlsxwriter",
            engine_kwargs={"options": {"strings_to_numbers": False}},
        ) as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)

            # 获取 xlsxwriter 的工作簿和工作表对象
            # workbook = writer.book
            # worksheet = writer.sheets['Sheet1']
            #
            # for col_idx, fmt_type in col_formats.items():
            #     if fmt_type == 'text':
            #         worksheet.set_column(col_idx, col_idx, None, workbook.add_format({'num_format': '@'}))
            #     elif fmt_type == 'number':
            #         worksheet.set_column(col_idx, col_idx, None, workbook.add_format({'num_format': '0'}))

        buffer.seek(0)
        return io.BytesIO(buffer.getvalue())

    result: io.BytesIO = await asyncio.to_thread(inner)
    return StreamingResponse(
        result,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
