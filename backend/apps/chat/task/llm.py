import concurrent.futures
import json
import os
import traceback
import urllib.parse
import warnings
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from importlib import import_module
from typing import TYPE_CHECKING, Any, Protocol, cast

import httpx
import orjson
import pandas as pd
import sqlparse
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    BaseMessageChunk,
    HumanMessage,
    SystemMessage,
)
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session
from sqlmodel import select as sqlmodel_select

from apps.ai_model.model_factory import LLMConfig, LLMFactory, get_default_config
from apps.chat.curd.chat import (
    end_log,
    finish_record,
    format_chart_fields,
    format_json_data,
    get_chart_config,
    get_chat_brief_generate,
    get_chat_chart_config,
    get_chat_chart_data,
    get_chat_predict_data,
    get_last_execute_sql_error,
    get_old_questions,
    list_generate_chart_logs,
    list_generate_sql_logs,
    rename_chat,
    save_analysis_answer,
    save_analysis_predict_record,
    save_chart,
    save_chart_answer,
    save_error_message,
    save_predict_answer,
    save_predict_data,
    save_question,
    save_recommend_question_answer,
    save_select_datasource_answer,
    save_sql,
    save_sql_answer,
    save_sql_exec_data,
    start_log,
    trigger_log_error,
)
from apps.chat.models.chat_model import (
    AxisObj,
    Chat,
    ChatFinishStep,
    ChatLog,
    ChatQuestion,
    ChatRecord,
    OperationEnum,
    RenameChat,
)
from apps.data_training.curd.data_training import get_training_template
from apps.datasource.crud.datasource import get_table_schema
from apps.datasource.crud.permission import get_row_permission_filters, is_normal_user
from apps.datasource.embedding.ds_embedding import get_ds_embedding
from apps.datasource.models.datasource import CoreDatasource
from apps.db.db import check_connection, exec_sql, get_version
from apps.system.crud.assistant import (
    AssistantOutDs,
    AssistantOutDsFactory,
    get_assistant_ds,
)
from apps.system.crud.parameter_manage import get_groups
from apps.system.schemas.system_schema import AssistantOutDsSchema
from apps.terminology.curd.terminology import get_terminology_template
from common.core.config import settings
from common.core.db import engine
from common.core.deps import CurrentAssistant, CurrentUser
from common.error import (
    ParseSQLResultError,
    SingleMessageError,
    SQLBotDBConnectionError,
    SQLBotDBError,
)
from common.utils.data_format import DataFormat
from common.utils.locale import I18n, I18nHelper
from common.utils.utils import SQLBotLogUtil, extract_nested_json, prepare_for_orjson

if TYPE_CHECKING:
    from langchain.chat_models.base import BaseChatModel
else:
    BaseChatModel = Any

warnings.filterwarnings("ignore")

executor = ThreadPoolExecutor(max_workers=200)

dynamic_ds_types = [1, 3]
dynamic_subsql_prefix = "select * from sqlbot_dynamic_temp_table_"

session_maker = scoped_session(sessionmaker(bind=engine, class_=Session))

i18n = I18n()


class _LicenseUtilProtocol(Protocol):
    @staticmethod
    def valid() -> object: ...


class _LicenseModuleProtocol(Protocol):
    SQLBotLicenseUtil: type[_LicenseUtilProtocol]


class _CustomPromptModuleProtocol(Protocol):
    @staticmethod
    def find_custom_prompts(
        session: Session,
        custom_prompt_type: object,
        oid: int | None,
        ds_id: int | None,
    ) -> tuple[str, list[dict[str, object]]]: ...


class _CustomPromptEnumModuleProtocol(Protocol):
    CustomPromptTypeEnum: type[object]


class _ChatParamProtocol(Protocol):
    pkey: str
    pval: object


ChatMessagePayload = dict[str, object]
ObjectDict = dict[str, object]
TokenUsage = dict[str, object]
StreamOutput = str | ObjectDict


def _as_object_dict(value: object) -> ObjectDict | None:
    return cast(ObjectDict, value) if isinstance(value, dict) else None


def _as_object_dict_list(value: object) -> list[ObjectDict]:
    if not isinstance(value, list):
        return []
    value_list = cast(list[object], value)
    items: list[ObjectDict] = []
    for item in value_list:
        if isinstance(item, dict):
            items.append(cast(ObjectDict, item))
    return items


def _get_str(mapping: ObjectDict, key: str) -> str | None:
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _lowercase_mapping_value(mapping: ObjectDict, key: str) -> None:
    value = _get_str(mapping, key)
    if value is not None:
        mapping[key] = value.lower()


def _get_bool(mapping: ObjectDict, key: str) -> bool | None:
    value = mapping.get(key)
    return value if isinstance(value, bool) else None


def _parse_json_object(raw_json: str) -> ObjectDict | None:
    parsed = cast(object, orjson.loads(raw_json))
    return _as_object_dict(parsed)


def _get_string_list(mapping: ObjectDict, key: str) -> list[str] | None:
    value = mapping.get(key)
    if not isinstance(value, list):
        return None
    value_list = cast(list[object], value)
    items: list[str] = []
    for item in value_list:
        if isinstance(item, str):
            items.append(item)
    return items


def _get_object_dict_list(mapping: ObjectDict, key: str) -> list[ObjectDict] | None:
    value = mapping.get(key)
    if not isinstance(value, list):
        return None
    return _as_object_dict_list(cast(object, value))


def _as_object_list(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return cast(list[object], value)


def _stream_chunk(content: str, reasoning_content: str) -> ObjectDict:
    return cast(
        ObjectDict, {"content": content, "reasoning_content": reasoning_content}
    )


def _chunk_part_to_text(part: object) -> str:
    return part if isinstance(part, str) else str(part)


def _chunk_content_text_from_message(chunk: BaseMessageChunk) -> str:
    content_raw = cast(object, chunk.content)
    if isinstance(content_raw, str):
        return content_raw
    if isinstance(content_raw, list):
        content_list = _as_object_list(cast(object, content_raw))
        return "".join(_chunk_part_to_text(part) for part in content_list)
    return ""


def _chunk_additional_kwargs(chunk: BaseMessageChunk) -> ObjectDict:
    return _as_object_dict(cast(object, chunk.additional_kwargs)) or {}


def _mapping_value(mapping: ObjectDict, key: str) -> object | None:
    return mapping.get(key)


def _message_log_payload(msg: BaseMessage) -> ObjectDict:
    return {"type": msg.type, "content": cast(object, msg.content)}


def _message_log_payloads(messages: list[BaseMessage]) -> list[ObjectDict]:
    return [_message_log_payload(msg) for msg in messages]


def _chunk_content_text(chunk: ObjectDict) -> str:
    return _get_str(chunk, "content") or ""


def _chunk_reasoning_text(chunk: ObjectDict) -> str:
    return _get_str(chunk, "reasoning_content") or ""


def _is_license_valid() -> bool:
    module = cast(
        _LicenseModuleProtocol,
        import_module("sqlbot_xpack.license.license_manage"),
    )
    return bool(module.SQLBotLicenseUtil.valid())


def _find_custom_prompts(
    session: Session,
    custom_prompt_type: object,
    oid: int | None,
    ds_id: int | None,
) -> tuple[str, list[dict[str, object]]]:
    module = cast(
        _CustomPromptModuleProtocol,
        import_module("sqlbot_xpack.custom_prompt.curd.custom_prompt"),
    )
    return module.find_custom_prompts(session, custom_prompt_type, oid, ds_id)


def _custom_prompt_type(enum_name: str) -> object:
    module = cast(
        _CustomPromptEnumModuleProtocol,
        import_module("sqlbot_xpack.custom_prompt.models.custom_prompt_model"),
    )
    enum_cls = module.CustomPromptTypeEnum
    return cast(object, getattr(enum_cls, enum_name))


class LLMService:
    ds: CoreDatasource | AssistantOutDsSchema | None
    ds_core_id: int | None
    chat_question: ChatQuestion
    config: LLMConfig
    llm: BaseChatModel
    sql_message: list[BaseMessage]
    chart_message: list[BaseMessage]

    # session: Session = db_session
    current_user: CurrentUser
    current_assistant: CurrentAssistant | None = None
    out_ds_instance: AssistantOutDs | None = None
    change_title: bool = False

    generate_sql_logs: list[ChatLog]
    generate_chart_logs: list[ChatLog]
    current_logs: dict[OperationEnum, ChatLog]
    chunk_list: list[str | dict[str, object]]

    trans: I18nHelper

    last_execute_sql_error: str | None = None
    articles_number: int = 4

    enable_sql_row_limit: bool = settings.GENERATE_SQL_QUERY_LIMIT_ENABLED
    base_message_round_count_limit: int = (
        settings.GENERATE_SQL_QUERY_HISTORY_ROUND_COUNT
    )

    def __init__(
        self,
        session: Session,
        current_user: CurrentUser,
        chat_question: ChatQuestion,
        current_assistant: CurrentAssistant | None = None,
        no_reasoning: bool = False,
        embedding: bool = False,
        config: LLMConfig | None = None,
    ):
        self.sql_message = []
        self.chart_message = []
        self.generate_sql_logs = []
        self.generate_chart_logs = []
        self.current_logs = {}
        self.chunk_list = []
        self.current_user = current_user
        self.current_assistant = current_assistant
        self.record: ChatRecord = ChatRecord.model_construct()
        self.future: Future[None] = Future()
        self.future.set_result(None)
        self.ds_core_id = None
        chat_id = chat_question.chat_id
        chat: Chat | None = session.get(Chat, chat_id)
        if not chat:
            raise SingleMessageError(f"Chat with id {chat_id} not found")
        ds: CoreDatasource | AssistantOutDsSchema | None = None
        if not chat.datasource and chat_question.datasource_id:
            _ds = session.get(CoreDatasource, chat_question.datasource_id)
            if _ds:
                if _ds.oid != current_user.oid:
                    raise SingleMessageError(
                        f"Datasource with id {chat_question.datasource_id} does not belong to current workspace"
                    )
                chat.datasource = _ds.id
                chat.engine_type = _ds.type_name
                # save chat
                session.add(chat)
                session.flush()
                session.refresh(chat)
                session.commit()

        if chat.datasource:
            # Get available datasource
            if current_assistant and current_assistant.type in dynamic_ds_types:
                self.out_ds_instance = AssistantOutDsFactory.get_instance(
                    current_assistant
                )
                ds = self.out_ds_instance.get_ds(chat.datasource)
                chat_question.engine = (ds.type or "") + get_version(ds)
            else:
                ds = session.get(CoreDatasource, chat.datasource)
                if not ds:
                    raise SingleMessageError(
                        "No available datasource configuration found"
                    )
                chat_question.engine = (
                    ds.type_name if ds.type != "excel" else "PostgreSQL"
                ) + get_version(ds)

        self.generate_sql_logs = list_generate_sql_logs(
            session=session, chart_id=chat_id
        )
        self.generate_chart_logs = list_generate_chart_logs(
            session=session, chart_id=chat_id
        )

        self.change_title = not get_chat_brief_generate(
            session=session, chat_id=chat_id
        )

        chat_question.lang = get_lang_name(current_user.language)
        self.trans = i18n(lang=current_user.language)

        self._set_datasource(ds)
        self.chat_question = chat_question
        if config is None:
            raise SingleMessageError("No available model configuration found")
        self.config = config
        if no_reasoning:
            # only work while using qwen
            if self.config.additional_params:
                additional_params = cast(object, self.config.additional_params)
                additional_params_dict = _as_object_dict(additional_params)
                extra_body = (
                    _as_object_dict(additional_params_dict.get("extra_body"))
                    if additional_params_dict is not None
                    else None
                )
                if extra_body is not None and _get_bool(extra_body, "enable_thinking"):
                    del extra_body["enable_thinking"]

        self.chat_question.ai_modal_id = self.config.model_id
        self.chat_question.ai_modal_name = self.config.model_name

        # Create LLM instance through factory
        llm_instance = LLMFactory.create_llm(self.config)
        self.llm = llm_instance.llm

        # get last_execute_sql_error
        last_execute_sql_error = get_last_execute_sql_error(
            session, self.chat_question.chat_id
        )
        if last_execute_sql_error:
            self.chat_question.error_msg = f"""<error-msg>
{last_execute_sql_error}
</error-msg>"""
        else:
            self.chat_question.error_msg = ""

    @classmethod
    async def create(
        cls,
        session: Session,
        current_user: CurrentUser,
        chat_question: ChatQuestion,
        current_assistant: CurrentAssistant | None = None,
        no_reasoning: bool = False,
        embedding: bool = False,
        config: LLMConfig | None = None,
    ) -> "LLMService":
        resolved_config = config or await get_default_config()
        instance = cls(
            session=session,
            current_user=current_user,
            chat_question=chat_question,
            current_assistant=current_assistant,
            no_reasoning=no_reasoning,
            embedding=embedding,
            config=resolved_config,
        )

        chat_params = cast(list[_ChatParamProtocol], await get_groups(session, "chat"))
        for param in chat_params:
            if param.pkey == "chat.limit_rows":
                pval = param.pval
                if isinstance(pval, str) and pval.lower().strip() == "true":
                    instance.enable_sql_row_limit = True
                else:
                    instance.enable_sql_row_limit = False
            if param.pkey == "chat.context_record_count":
                count_value: int | str | None
                raw_count_value = param.pval
                if isinstance(raw_count_value, (int, str)):
                    count_value = raw_count_value
                else:
                    count_value = None
                if count_value is None:
                    count_value = settings.GENERATE_SQL_QUERY_HISTORY_ROUND_COUNT
                count_value = int(count_value)
                if count_value < 0:
                    count_value = 0
                instance.base_message_round_count_limit = count_value
        return instance

    def _set_datasource(self, ds: CoreDatasource | AssistantOutDsSchema | None) -> None:
        self.ds = ds
        self.ds_core_id = ds.id if isinstance(ds, CoreDatasource) else None

    def _ensure_runtime_datasource(self, _session: Session) -> None:
        if self.ds_core_id is None:
            return
        current_ds = _session.get(CoreDatasource, self.ds_core_id)
        if current_ds is None:
            raise SingleMessageError("No available datasource configuration found")
        self.ds = current_ds

    def is_running(self, timeout: float = 0.5) -> bool:
        try:
            r = concurrent.futures.wait([self.future], timeout)
            if len(r.not_done) > 0:
                return True
            else:
                return False
        except Exception:
            return True

    def init_messages(self, session: Session) -> None:
        self.choose_table_schema(session)

        sql_messages_obj = (
            self.generate_sql_logs[-1].messages if self.generate_sql_logs else None
        )
        last_sql_messages: list[ChatMessagePayload] = (
            sql_messages_obj if isinstance(sql_messages_obj, list) else []
        )
        if self.chat_question.regenerate_record_id:
            # filter record before regenerate_record_id
            _temp_log = next(
                filter(
                    lambda obj: obj.pid == self.chat_question.regenerate_record_id,
                    self.generate_sql_logs,
                ),
                None,
            )
            temp_sql_messages = _temp_log.messages if _temp_log else None
            last_sql_messages = (
                temp_sql_messages if isinstance(temp_sql_messages, list) else []
            )

        count_limit = self.base_message_round_count_limit

        self.sql_message = []
        # add sys prompt
        ds_type = self.ds.type if self.ds and self.ds.type is not None else ""
        self.sql_message.append(
            SystemMessage(
                content=self.chat_question.sql_sys_question(
                    ds_type, self.enable_sql_row_limit
                )
            )
        )
        if last_sql_messages:
            last_rounds = get_last_conversation_rounds(
                last_sql_messages, rounds=count_limit
            )

            for _msg_dict in last_rounds:
                message_type = _msg_dict.get("type")
                if message_type == "human":
                    self.sql_message.append(
                        HumanMessage(content=str(_msg_dict.get("content") or ""))
                    )
                elif message_type == "ai":
                    self.sql_message.append(
                        AIMessage(content=str(_msg_dict.get("content") or ""))
                    )

        chart_messages_obj = (
            self.generate_chart_logs[-1].messages if self.generate_chart_logs else None
        )
        last_chart_messages: list[ChatMessagePayload] = (
            chart_messages_obj if isinstance(chart_messages_obj, list) else []
        )
        if self.chat_question.regenerate_record_id:
            # filter record before regenerate_record_id
            _temp_log = next(
                filter(
                    lambda obj: obj.pid == self.chat_question.regenerate_record_id,
                    self.generate_chart_logs,
                ),
                None,
            )
            temp_chart_messages = _temp_log.messages if _temp_log else None
            last_chart_messages = (
                temp_chart_messages if isinstance(temp_chart_messages, list) else []
            )

        count_chart_limit = self.base_message_round_count_limit

        self.chart_message = []
        # add sys prompt
        self.chart_message.append(
            SystemMessage(content=self.chat_question.chart_sys_question())
        )
        if last_chart_messages:
            last_rounds = get_last_conversation_rounds(
                last_chart_messages, rounds=count_chart_limit
            )

            for _msg_dict in last_rounds:
                message_type = _msg_dict.get("type")
                if message_type == "human":
                    self.chart_message.append(
                        HumanMessage(content=str(_msg_dict.get("content") or ""))
                    )
                elif message_type == "ai":
                    self.chart_message.append(
                        AIMessage(content=str(_msg_dict.get("content") or ""))
                    )

    def init_record(self, session: Session) -> ChatRecord:
        self.record = save_question(
            session=session, current_user=self.current_user, question=self.chat_question
        )
        return self.record

    def get_record(self) -> ChatRecord:
        return self.record

    def set_record(self, record: ChatRecord) -> None:
        self.record = record

    def set_articles_number(self, articles_number: int | None) -> None:
        self.articles_number = articles_number if articles_number is not None else 4

    def get_fields_from_chart(self, _session: Session) -> list[str]:
        if self.record.id is None:
            return []
        chart_info = get_chart_config(_session, self.record.id)
        return format_chart_fields(chart_info)

    def filter_terminology_template(
        self, _session: Session, oid: int | None = None, ds_id: int | None = None
    ) -> None:
        calculate_oid = oid
        calculate_ds_id = ds_id
        if self.current_assistant:
            calculate_oid = (
                self.current_assistant.oid
                if self.current_assistant.type != 4
                else self.current_user.oid
            )
            if self.current_assistant.type == 1:
                calculate_ds_id = None
        self.current_logs[OperationEnum.FILTER_TERMS] = start_log(
            session=_session,
            operate=OperationEnum.FILTER_TERMS,
            record_id=self.record.id,
            local_operation=True,
        )

        question_text = self.chat_question.question or ""
        self.chat_question.terminologies, term_list = get_terminology_template(
            _session, question_text, calculate_oid, calculate_ds_id
        )
        self.current_logs[OperationEnum.FILTER_TERMS] = end_log(
            session=_session,
            log=self.current_logs[OperationEnum.FILTER_TERMS],
            full_message=term_list,
        )

    def filter_custom_prompts(
        self,
        _session: Session,
        custom_prompt_type: object,
        oid: int | None = None,
        ds_id: int | None = None,
    ) -> None:
        if _is_license_valid():
            calculate_oid = oid
            calculate_ds_id = ds_id
            if self.current_assistant:
                calculate_oid = (
                    self.current_assistant.oid
                    if self.current_assistant.type != 4
                    else self.current_user.oid
                )
                if self.current_assistant.type == 1:
                    calculate_ds_id = None
            self.current_logs[OperationEnum.FILTER_CUSTOM_PROMPT] = start_log(
                session=_session,
                operate=OperationEnum.FILTER_CUSTOM_PROMPT,
                record_id=self.record.id,
                local_operation=True,
            )
            self.chat_question.custom_prompt, prompt_list = _find_custom_prompts(
                _session, custom_prompt_type, calculate_oid, calculate_ds_id
            )
            self.current_logs[OperationEnum.FILTER_CUSTOM_PROMPT] = end_log(
                session=_session,
                log=self.current_logs[OperationEnum.FILTER_CUSTOM_PROMPT],
                full_message=prompt_list,
            )

    def filter_training_template(
        self, _session: Session, oid: int | None = None, ds_id: int | None = None
    ) -> None:
        self.current_logs[OperationEnum.FILTER_SQL_EXAMPLE] = start_log(
            session=_session,
            operate=OperationEnum.FILTER_SQL_EXAMPLE,
            record_id=self.record.id,
            local_operation=True,
        )
        calculate_oid = oid
        calculate_ds_id = ds_id
        if self.current_assistant:
            calculate_oid = (
                self.current_assistant.oid
                if self.current_assistant.type != 4
                else self.current_user.oid
            )
            if self.current_assistant.type == 1:
                calculate_ds_id = None
        question_text = self.chat_question.question or ""
        if self.current_assistant and self.current_assistant.type == 1:
            self.chat_question.data_training, example_list = get_training_template(
                _session,
                question_text,
                calculate_oid,
                None,
                self.current_assistant.id,
            )
        else:
            self.chat_question.data_training, example_list = get_training_template(
                _session, question_text, calculate_oid, calculate_ds_id
            )
        self.current_logs[OperationEnum.FILTER_SQL_EXAMPLE] = end_log(
            session=_session,
            log=self.current_logs[OperationEnum.FILTER_SQL_EXAMPLE],
            full_message=example_list,
        )

    def choose_table_schema(self, _session: Session) -> None:
        self.current_logs[OperationEnum.CHOOSE_TABLE] = start_log(
            session=_session,
            operate=OperationEnum.CHOOSE_TABLE,
            record_id=self.record.id,
            local_operation=True,
        )
        question_text = self.chat_question.question or ""
        if self.out_ds_instance:
            ds_id = self.ds.id if self.ds and self.ds.id is not None else 0
            self.chat_question.db_schema = self.out_ds_instance.get_db_schema(
                ds_id, question_text
            )
        else:
            if not isinstance(self.ds, CoreDatasource):
                raise SingleMessageError("No available datasource configuration found")
            self.chat_question.db_schema = get_table_schema(
                session=_session,
                current_user=self.current_user,
                ds=self.ds,
                question=question_text,
            )

        self.current_logs[OperationEnum.CHOOSE_TABLE] = end_log(
            session=_session,
            log=self.current_logs[OperationEnum.CHOOSE_TABLE],
            full_message={"db_schema": self.chat_question.db_schema},
        )

    def generate_analysis(self, _session: Session) -> Iterator[ObjectDict]:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        record_id = self.record.id
        fields = self.get_fields_from_chart(_session)
        self.chat_question.fields = orjson.dumps(fields).decode()
        data = get_chat_chart_data(_session, record_id)
        self.chat_question.data = orjson.dumps(data.get("data")).decode()
        analysis_msg: list[BaseMessage] = []

        ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None

        self.filter_terminology_template(_session, self.current_user.oid, ds_id)

        self.filter_custom_prompts(
            _session,
            _custom_prompt_type("ANALYSIS"),
            self.current_user.oid,
            ds_id,
        )

        analysis_msg.append(
            SystemMessage(content=self.chat_question.analysis_sys_question())
        )
        analysis_msg.append(
            HumanMessage(content=self.chat_question.analysis_user_question())
        )

        self.current_logs[OperationEnum.ANALYSIS] = start_log(
            session=_session,
            ai_modal_id=self.chat_question.ai_modal_id,
            ai_modal_name=self.chat_question.ai_modal_name,
            operate=OperationEnum.ANALYSIS,
            record_id=record_id,
            full_message=_message_log_payloads(analysis_msg),
        )
        full_thinking_text = ""
        full_analysis_text = ""
        token_usage: TokenUsage = {}
        res = process_stream(self.llm.stream(analysis_msg), token_usage)
        for chunk in res:
            full_analysis_text += _chunk_content_text(chunk)
            full_thinking_text += _chunk_reasoning_text(chunk)
            yield chunk

        analysis_msg.append(AIMessage(full_analysis_text))

        self.current_logs[OperationEnum.ANALYSIS] = end_log(
            session=_session,
            log=self.current_logs[OperationEnum.ANALYSIS],
            full_message=_message_log_payloads(analysis_msg),
            reasoning_content=full_thinking_text,
            token_usage=token_usage,
        )
        self.record = save_analysis_answer(
            session=_session,
            record_id=record_id,
            answer=orjson.dumps({"content": full_analysis_text}).decode(),
        )

    def generate_predict(self, _session: Session) -> Iterator[ObjectDict]:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        record_id = self.record.id
        fields = self.get_fields_from_chart(_session)
        self.chat_question.fields = orjson.dumps(fields).decode()
        data = get_chat_chart_data(_session, record_id)
        self.chat_question.data = orjson.dumps(data.get("data")).decode()

        ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None
        self.filter_custom_prompts(
            _session,
            _custom_prompt_type("PREDICT_DATA"),
            self.current_user.oid,
            ds_id,
        )

        predict_msg: list[BaseMessage] = []
        predict_msg.append(
            SystemMessage(content=self.chat_question.predict_sys_question())
        )
        predict_msg.append(
            HumanMessage(content=self.chat_question.predict_user_question())
        )

        self.current_logs[OperationEnum.PREDICT_DATA] = start_log(
            session=_session,
            ai_modal_id=self.chat_question.ai_modal_id,
            ai_modal_name=self.chat_question.ai_modal_name,
            operate=OperationEnum.PREDICT_DATA,
            record_id=record_id,
            full_message=_message_log_payloads(predict_msg),
        )
        full_thinking_text = ""
        full_predict_text = ""
        token_usage: TokenUsage = {}
        res = process_stream(self.llm.stream(predict_msg), token_usage)
        for chunk in res:
            full_predict_text += _chunk_content_text(chunk)
            full_thinking_text += _chunk_reasoning_text(chunk)
            yield chunk

        predict_msg.append(AIMessage(full_predict_text))
        self.record = save_predict_answer(
            session=_session,
            record_id=record_id,
            answer=orjson.dumps({"content": full_predict_text}).decode(),
        )
        self.current_logs[OperationEnum.PREDICT_DATA] = end_log(
            session=_session,
            log=self.current_logs[OperationEnum.PREDICT_DATA],
            full_message=_message_log_payloads(predict_msg),
            reasoning_content=full_thinking_text,
            token_usage=token_usage,
        )

    def generate_recommend_questions_task(
        self, _session: Session
    ) -> Iterator[ObjectDict]:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        record_id = self.record.id
        # get schema
        if self.ds and not self.chat_question.db_schema:
            question_text = self.chat_question.question or ""
            self.chat_question.db_schema = (
                self.out_ds_instance.get_db_schema(self.ds.id or 0, question_text)
                if self.out_ds_instance
                else get_table_schema(
                    session=_session,
                    current_user=self.current_user,
                    ds=cast(CoreDatasource, self.ds),
                    question=question_text,
                    embedding=False,
                )
            )

        guess_msg: list[BaseMessage] = []
        guess_msg.append(
            SystemMessage(
                content=self.chat_question.guess_sys_question(self.articles_number)
            )
        )

        old_questions = [
            question.strip()
            for question in get_old_questions(_session, self.record.datasource)
        ]
        guess_msg.append(
            HumanMessage(
                content=self.chat_question.guess_user_question(
                    orjson.dumps(old_questions).decode()
                )
            )
        )

        self.current_logs[OperationEnum.GENERATE_RECOMMENDED_QUESTIONS] = start_log(
            session=_session,
            ai_modal_id=self.chat_question.ai_modal_id,
            ai_modal_name=self.chat_question.ai_modal_name,
            operate=OperationEnum.GENERATE_RECOMMENDED_QUESTIONS,
            record_id=record_id,
            full_message=_message_log_payloads(guess_msg),
        )
        full_thinking_text = ""
        full_guess_text = ""
        token_usage: TokenUsage = {}
        res = process_stream(self.llm.stream(guess_msg), token_usage)
        for chunk in res:
            full_guess_text += _chunk_content_text(chunk)
            full_thinking_text += _chunk_reasoning_text(chunk)
            yield chunk

        guess_msg.append(AIMessage(full_guess_text))

        self.current_logs[OperationEnum.GENERATE_RECOMMENDED_QUESTIONS] = end_log(
            session=_session,
            log=self.current_logs[OperationEnum.GENERATE_RECOMMENDED_QUESTIONS],
            full_message=_message_log_payloads(guess_msg),
            reasoning_content=full_thinking_text,
            token_usage=token_usage,
        )
        self.record = save_recommend_question_answer(
            session=_session,
            record_id=record_id,
            answer={"content": full_guess_text},
            articles_number=self.articles_number,
        )

        yield {"recommended_question": self.record.recommended_question}

    def select_datasource(self, _session: Session) -> Iterator[ObjectDict]:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        record_id = self.record.id
        datasource_msg: list[BaseMessage] = []
        datasource_msg.append(
            SystemMessage(self.chat_question.datasource_sys_question())
        )
        if self.current_assistant and self.current_assistant.type != 4:
            _ds_list = get_assistant_ds(session=_session, llm_service=self)
        else:
            stmt = sqlmodel_select(
                CoreDatasource.id,
                CoreDatasource.name,
                CoreDatasource.description,
            ).where(CoreDatasource.oid == self.current_user.oid)
            _ds_list = [
                {"id": ds_id, "name": ds_name, "description": ds_description}
                for ds_id, ds_name, ds_description in _session.exec(stmt).all()
            ]
        if not _ds_list:
            raise SingleMessageError("No available datasource configuration found")
        ignore_auto_select = _ds_list and len(_ds_list) == 1
        # ignore auto select ds

        full_thinking_text = ""
        full_text = ""
        ds: ObjectDict = {}
        if not ignore_auto_select:
            _ds_list_dict: list[ObjectDict] = []
            if settings.TABLE_EMBEDDING_ENABLED and (
                not self.current_assistant
                or (self.current_assistant and self.current_assistant.type != 1)
            ):
                _ds_list = get_ds_embedding(
                    _session,
                    self.current_user,
                    _ds_list,
                    cast(AssistantOutDs, self.out_ds_instance),
                    self.chat_question.question or "",
                    self.current_assistant,
                )
                # yield {'content': '{"id":' + str(ds.get('id')) + '}'}

            for ds_item in _ds_list:
                _ds_list_dict.append(ds_item)
            datasource_msg.append(
                HumanMessage(
                    self.chat_question.datasource_user_question(
                        orjson.dumps(_ds_list_dict).decode()
                    )
                )
            )

            self.current_logs[OperationEnum.CHOOSE_DATASOURCE] = start_log(
                session=_session,
                ai_modal_id=self.chat_question.ai_modal_id,
                ai_modal_name=self.chat_question.ai_modal_name,
                operate=OperationEnum.CHOOSE_DATASOURCE,
                record_id=record_id,
                full_message=_message_log_payloads(datasource_msg),
            )

            token_usage: TokenUsage = {}
            res = process_stream(self.llm.stream(datasource_msg), token_usage)
            for chunk in res:
                full_text += _chunk_content_text(chunk)
                full_thinking_text += _chunk_reasoning_text(chunk)
                yield chunk
            datasource_msg.append(AIMessage(full_text))

            self.current_logs[OperationEnum.CHOOSE_DATASOURCE] = end_log(
                session=_session,
                log=self.current_logs[OperationEnum.CHOOSE_DATASOURCE],
                full_message=_message_log_payloads(datasource_msg),
                reasoning_content=full_thinking_text,
                token_usage=token_usage,
            )

            json_str = extract_nested_json(full_text)
            if json_str is None:
                raise SingleMessageError(
                    f"Cannot parse datasource from answer: {full_text}"
                )
            parsed_ds = _parse_json_object(json_str)
            ds = parsed_ds or {}

        _error: Exception | None = None
        _datasource: int | None = None
        _engine_type: str | None = None
        try:
            data = _ds_list[0] if ignore_auto_select else ds
            data_id_raw = data.get("id")
            data_id: int | None = None
            if isinstance(data_id_raw, int):
                data_id = data_id_raw
            elif isinstance(data_id_raw, str):
                try:
                    data_id = int(data_id_raw)
                except ValueError:
                    data_id = None

            if data_id and data_id != 0:
                _datasource = data_id
                _chat = _session.get(Chat, self.record.chat_id)
                if _chat is None:
                    raise SingleMessageError("Chat not found")
                _chat.datasource = _datasource
                if (
                    self.current_assistant
                    and self.current_assistant.type in dynamic_ds_types
                ):
                    if self.out_ds_instance is None:
                        raise SingleMessageError(
                            "No available datasource configuration found"
                        )
                    out_ds_schema = self.out_ds_instance.get_ds(data_id)
                    self._set_datasource(out_ds_schema)
                    ds_type = out_ds_schema.type or ""
                    self.chat_question.engine = ds_type + get_version(out_ds_schema)

                    _engine_type = self.chat_question.engine
                    _chat.engine_type = ds_type
                else:
                    db_ds = _session.get(CoreDatasource, _datasource)
                    if not db_ds:
                        raise SingleMessageError(
                            f"Datasource configuration with id {_datasource} not found"
                        )
                    self._set_datasource(db_ds)
                    self.chat_question.engine = (
                        db_ds.type_name if db_ds.type != "excel" else "PostgreSQL"
                    ) + get_version(db_ds)

                    _engine_type = self.chat_question.engine
                    _chat.engine_type = db_ds.type_name or ""
                # save chat
                with _session.begin_nested():
                    # 为了能继续记日志，先单独处理下事务
                    try:
                        _session.add(_chat)
                        _session.flush()
                        _session.refresh(_chat)
                        _session.commit()
                    except Exception as e:
                        _session.rollback()
                        raise e

            elif isinstance(data.get("fail"), str) and data.get("fail"):
                raise SingleMessageError(str(data.get("fail")))
            else:
                raise SingleMessageError("No available datasource configuration found")

        except Exception as e:
            _error = e

        if not ignore_auto_select and not settings.TABLE_EMBEDDING_ENABLED:
            self.record = save_select_datasource_answer(
                session=_session,
                record_id=record_id,
                answer=orjson.dumps({"content": full_text}).decode(),
                datasource=_datasource,
                engine_type=_engine_type,
            )
        if self.ds:
            oid = self.ds.oid if isinstance(self.ds, CoreDatasource) else 1
            ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None

            self.filter_terminology_template(_session, oid, ds_id)

            self.filter_training_template(_session, oid, ds_id)

            self.filter_custom_prompts(
                _session, _custom_prompt_type("GENERATE_SQL"), oid, ds_id
            )

            self.init_messages(_session)

        if _error:
            raise _error

    def generate_sql(self, _session: Session) -> Iterator[ObjectDict]:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        record_id = self.record.id
        # append current question
        self.sql_message.append(
            HumanMessage(
                self.chat_question.sql_user_question(
                    current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    change_title=self.change_title,
                )
            )
        )

        self.current_logs[OperationEnum.GENERATE_SQL] = start_log(
            session=_session,
            ai_modal_id=self.chat_question.ai_modal_id,
            ai_modal_name=self.chat_question.ai_modal_name,
            operate=OperationEnum.GENERATE_SQL,
            record_id=record_id,
            full_message=_message_log_payloads(self.sql_message),
        )
        full_thinking_text = ""
        full_sql_text = ""
        token_usage: TokenUsage = {}
        res = process_stream(self.llm.stream(self.sql_message), token_usage)
        for chunk in res:
            full_sql_text += _chunk_content_text(chunk)
            full_thinking_text += _chunk_reasoning_text(chunk)
            yield chunk

        self.sql_message.append(AIMessage(full_sql_text))

        self.current_logs[OperationEnum.GENERATE_SQL] = end_log(
            session=_session,
            log=self.current_logs[OperationEnum.GENERATE_SQL],
            full_message=_message_log_payloads(self.sql_message),
            reasoning_content=full_thinking_text,
            token_usage=token_usage,
        )
        self.record = save_sql_answer(
            session=_session,
            record_id=record_id,
            answer=orjson.dumps({"content": full_sql_text}).decode(),
        )

    def generate_with_sub_sql(
        self, session: Session, sql: str, sub_mappings: list[dict[str, str]]
    ) -> str:
        _ = json.dumps(sub_mappings, ensure_ascii=False)
        self.chat_question.sql = sql
        self.chat_question.sub_query = sub_mappings
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        record_id = self.record.id
        dynamic_sql_msg: list[BaseMessage] = []
        dynamic_sql_msg.append(
            SystemMessage(content=self.chat_question.dynamic_sys_question())
        )
        dynamic_sql_msg.append(
            HumanMessage(content=self.chat_question.dynamic_user_question())
        )

        self.current_logs[OperationEnum.GENERATE_DYNAMIC_SQL] = start_log(
            session=session,
            ai_modal_id=self.chat_question.ai_modal_id,
            ai_modal_name=self.chat_question.ai_modal_name,
            operate=OperationEnum.GENERATE_DYNAMIC_SQL,
            record_id=record_id,
            full_message=_message_log_payloads(dynamic_sql_msg),
        )

        full_thinking_text = ""
        full_dynamic_text = ""
        token_usage: TokenUsage = {}
        res = process_stream(self.llm.stream(dynamic_sql_msg), token_usage)
        for chunk in res:
            full_dynamic_text += _chunk_content_text(chunk)
            full_thinking_text += _chunk_reasoning_text(chunk)

        dynamic_sql_msg.append(AIMessage(full_dynamic_text))

        self.current_logs[OperationEnum.GENERATE_DYNAMIC_SQL] = end_log(
            session=session,
            log=self.current_logs[OperationEnum.GENERATE_DYNAMIC_SQL],
            full_message=_message_log_payloads(dynamic_sql_msg),
            reasoning_content=full_thinking_text,
            token_usage=token_usage,
        )

        SQLBotLogUtil.info(full_dynamic_text)
        return full_dynamic_text

    def generate_assistant_dynamic_sql(
        self, _session: Session, sql: str, tables: list[str]
    ) -> dict[str, str] | None:
        if not isinstance(self.ds, AssistantOutDsSchema):
            return None
        ds: AssistantOutDsSchema = self.ds
        sub_query: list[dict[str, str]] = []
        result_dict: dict[str, str] = {}
        table_list = ds.tables or []
        for table in table_list:
            if table.name is None or table.sql is None:
                continue
            if table.name in tables:
                # sub_query.append({"table": table.name, "query": table.sql})
                result_dict[table.name] = table.sql
                sub_query.append(
                    {
                        "table": table.name,
                        "query": f"{dynamic_subsql_prefix}{table.name}",
                    }
                )
        if not sub_query:
            return None
        temp_sql_text = self.generate_with_sub_sql(
            session=_session, sql=sql, sub_mappings=sub_query
        )
        result_dict["sqlbot_temp_sql_text"] = temp_sql_text
        return result_dict

    def build_table_filter(
        self, session: Session, sql: str, filters: list[dict[str, str]]
    ) -> str:
        _ = json.dumps(filters, ensure_ascii=False)
        self.chat_question.sql = sql
        self.chat_question.filter = filters
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        record_id = self.record.id
        permission_sql_msg: list[BaseMessage] = []
        permission_sql_msg.append(
            SystemMessage(content=self.chat_question.filter_sys_question())
        )
        permission_sql_msg.append(
            HumanMessage(content=self.chat_question.filter_user_question())
        )

        self.current_logs[OperationEnum.GENERATE_SQL_WITH_PERMISSIONS] = start_log(
            session=session,
            ai_modal_id=self.chat_question.ai_modal_id,
            ai_modal_name=self.chat_question.ai_modal_name,
            operate=OperationEnum.GENERATE_SQL_WITH_PERMISSIONS,
            record_id=record_id,
            full_message=_message_log_payloads(permission_sql_msg),
        )
        full_thinking_text = ""
        full_filter_text = ""
        token_usage: TokenUsage = {}
        res = process_stream(self.llm.stream(permission_sql_msg), token_usage)
        for chunk in res:
            full_filter_text += _chunk_content_text(chunk)
            full_thinking_text += _chunk_reasoning_text(chunk)

        permission_sql_msg.append(AIMessage(full_filter_text))

        self.current_logs[OperationEnum.GENERATE_SQL_WITH_PERMISSIONS] = end_log(
            session=session,
            log=self.current_logs[OperationEnum.GENERATE_SQL_WITH_PERMISSIONS],
            full_message=_message_log_payloads(permission_sql_msg),
            reasoning_content=full_thinking_text,
            token_usage=token_usage,
        )

        SQLBotLogUtil.info(full_filter_text)
        return full_filter_text

    def generate_filter(
        self, _session: Session, sql: str, tables: list[str]
    ) -> str | None:
        if not isinstance(self.ds, CoreDatasource):
            return None
        filters = get_row_permission_filters(
            session=_session, current_user=self.current_user, ds=self.ds, tables=tables
        )
        if not filters:
            return None
        return self.build_table_filter(session=_session, sql=sql, filters=filters)

    def generate_assistant_filter(
        self, _session: Session, sql: str, tables: list[str]
    ) -> str | None:
        if not isinstance(self.ds, AssistantOutDsSchema):
            return None
        ds: AssistantOutDsSchema = self.ds
        filters: list[dict[str, str]] = []
        for table in ds.tables or []:
            if table.name in tables and table.rule:
                filters.append({"table": table.name, "filter": table.rule})
        if not filters:
            return None
        return self.build_table_filter(session=_session, sql=sql, filters=filters)

    def generate_chart(
        self,
        _session: Session,
        chart_type: str | None = "",
        schema: str | None = "",
    ) -> Iterator[ObjectDict]:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        record_id = self.record.id
        # append current question
        self.chart_message.append(
            HumanMessage(self.chat_question.chart_user_question(chart_type, schema))
        )

        self.current_logs[OperationEnum.GENERATE_CHART] = start_log(
            session=_session,
            ai_modal_id=self.chat_question.ai_modal_id,
            ai_modal_name=self.chat_question.ai_modal_name,
            operate=OperationEnum.GENERATE_CHART,
            record_id=record_id,
            full_message=_message_log_payloads(self.chart_message),
        )
        full_thinking_text = ""
        full_chart_text = ""
        token_usage: TokenUsage = {}
        res = process_stream(self.llm.stream(self.chart_message), token_usage)
        for chunk in res:
            full_chart_text += _chunk_content_text(chunk)
            full_thinking_text += _chunk_reasoning_text(chunk)
            yield chunk

        self.chart_message.append(AIMessage(full_chart_text))

        self.record = save_chart_answer(
            session=_session,
            record_id=record_id,
            answer=orjson.dumps({"content": full_chart_text}).decode(),
        )
        self.current_logs[OperationEnum.GENERATE_CHART] = end_log(
            session=_session,
            log=self.current_logs[OperationEnum.GENERATE_CHART],
            full_message=_message_log_payloads(self.chart_message),
            reasoning_content=full_thinking_text,
            token_usage=token_usage,
        )

    def check_sql(
        self, session: Session, res: str, operate: OperationEnum
    ) -> tuple[str, list[str] | None]:
        json_str = extract_nested_json(res)

        log = self.current_logs[operate]

        if json_str is None:
            _ = trigger_log_error(session, log)
            raise SingleMessageError(
                orjson.dumps(
                    {
                        "message": "SQL answer is not a valid json object",
                        "traceback": "SQL answer is not a valid json object:\n" + res,
                    }
                ).decode()
            )
        sql: str
        try:
            data = _parse_json_object(json_str)
            if data is None:
                raise ValueError("SQL payload is not a valid object")

            if _get_bool(data, "success"):
                sql_value = _get_str(data, "sql")
                if sql_value is None:
                    raise ValueError("SQL field is missing")
                sql = sql_value
            else:
                message = _get_str(data, "message") or "Cannot parse sql from answer"
                raise SingleMessageError(message)
        except SingleMessageError as e:
            _ = trigger_log_error(session, log)
            raise e
        except Exception:
            _ = trigger_log_error(session, log)
            raise SingleMessageError(
                orjson.dumps(
                    {
                        "message": "Cannot parse sql from answer",
                        "traceback": "Cannot parse sql from answer:\n" + res,
                    }
                ).decode()
            )

        if sql.strip() == "":
            _ = trigger_log_error(session, log)
            raise SingleMessageError("SQL query is empty")
        tables = _get_string_list(data, "tables")
        return sql, tables

    @staticmethod
    def get_chart_type_from_sql_answer(res: str) -> str | None:
        json_str = extract_nested_json(res)
        if json_str is None:
            return None

        try:
            data = _parse_json_object(json_str)
            if data is None:
                return None
            if _get_bool(data, "success"):
                return _get_str(data, "chart-type")
            return None
        except Exception:
            return None

    @staticmethod
    def get_brief_from_sql_answer(res: str) -> str | None:
        json_str = extract_nested_json(res)
        if json_str is None:
            return None

        try:
            data = _parse_json_object(json_str)
            if data is None:
                return None
            if _get_bool(data, "success"):
                return _get_str(data, "brief")
            return None
        except Exception:
            return None

    def check_save_sql(self, session: Session, res: str, operate: OperationEnum) -> str:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        sql, *_ = self.check_sql(session=session, res=res, operate=operate)
        _ = save_sql(session=session, sql=sql, record_id=self.record.id)

        self.chat_question.sql = sql

        return sql

    def check_save_chart(self, session: Session, res: str) -> ObjectDict:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        json_str = extract_nested_json(res)
        if json_str is None:
            raise SingleMessageError(
                orjson.dumps(
                    {
                        "message": "Cannot parse chart config from answer",
                        "traceback": "Cannot parse chart config from answer:\n" + res,
                    }
                ).decode()
            )
        chart: ObjectDict = {}
        message = ""
        error = False

        try:
            data = _parse_json_object(json_str)
            if data is None:
                raise ValueError("Chart payload is not a valid object")

            chart_type = _get_str(data, "type")
            if chart_type and chart_type != "error":
                chart = data
                columns_value = chart.get("columns")
                for column in _as_object_dict_list(columns_value):
                    _lowercase_mapping_value(column, "value")

                axis_data = _as_object_dict(chart.get("axis"))
                if axis_data is not None:
                    x_axis = _as_object_dict(axis_data.get("x"))
                    if x_axis is not None:
                        _lowercase_mapping_value(x_axis, "value")

                    y_axis = axis_data.get("y")
                    if y_axis:
                        if isinstance(y_axis, list):
                            for item in _as_object_dict_list(cast(object, y_axis)):
                                _lowercase_mapping_value(item, "value")
                        else:
                            y_axis_mapping = _as_object_dict(y_axis)
                            if y_axis_mapping is not None:
                                _lowercase_mapping_value(y_axis_mapping, "value")

                    series = _as_object_dict(axis_data.get("series"))
                    if series is not None:
                        _lowercase_mapping_value(series, "value")

                    multi_quota = _as_object_dict(axis_data.get("multi-quota"))
                    if multi_quota is not None:
                        multi_quota_value = multi_quota.get("value")
                        if isinstance(multi_quota_value, list):
                            multi_quota_values = _as_object_list(
                                cast(object, multi_quota_value)
                            )
                            multi_quota["value"] = [
                                value.lower() if isinstance(value, str) else value
                                for value in multi_quota_values
                            ]
                        elif isinstance(multi_quota_value, str):
                            multi_quota["value"] = multi_quota_value.lower()
            elif chart_type == "error":
                message = _get_str(data, "reason") or "Chart is empty"
                error = True
            else:
                raise Exception("Chart is empty")
        except Exception:
            error = True
            message = orjson.dumps(
                {
                    "message": "Cannot parse chart config from answer",
                    "traceback": "Cannot parse chart config from answer:\n" + res,
                }
            ).decode()

        if error:
            raise SingleMessageError(message)

        _ = save_chart(
            session=session,
            chart=orjson.dumps(chart).decode(),
            record_id=self.record.id,
        )

        return chart

    def check_save_predict_data(self, session: Session, res: str) -> bool:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        json_str = extract_nested_json(res)

        if not json_str:
            json_str = ""

        _ = save_predict_data(session=session, record_id=self.record.id, data=json_str)

        if json_str == "":
            return False

        return True

    def save_error(self, session: Session, message: str) -> ChatRecord:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        return save_error_message(
            session=session, record_id=self.record.id, message=message
        )

    def save_sql_data(self, session: Session, data_obj: ObjectDict) -> ChatRecord:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        data_result = data_obj.get("data")
        limit = 1000
        if data_result is not None:
            prepared_data = cast(object, prepare_for_orjson(data_result))
            prepared_rows = (
                _as_object_dict_list(cast(object, prepared_data))
                if isinstance(prepared_data, list)
                else None
            )
            if (
                prepared_rows is not None
                and len(prepared_rows) > limit
                and self.enable_sql_row_limit
            ):
                data_obj["data"] = prepared_rows[:limit]
                data_obj["limit"] = limit
            else:
                data_obj["data"] = (
                    prepared_rows if prepared_rows is not None else prepared_data
                )
            if self.ds and self.ds.id is not None:
                data_obj["datasource"] = self.ds.id
        return save_sql_exec_data(
            session=session,
            record_id=self.record.id,
            data=orjson.dumps(data_obj).decode(),
        )

    def finish(self, session: Session) -> ChatRecord:
        if self.record.id is None:
            raise SingleMessageError("Record not initialized")
        return finish_record(session=session, record_id=self.record.id)

    def execute_sql(self, sql: str) -> ObjectDict:
        """Execute SQL query

        Args:
            ds: Data source instance
            sql: SQL query statement

        Returns:
            Query results
        """
        if self.ds is None or self.ds.id is None:
            raise SingleMessageError("No available datasource configuration found")
        SQLBotLogUtil.info(f"Executing SQL on ds_id {self.ds.id}: {sql}")
        try:
            return cast(
                ObjectDict,
                exec_sql(ds=self.ds, sql=sql, origin_column=False),
            )
        except Exception as e:
            if isinstance(e, ParseSQLResultError):
                raise e
            else:
                err = traceback.format_exc(limit=1, chain=True)
                raise SQLBotDBError(err)

    def pop_chunk(self) -> StreamOutput | None:
        try:
            chunk = self.chunk_list.pop(0)
            return chunk
        except IndexError:
            return None

    def await_result(self) -> Iterator[StreamOutput]:
        while self.is_running():
            while True:
                chunk = self.pop_chunk()
                if chunk is not None:
                    yield chunk
                else:
                    break
        while True:
            chunk = self.pop_chunk()
            if chunk is None:
                break
            yield chunk

    def run_task_async(
        self,
        in_chat: bool = True,
        stream: bool = True,
        finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART,
    ) -> None:
        if in_chat:
            stream = True
        self.future = executor.submit(self.run_task_cache, in_chat, stream, finish_step)

    def run_task_cache(
        self,
        in_chat: bool = True,
        stream: bool = True,
        finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART,
    ) -> None:
        for chunk in self.run_task(in_chat, stream, finish_step):
            self.chunk_list.append(chunk)

    def run_task(
        self,
        in_chat: bool = True,
        stream: bool = True,
        finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART,
    ) -> Iterator[StreamOutput]:
        json_result: ObjectDict = {"success": True}
        _session: Session | None = None
        try:
            _session = session_maker()
            self._ensure_runtime_datasource(_session)
            if self.ds:
                oid = self.ds.oid if isinstance(self.ds, CoreDatasource) else 1
                ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None

                self.filter_terminology_template(_session, oid, ds_id)

                self.filter_training_template(_session, oid, ds_id)

                self.filter_custom_prompts(
                    _session, _custom_prompt_type("GENERATE_SQL"), oid, ds_id
                )

                self.init_messages(_session)

            # return id
            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps({"type": "id", "id": self.get_record().id}).decode()
                    + "\n\n"
                )
                if self.get_record().regenerate_record_id:
                    yield (
                        "data:"
                        + orjson.dumps(
                            {
                                "type": "regenerate_record_id",
                                "regenerate_record_id": self.get_record().regenerate_record_id,
                            }
                        ).decode()
                        + "\n\n"
                    )
                yield (
                    "data:"
                    + orjson.dumps(
                        {"type": "question", "question": self.get_record().question}
                    ).decode()
                    + "\n\n"
                )
            else:
                if stream:
                    yield (
                        "> "
                        + self.trans("i18n_chat.record_id_in_mcp")
                        + str(self.get_record().id)
                        + "\n"
                    )
                    yield "> " + self.get_record().question + "\n\n"
            if not stream:
                json_result["record_id"] = self.get_record().id

                # select datasource if datasource is none
            if not self.ds:
                ds_res = self.select_datasource(_session)

                for chunk in ds_res:
                    SQLBotLogUtil.info(str(chunk))
                    if in_chat:
                        yield (
                            "data:"
                            + orjson.dumps(
                                {
                                    "content": _chunk_content_text(chunk),
                                    "reasoning_content": _chunk_reasoning_text(chunk),
                                    "type": "datasource-result",
                                }
                            ).decode()
                            + "\n\n"
                        )
                if in_chat:
                    if self.ds is None:
                        raise SingleMessageError(
                            "No available datasource configuration found"
                        )
                    yield (
                        "data:"
                        + orjson.dumps(
                            {
                                "id": self.ds.id,
                                "datasource_name": self.ds.name,
                                "engine_type": self.ds.type_name or self.ds.type,
                                "type": "datasource",
                            }
                        ).decode()
                        + "\n\n"
                    )

            else:
                self.validate_history_ds(_session)

            # check connection
            if self.ds is None:
                raise SingleMessageError("No available datasource configuration found")
            connected = check_connection(ds=self.ds, trans=None)
            if not connected:
                raise SQLBotDBConnectionError("Connect DB failed")

            # generate sql
            sql_res = self.generate_sql(_session)
            full_sql_text = ""
            for chunk in sql_res:
                full_sql_text += _chunk_content_text(chunk)
                if in_chat:
                    yield (
                        "data:"
                        + orjson.dumps(
                            {
                                "content": _chunk_content_text(chunk),
                                "reasoning_content": _chunk_reasoning_text(chunk),
                                "type": "sql-result",
                            }
                        ).decode()
                        + "\n\n"
                    )
            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps({"type": "info", "msg": "sql generated"}).decode()
                    + "\n\n"
                )
            # filter sql
            SQLBotLogUtil.info(full_sql_text)

            chart_type = self.get_chart_type_from_sql_answer(full_sql_text)

            # return title
            if self.change_title:
                llm_brief = self.get_brief_from_sql_answer(full_sql_text)
                llm_brief_generated = bool(llm_brief)
                question_text = self.chat_question.question or ""
                if llm_brief_generated or (
                    question_text and question_text.strip() != ""
                ):
                    save_brief = (
                        llm_brief
                        if (llm_brief and llm_brief != "")
                        else question_text.strip()[:20]
                    )
                    brief = rename_chat(
                        session=_session,
                        rename_object=RenameChat(
                            id=self.get_record().chat_id,
                            brief=save_brief,
                            brief_generate=llm_brief_generated,
                        ),
                    )
                    if in_chat:
                        yield (
                            "data:"
                            + orjson.dumps({"type": "brief", "brief": brief}).decode()
                            + "\n\n"
                        )
                    if not stream:
                        json_result["title"] = brief

            use_dynamic_ds: bool = bool(
                self.current_assistant
                and self.current_assistant.type in dynamic_ds_types
            )
            is_page_embedded: bool = bool(
                self.current_assistant and self.current_assistant.type == 4
            )
            dynamic_sql_result: dict[str, str] | None = None
            sqlbot_temp_sql_text = None
            assistant_dynamic_sql = None
            # row permission

            sql_operate = OperationEnum.GENERATE_SQL
            sql, tables = self.check_sql(
                session=_session, res=full_sql_text, operate=sql_operate
            )
            table_list: list[str] = tables or []
            if (
                (not self.current_assistant or is_page_embedded)
                and is_normal_user(self.current_user)
            ) or use_dynamic_ds:
                sql_result = None

                if use_dynamic_ds:
                    dynamic_sql_result = self.generate_assistant_dynamic_sql(
                        _session, sql, table_list
                    )
                    sqlbot_temp_sql_text = (
                        dynamic_sql_result.get("sqlbot_temp_sql_text")
                        if dynamic_sql_result
                        else None
                    )
                else:
                    sql_result = self.generate_filter(
                        _session, sql, table_list
                    )  # maybe no sql and tables

                if sql_result:
                    SQLBotLogUtil.info(sql_result)
                    sql_operate = OperationEnum.GENERATE_SQL_WITH_PERMISSIONS
                    sql = self.check_save_sql(
                        session=_session, res=sql_result, operate=sql_operate
                    )
                elif dynamic_sql_result and sqlbot_temp_sql_text:
                    sql_operate = OperationEnum.GENERATE_DYNAMIC_SQL
                    assistant_dynamic_sql = self.check_save_sql(
                        session=_session, res=sqlbot_temp_sql_text, operate=sql_operate
                    )
                else:
                    sql = self.check_save_sql(
                        session=_session, res=full_sql_text, operate=sql_operate
                    )
            else:
                sql = self.check_save_sql(
                    session=_session, res=full_sql_text, operate=sql_operate
                )

            SQLBotLogUtil.info("sql: " + sql)

            if not stream:
                json_result["sql"] = sql

            format_sql = sqlparse.format(sql, reindent=True)
            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps({"content": format_sql, "type": "sql"}).decode()
                    + "\n\n"
                )
            else:
                if stream:
                    yield f"```sql\n{format_sql}\n```\n\n"

            # execute sql
            real_execute_sql = sql
            if sqlbot_temp_sql_text and assistant_dynamic_sql:
                if dynamic_sql_result is not None:
                    _ = dynamic_sql_result.pop("sqlbot_temp_sql_text", None)
                    for origin_table, subsql in dynamic_sql_result.items():
                        assistant_dynamic_sql = assistant_dynamic_sql.replace(
                            f"{dynamic_subsql_prefix}{origin_table}", subsql
                        )
                real_execute_sql = assistant_dynamic_sql

            if finish_step.value <= ChatFinishStep.GENERATE_SQL.value:
                if in_chat:
                    yield "data:" + orjson.dumps({"type": "finish"}).decode() + "\n\n"
                if not stream:
                    yield json_result
                return

            self.current_logs[OperationEnum.EXECUTE_SQL] = start_log(
                session=_session,
                operate=OperationEnum.EXECUTE_SQL,
                record_id=self.record.id,
                local_operation=True,
            )
            result = self.execute_sql(sql=real_execute_sql)
            data_rows = _get_object_dict_list(result, "data") or []
            self.current_logs[OperationEnum.EXECUTE_SQL] = end_log(
                session=_session,
                log=self.current_logs[OperationEnum.EXECUTE_SQL],
                full_message={
                    "sql": real_execute_sql,
                    "count": len(data_rows),
                },
            )

            _data = cast(
                list[ObjectDict],
                DataFormat.convert_large_numbers_in_object_array(data_rows),
            )
            result["data"] = _data

            _ = self.save_sql_data(session=_session, data_obj=result)
            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps(
                        {"content": "execute-success", "type": "sql-data"}
                    ).decode()
                    + "\n\n"
                )
            if not stream:
                if self.record.id is None:
                    raise SingleMessageError("Record not initialized")
                json_result["data"] = get_chat_chart_data(_session, self.record.id)

            if finish_step.value <= ChatFinishStep.QUERY_DATA.value:
                if stream:
                    if in_chat:
                        yield (
                            "data:" + orjson.dumps({"type": "finish"}).decode() + "\n\n"
                        )
                    else:
                        _column_list: list[AxisObj] = []
                        fields = _get_string_list(result, "fields") or []
                        for field in fields:
                            _column_list.append(AxisObj(name=field, value=field))

                        md_data, _fields_list = (
                            DataFormat.convert_object_array_for_pandas(
                                _column_list, _data
                            )
                        )

                        # data, _fields_list, col_formats = self.format_pd_data(_column_list, result.get('data'))

                        if not _data or not _fields_list:
                            yield "The SQL execution result is empty.\n\n"
                        else:
                            df = pd.DataFrame(_data, columns=_fields_list)
                            df_safe = DataFormat.safe_convert_to_string(df)
                            markdown_table = df_safe.to_markdown(index=False)
                            yield markdown_table + "\n\n"
                else:
                    yield json_result
                return

            # generate chart
            question_text = self.chat_question.question or ""
            if self.out_ds_instance:
                used_tables_schema = self.out_ds_instance.get_db_schema(
                    self.ds.id if self.ds and self.ds.id is not None else 0,
                    question_text,
                    embedding=False,
                    table_list=table_list,
                )
            else:
                if not isinstance(self.ds, CoreDatasource):
                    raise SingleMessageError(
                        "No available datasource configuration found"
                    )
                used_tables_schema = get_table_schema(
                    session=_session,
                    current_user=self.current_user,
                    ds=self.ds,
                    question=question_text,
                    embedding=False,
                    table_list=table_list,
                )
            SQLBotLogUtil.info("used_tables_schema: \n" + used_tables_schema)
            chart_res = self.generate_chart(_session, chart_type, used_tables_schema)
            full_chart_text = ""
            for chunk in chart_res:
                full_chart_text += _chunk_content_text(chunk)
                if in_chat:
                    yield (
                        "data:"
                        + orjson.dumps(
                            {
                                "content": _chunk_content_text(chunk),
                                "reasoning_content": _chunk_reasoning_text(chunk),
                                "type": "chart-result",
                            }
                        ).decode()
                        + "\n\n"
                    )
            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps({"type": "info", "msg": "chart generated"}).decode()
                    + "\n\n"
                )

            # filter chart
            SQLBotLogUtil.info(full_chart_text)
            chart = self.check_save_chart(session=_session, res=full_chart_text)
            SQLBotLogUtil.info(str(chart))

            if not stream:
                json_result["chart"] = chart

            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps(
                        {"content": orjson.dumps(chart).decode(), "type": "chart"}
                    ).decode()
                    + "\n\n"
                )
            else:
                if stream:
                    fields = _get_string_list(result, "fields") or []
                    md_data, _fields_list = DataFormat.convert_data_fields_for_pandas(
                        chart, fields, _data
                    )
                    # data, _fields_list, col_formats = self.format_pd_data(_column_list, result.get('data'))

                    if not md_data or not _fields_list:
                        yield "The SQL execution result is empty.\n\n"
                    else:
                        df = pd.DataFrame(md_data, columns=_fields_list)
                        df_safe = DataFormat.safe_convert_to_string(df)
                        markdown_table = df_safe.to_markdown(index=False)
                        yield markdown_table + "\n\n"

            if in_chat:
                yield "data:" + orjson.dumps({"type": "finish"}).decode() + "\n\n"
            else:
                # generate picture
                try:
                    if chart.get("type") != "table":
                        # yield '### generated chart picture\n\n'
                        self.current_logs[OperationEnum.GENERATE_PICTURE] = start_log(
                            session=_session,
                            operate=OperationEnum.GENERATE_PICTURE,
                            record_id=self.record.id,
                            local_operation=True,
                        )
                        if self.record.id is None:
                            raise SingleMessageError("Record not initialized")
                        image_url, error = request_picture(
                            self.record.chat_id,
                            self.record.id,
                            chart,
                            format_json_data(result),
                        )
                        SQLBotLogUtil.info(image_url)
                        if stream:
                            yield f"![{chart.get('type')}]({image_url})"
                        else:
                            json_result["image_url"] = image_url
                        if error is not None:
                            raise error

                        self.current_logs[OperationEnum.GENERATE_PICTURE] = end_log(
                            session=_session,
                            log=self.current_logs[OperationEnum.GENERATE_PICTURE],
                            full_message={"image_url": image_url},
                        )
                except Exception as e:
                    if stream:
                        if chart.get("type") != "table":
                            yield "generate or fetch chart picture error.\n\n"
                        raise e

            if not stream:
                yield json_result

        except Exception as e:
            traceback.print_exc()
            error_msg: str
            if isinstance(e, SingleMessageError):
                error_msg = str(e)
            elif isinstance(e, SQLBotDBConnectionError):
                error_msg = orjson.dumps(
                    {"message": str(e), "type": "db-connection-err"}
                ).decode()
            elif isinstance(e, SQLBotDBError):
                error_msg = orjson.dumps(
                    {
                        "message": "Execute SQL Failed",
                        "traceback": str(e),
                        "type": "exec-sql-err",
                    }
                ).decode()
            else:
                error_msg = orjson.dumps(
                    {"message": str(e), "traceback": traceback.format_exc(limit=1)}
                ).decode()
            if _session:
                _ = self.save_error(session=_session, message=error_msg)
            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps({"content": error_msg, "type": "error"}).decode()
                    + "\n\n"
                )
            else:
                if stream:
                    yield "&#x274c; **ERROR:**\n"
                    yield f"> {error_msg}\n"
                else:
                    json_result["success"] = False
                    json_result["message"] = error_msg
                    yield json_result
        finally:
            if _session is not None:
                _ = self.finish(_session)
            session_maker.remove()

    def run_recommend_questions_task_async(self) -> None:
        self.future = executor.submit(self.run_recommend_questions_task_cache)

    def run_recommend_questions_task_cache(self) -> None:
        for chunk in self.run_recommend_questions_task():
            self.chunk_list.append(chunk)

    def run_recommend_questions_task(self) -> Iterator[str]:
        _session: Session | None = None
        try:
            _session = session_maker()
            self._ensure_runtime_datasource(_session)
            res = self.generate_recommend_questions_task(_session)

            for chunk in res:
                if chunk.get("recommended_question"):
                    yield (
                        "data:"
                        + orjson.dumps(
                            {
                                "content": chunk.get("recommended_question"),
                                "type": "recommended_question",
                            }
                        ).decode()
                        + "\n\n"
                    )
                else:
                    yield (
                        "data:"
                        + orjson.dumps(
                            {
                                "content": _chunk_content_text(chunk),
                                "reasoning_content": _chunk_reasoning_text(chunk),
                                "type": "recommended_question_result",
                            }
                        ).decode()
                        + "\n\n"
                    )
        except Exception:
            traceback.print_exc()
        finally:
            _ = _session
            session_maker.remove()

    def run_analysis_or_predict_task_async(
        self,
        session: Session,
        action_type: str,
        base_record: ChatRecord,
        in_chat: bool = True,
        stream: bool = True,
    ) -> None:
        self.set_record(save_analysis_predict_record(session, base_record, action_type))
        self.future = executor.submit(
            self.run_analysis_or_predict_task_cache, action_type, in_chat, stream
        )

    def run_analysis_or_predict_task_cache(
        self, action_type: str, in_chat: bool = True, stream: bool = True
    ) -> None:
        for chunk in self.run_analysis_or_predict_task(action_type, in_chat, stream):
            self.chunk_list.append(chunk)

    def run_analysis_or_predict_task(
        self, action_type: str, in_chat: bool = True, stream: bool = True
    ) -> Iterator[str | dict[str, object]]:
        json_result: dict[str, object] = {"success": True}
        _session: Session | None = None
        try:
            _session = session_maker()
            self._ensure_runtime_datasource(_session)
            record_id = self.get_record().id
            if record_id is None:
                raise SingleMessageError("Record not initialized")
            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps({"type": "id", "id": record_id}).decode()
                    + "\n\n"
                )
            else:
                if stream:
                    yield (
                        "> "
                        + self.trans("i18n_chat.record_id_in_mcp")
                        + str(record_id)
                        + "\n"
                    )
                    yield "> " + str(self.get_record().question or "") + "\n\n"
            if not stream:
                json_result["record_id"] = record_id

            if action_type == "analysis":
                # generate analysis
                analysis_res = self.generate_analysis(_session)
                full_text = ""
                for chunk in analysis_res:
                    content = _chunk_content_text(chunk)
                    full_text += content
                    if in_chat:
                        yield (
                            "data:"
                            + orjson.dumps(
                                {
                                    "content": content,
                                    "reasoning_content": _chunk_reasoning_text(chunk),
                                    "type": "analysis-result",
                                }
                            ).decode()
                            + "\n\n"
                        )
                    else:
                        if stream:
                            yield str(content or "")
                if in_chat:
                    yield (
                        "data:"
                        + orjson.dumps(
                            {"type": "info", "msg": "analysis generated"}
                        ).decode()
                        + "\n\n"
                    )
                    yield (
                        "data:"
                        + orjson.dumps({"type": "analysis_finish"}).decode()
                        + "\n\n"
                    )
                else:
                    if stream:
                        yield "\n\n"
                if not stream:
                    json_result["content"] = full_text

            elif action_type == "predict":
                # generate predict
                analysis_res = self.generate_predict(_session)
                full_text = ""
                for chunk in analysis_res:
                    content = _chunk_content_text(chunk)
                    full_text += content
                    if in_chat:
                        yield (
                            "data:"
                            + orjson.dumps(
                                {
                                    "content": content,
                                    "reasoning_content": _chunk_reasoning_text(chunk),
                                    "type": "predict-result",
                                }
                            ).decode()
                            + "\n\n"
                        )
                if in_chat:
                    yield (
                        "data:"
                        + orjson.dumps(
                            {"type": "info", "msg": "predict generated"}
                        ).decode()
                        + "\n\n"
                    )

                has_data = self.check_save_predict_data(session=_session, res=full_text)
                if has_data:
                    if in_chat:
                        yield (
                            "data:"
                            + orjson.dumps({"type": "predict-success"}).decode()
                            + "\n\n"
                        )
                    else:
                        chart = get_chat_chart_config(_session, record_id)
                        origin_data = get_chat_chart_data(_session, record_id)
                        predict_payload = get_chat_predict_data(_session, record_id)
                        predict_rows = (
                            _get_object_dict_list(predict_payload, "data") or []
                        )
                        fields = _get_string_list(origin_data, "fields") or []

                        if stream:
                            md_data, _fields_list = (
                                DataFormat.convert_data_fields_for_pandas(
                                    chart, fields, predict_rows
                                )
                            )
                            if not md_data or not _fields_list:
                                yield "Predict data result is empty.\n\n"
                            else:
                                df = pd.DataFrame(md_data, columns=_fields_list)
                                df_safe = DataFormat.safe_convert_to_string(df)
                                markdown_table = df_safe.to_markdown(index=False)
                                yield markdown_table + "\n\n"

                        else:
                            json_result["origin_data"] = origin_data
                            json_result["predict_data"] = predict_payload

                        # generate picture
                        try:
                            if chart.get("type") != "table":
                                # yield '### generated chart picture\n\n'

                                _data = get_chat_chart_data(_session, record_id)
                                data_list = _get_object_dict_list(_data, "data") or []
                                _data["data"] = data_list + predict_rows

                                image_url, error = request_picture(
                                    self.record.chat_id,
                                    record_id,
                                    chart,
                                    format_json_data(_data),
                                )
                                SQLBotLogUtil.info(image_url)
                                if stream:
                                    yield f"![{chart.get('type')}]({image_url})"
                                else:
                                    json_result["image_url"] = image_url
                                if error is not None:
                                    raise error
                        except Exception as e:
                            if stream:
                                if chart.get("type") != "table":
                                    yield "generate or fetch chart picture error.\n\n"
                                raise e
                else:
                    if in_chat:
                        yield (
                            "data:"
                            + orjson.dumps({"type": "predict-failed"}).decode()
                            + "\n\n"
                        )
                    else:
                        if stream:
                            yield full_text + "\n\n"
                    if not stream:
                        json_result["success"] = False
                        json_result["message"] = full_text
                if in_chat:
                    yield (
                        "data:"
                        + orjson.dumps({"type": "predict_finish"}).decode()
                        + "\n\n"
                    )

            _ = self.finish(_session)

            if not stream:
                yield json_result
        except Exception as e:
            traceback.print_exc()
            error_msg: str
            if isinstance(e, SingleMessageError):
                error_msg = str(e)
            else:
                error_msg = orjson.dumps(
                    {"message": str(e), "traceback": traceback.format_exc(limit=1)}
                ).decode()
            if _session:
                _ = self.save_error(session=_session, message=error_msg)
            if in_chat:
                yield (
                    "data:"
                    + orjson.dumps({"content": error_msg, "type": "error"}).decode()
                    + "\n\n"
                )
            else:
                if stream:
                    yield "&#x274c; **ERROR:**\n"
                    yield f"> {error_msg}\n"
                else:
                    json_result["success"] = False
                    json_result["message"] = error_msg
                    yield json_result
        finally:
            # end
            _ = _session
            session_maker.remove()

    def validate_history_ds(self, session: Session) -> None:
        ds = self.ds
        if ds is None or ds.id is None:
            raise SingleMessageError("chat.ds_is_invalid")

        if not self.current_assistant or self.current_assistant.type == 4:
            current_ds = session.get(CoreDatasource, ds.id)
            if current_ds is None:
                raise SingleMessageError("chat.ds_is_invalid")
            return

        ds_list: list[dict[str, object]] = get_assistant_ds(
            session=session, llm_service=self
        )
        match_ds = any(item.get("id") == ds.id for item in ds_list)
        if not match_ds:
            assistant_type = self.current_assistant.type
            msg = (
                "[please check ds list and public ds list]"
                if assistant_type == 0
                else "[please check ds api]"
            )
            raise SingleMessageError(msg)


def execute_sql_with_db(db: SQLDatabase, sql: str) -> str:
    """Execute SQL query using SQLDatabase

    Args:
        db: SQLDatabase instance
        sql: SQL query statement

    Returns:
        str: Query results formatted as string
    """
    try:
        # Execute query
        result = db.run(sql)

        if not result:
            return "Query executed successfully but returned no results."

        # Format results
        return str(result)

    except Exception as e:
        error_msg = f"SQL execution failed: {str(e)}"
        SQLBotLogUtil.exception(error_msg)
        raise RuntimeError(error_msg)


def request_picture(
    chat_id: int,
    record_id: int,
    chart: ObjectDict,
    data: ObjectDict,
) -> tuple[str, Exception | None]:
    file_name = f"c_{chat_id}_r_{record_id}"

    columns_raw = chart.get("columns")
    columns = _as_object_dict_list(columns_raw)
    axis_data_raw = chart.get("axis")
    axis_data = _as_object_dict(axis_data_raw) or {}
    x_raw = axis_data.get("x")
    x = _as_object_dict(x_raw)
    y = axis_data.get("y")
    series_raw = axis_data.get("series")
    series = _as_object_dict(series_raw)

    multi_quota_fields_raw: list[object] | object = []
    multi_quota_name: str | None = None
    multi_quota = _as_object_dict(axis_data.get("multi-quota"))
    if multi_quota is not None:
        multi_quota_fields_raw = multi_quota.get("value", [])
        multi_quota_name = _get_str(multi_quota, "name")
    multi_quota_fields = _as_object_list(multi_quota_fields_raw)

    axis: list[dict[str, object]] = []
    for v in columns:
        axis.append({"name": v.get("name"), "value": v.get("value")})
    if x is not None:
        axis.append({"name": x.get("name"), "value": x.get("value"), "type": "x"})
    if y:
        y_list = _as_object_list(cast(object, y)) if isinstance(y, list) else [y]

        for y_item in y_list:
            y_item_mapping = _as_object_dict(y_item)
            if y_item_mapping is not None and "value" in y_item_mapping:
                y_obj = {
                    "name": y_item_mapping.get("name"),
                    "value": y_item_mapping.get("value"),
                    "type": "y",
                }
                if y_item_mapping.get("value") in multi_quota_fields:
                    y_obj["multi-quota"] = True
                axis.append(y_obj)
    if series is not None:
        axis.append(
            {"name": series.get("name"), "value": series.get("value"), "type": "series"}
        )
    if multi_quota_name:
        axis.append(
            {"name": multi_quota_name, "value": multi_quota_name, "type": "other-info"}
        )

    data_rows = _get_object_dict_list(data, "data") or []

    request_obj: dict[str, object] = {
        "path": os.path.join(settings.MCP_IMAGE_PATH, file_name),
        "type": chart.get("type"),
        "data": orjson.dumps(data_rows).decode(),
        "axis": orjson.dumps(axis).decode(),
    }

    _error: Exception | None = None
    try:
        response = httpx.post(
            url=settings.MCP_IMAGE_HOST,
            json=request_obj,
            timeout=settings.SERVER_IMAGE_TIMEOUT,
        )
        _ = response.raise_for_status()
    except httpx.HTTPError as e:
        _error = e

    request_path = urllib.parse.urljoin(settings.SERVER_IMAGE_HOST, f"{file_name}.png")

    return request_path, _error


def get_token_usage(
    chunk: BaseMessageChunk, token_usage: dict[str, object] | None = None
) -> dict[str, object]:
    if token_usage is None:
        token_usage = {}
    usage_metadata = _as_object_dict(
        cast(object, getattr(chunk, "usage_metadata", None))
    )
    if usage_metadata is not None:
        token_usage["input_tokens"] = _mapping_value(usage_metadata, "input_tokens")
        token_usage["output_tokens"] = _mapping_value(usage_metadata, "output_tokens")
        token_usage["total_tokens"] = _mapping_value(usage_metadata, "total_tokens")
    return token_usage


def process_stream(
    res: Iterator[BaseMessageChunk],
    token_usage: dict[str, object] | None = None,
    enable_tag_parsing: bool = settings.PARSE_REASONING_BLOCK_ENABLED,
    start_tag: str = settings.DEFAULT_REASONING_CONTENT_START,
    end_tag: str = settings.DEFAULT_REASONING_CONTENT_END,
) -> Iterator[ObjectDict]:
    if token_usage is None:
        token_usage = {}
    in_thinking_block = False  # 标记是否在思考过程块中
    current_thinking = ""  # 当前收集的思考过程内容
    pending_start_tag = ""  # 用于缓存可能被截断的开始标签部分

    for chunk in res:
        SQLBotLogUtil.info(str(chunk))
        reasoning_content_chunk = ""
        content = _chunk_content_text_from_message(chunk)
        output_content = ""  # 实际要输出的内容

        # 检查additional_kwargs中的reasoning_content
        additional_kwargs = _chunk_additional_kwargs(chunk)
        reasoning_content_raw = _mapping_value(additional_kwargs, "reasoning_content")
        if reasoning_content_raw is not None:
            reasoning_content = (
                reasoning_content_raw if isinstance(reasoning_content_raw, str) else ""
            )

            # 累积additional_kwargs中的思考内容到current_thinking
            current_thinking += reasoning_content
            reasoning_content_chunk = reasoning_content

        # 只有当current_thinking不是空字符串时才跳过标签解析
        if not in_thinking_block and current_thinking.strip() != "":
            output_content = content  # 正常输出content
            yield _stream_chunk(output_content, reasoning_content_chunk)
            _ = get_token_usage(chunk, token_usage)
            continue  # 跳过后续的标签解析逻辑

        # 如果没有有效的思考内容，并且启用了标签解析，才执行标签解析逻辑
        # 如果有缓存的开始标签部分，先拼接当前内容
        if pending_start_tag:
            content = pending_start_tag + content
            pending_start_tag = ""

        # 检查是否开始思考过程块（处理可能被截断的开始标签）
        if enable_tag_parsing and not in_thinking_block and start_tag:
            if start_tag in content:
                start_idx = content.index(start_tag)
                # 只有当开始标签前面没有其他文本时才认为是真正的思考块开始
                if start_idx == 0 or content[:start_idx].strip() == "":
                    # 完整标签存在且前面没有其他文本
                    output_content += content[:start_idx]  # 输出开始标签之前的内容
                    content = content[start_idx + len(start_tag) :]  # 移除开始标签
                    in_thinking_block = True
                else:
                    # 开始标签前面有其他文本，不认为是思考块开始
                    output_content += content
                    content = ""
            else:
                # 检查是否可能有部分开始标签
                for i in range(1, len(start_tag)):
                    if content.endswith(start_tag[:i]):
                        # 只有当当前内容全是空白时才缓存部分标签
                        if content[:-i].strip() == "":
                            pending_start_tag = start_tag[:i]
                            content = content[:-i]  # 移除可能的部分标签
                            output_content += content
                            content = ""
                        break

        # 处理思考块内容
        if enable_tag_parsing and in_thinking_block and end_tag:
            if end_tag in content:
                # 找到结束标签
                end_idx = content.index(end_tag)
                current_thinking += content[:end_idx]  # 收集思考内容
                reasoning_content_chunk += current_thinking  # 添加到当前块的思考内容
                content = content[end_idx + len(end_tag) :]  # 移除结束标签后的内容
                current_thinking = ""  # 重置当前思考内容
                in_thinking_block = False
                output_content += content  # 输出结束标签之后的内容
            else:
                # 在遇到结束标签前，持续收集思考内容
                current_thinking += content
                reasoning_content_chunk += content
                content = ""

        else:
            # 不在思考块中或标签解析未启用，正常输出
            output_content += content

        yield _stream_chunk(output_content, reasoning_content_chunk)
        _ = get_token_usage(chunk, token_usage)


def get_lang_name(lang: str) -> str:
    if not lang:
        return "简体中文"
    normalized = lang.lower()
    if normalized.startswith("en"):
        return "英文"
    if normalized.startswith("ko"):
        return "韩语"
    return "简体中文"


def get_last_conversation_rounds(
    messages: list[dict[str, object]],
    rounds: int = settings.GENERATE_SQL_QUERY_HISTORY_ROUND_COUNT,
) -> list[dict[str, object]]:
    """获取最后N轮对话，处理不完整对话的情况"""
    if not messages or rounds <= 0:
        return []

    # 找到所有用户消息的位置
    human_indices: list[int] = []
    for index, msg in enumerate(messages):
        if msg.get("type") == "human":
            human_indices.append(index)

    # 如果没有用户消息，返回空
    if not human_indices:
        return []

    # 计算从哪个索引开始
    if len(human_indices) <= rounds:
        # 如果用户消息数少于等于需要的轮数，从第一个用户消息开始
        start_index = human_indices[0]
    else:
        # 否则，从倒数第N个用户消息开始
        start_index = human_indices[-rounds]

    return messages[start_index:]
