import asyncio
import io
import tempfile
import traceback
from importlib import import_module
from typing import Any, cast

import pandas as pd
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse
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
    RenameChat,
)
from apps.chat.orchestration import (
    AnalysisRecordRequest,
    ChatExecutionRequest,
    ChatOrchestrator,
    QuestionAnswerRequest,
    RecommendQuestionsRequest,
)
from apps.chat.orchestration.coordinator import empty_recommended_questions_response
from apps.chat.streaming import iter_error_events
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.audit.models.log_model import OperationModules, OperationType
from common.audit.schemas.logger_decorator import LogConfig, system_log
from common.core.deps import CurrentAssistant, CurrentUser, SessionDep, Trans
from common.utils.data_format import DataFormat

router = APIRouter(tags=["Data Q&A"], prefix="/chat")


def _get_llm_service_class() -> type[Any]:
    module = import_module("apps.chat.task.llm")
    return cast(type[Any], module.LLMService)


def _get_chat_orchestrator() -> ChatOrchestrator:
    return ChatOrchestrator(_get_llm_service_class())


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
    try:
        record = get_chat_record_by_id(session, chat_record_id)

        if not record:
            return empty_recommended_questions_response()

        request_question = ChatQuestion(
            chat_id=record.chat_id, question=record.question if record.question else ""
        )
        return await _get_chat_orchestrator().start_recommend_questions(
            RecommendQuestionsRequest(
                session=session,
                current_user=current_user,
                request_question=request_question,
                record=record,
                current_assistant=current_assistant,
                articles_number=articles_number,
            )
        )
    except Exception as e:
        traceback.print_exc()
        return StreamingResponse(
            iter_error_events(str(e)), media_type="text/event-stream"
        )


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
        return await _get_chat_orchestrator().answer_question(
            QuestionAnswerRequest(
                session=session,
                current_user=current_user,
                request_question=request_question,
                current_assistant=current_assistant,
                in_chat=in_chat,
                stream=stream,
                finish_step=finish_step,
                embedding=embedding,
            )
        )
    except Exception as e:
        traceback.print_exc()

        if stream:
            return StreamingResponse(
                iter_error_events(str(e), in_chat=in_chat),
                media_type="text/event-stream",
            )
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
    return await _get_chat_orchestrator().start_chat(
        ChatExecutionRequest(
            session=session,
            current_user=current_user,
            request_question=request_question,
            current_assistant=current_assistant,
            in_chat=in_chat,
            stream=stream,
            finish_step=finish_step,
            embedding=embedding,
        )
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
        return await _get_chat_orchestrator().start_analysis_or_predict_by_record(
            AnalysisRecordRequest(
                session=session,
                current_user=current_user,
                chat_record_id=chat_record_id,
                action_type=action_type,
                current_assistant=current_assistant,
                in_chat=in_chat,
                stream=stream,
            )
        )
    except Exception as e:
        traceback.print_exc()
        if stream:
            return StreamingResponse(
                iter_error_events(str(e), in_chat=in_chat),
                media_type="text/event-stream",
            )
        else:
            return JSONResponse(
                content={"message": str(e)},
                status_code=500,
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

        df = pd.DataFrame(md_data, columns=pd.Index(_fields_list))

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            with pd.ExcelWriter(
                temp_file.name,
                engine="xlsxwriter",
                engine_kwargs={"options": {"strings_to_numbers": False}},
            ) as writer:
                df.to_excel(writer, sheet_name="Sheet1", index=False)

            with open(temp_file.name, "rb") as file_obj:
                return io.BytesIO(file_obj.read())

    result: io.BytesIO = await asyncio.to_thread(inner)
    return StreamingResponse(
        result,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
