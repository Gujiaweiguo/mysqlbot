from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, cast

from fastapi import Body
from pydantic import BaseModel
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Identity, Integer, Text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from apps.db.constant import DB
from apps.template.filter.generator import get_permissions_template
from apps.template.generate_analysis.generator import get_analysis_template
from apps.template.generate_chart.generator import get_chart_template
from apps.template.generate_dynamic.generator import get_dynamic_template
from apps.template.generate_guess_question.generator import get_guess_question_template
from apps.template.generate_predict.generator import get_predict_template
from apps.template.generate_sql.generator import (
    get_sql_example_template,
    get_sql_template,
)
from apps.template.select_datasource.generator import get_datasource_template

TemplateFactory = Callable[[], dict[str, Any]]
SqlTemplateFactory = Callable[[str | DB], dict[str, Any]]

_get_permissions_template = cast(TemplateFactory, get_permissions_template)
_get_analysis_template = cast(TemplateFactory, get_analysis_template)
_get_chart_template = cast(TemplateFactory, get_chart_template)
_get_dynamic_template = cast(TemplateFactory, get_dynamic_template)
_get_guess_question_template = cast(TemplateFactory, get_guess_question_template)
_get_predict_template = cast(TemplateFactory, get_predict_template)
_get_sql_template = cast(TemplateFactory, get_sql_template)
_get_sql_example_template = cast(SqlTemplateFactory, get_sql_example_template)
_get_datasource_template = cast(TemplateFactory, get_datasource_template)


def enum_values(enum_class: type[Enum]) -> list[str | int]:
    """Get values for enum."""
    return [status.value for status in enum_class]


class TypeEnum(Enum):
    CHAT = "0"


#     TODO other usage


class OperationEnum(Enum):
    GENERATE_SQL = "0"
    GENERATE_CHART = "1"
    ANALYSIS = "2"
    PREDICT_DATA = "3"
    GENERATE_RECOMMENDED_QUESTIONS = "4"
    GENERATE_SQL_WITH_PERMISSIONS = "5"
    CHOOSE_DATASOURCE = "6"
    GENERATE_DYNAMIC_SQL = "7"
    CHOOSE_TABLE = "8"
    FILTER_TERMS = "9"
    FILTER_SQL_EXAMPLE = "10"
    FILTER_CUSTOM_PROMPT = "11"
    EXECUTE_SQL = "12"
    GENERATE_PICTURE = "13"


class ChatFinishStep(Enum):
    GENERATE_SQL = 1
    QUERY_DATA = 2
    GENERATE_CHART = 3


class QuickCommand(Enum):
    REGENERATE = "/regenerate"
    ANALYSIS = "/analysis"
    PREDICT_DATA = "/predict"


#     TODO choose table / check connection / generate description


class ChatLog(SQLModel, table=True):
    __tablename__ = "chat_log"
    id: int | None = Field(
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True)
    )
    type: TypeEnum = Field(
        sa_column=Column(
            SQLAlchemyEnum(
                TypeEnum, native_enum=False, values_callable=enum_values, length=3
            )
        )
    )
    operate: OperationEnum = Field(
        sa_column=Column(
            SQLAlchemyEnum(
                OperationEnum, native_enum=False, values_callable=enum_values, length=3
            )
        )
    )
    pid: int | None = Field(sa_column=Column(BigInteger, nullable=True))
    ai_modal_id: int | None = Field(sa_column=Column(BigInteger))
    base_modal: str | None = Field(max_length=255)
    messages: list[dict[str, Any]] | None = Field(sa_column=Column(JSONB))
    reasoning_content: str | None = Field(sa_column=Column(Text, nullable=True))
    start_time: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    finish_time: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    token_usage: dict[str, Any] | int | None = Field(sa_column=Column(JSONB))
    local_operation: bool = Field(default=False)
    error: bool = Field(default=False)


class Chat(SQLModel, table=True):
    __tablename__ = "chat"
    id: int | None = Field(
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True)
    )
    oid: int | None = Field(sa_column=Column(BigInteger, nullable=True, default=1))
    create_time: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    create_by: int = Field(sa_column=Column(BigInteger, nullable=True))
    brief: str = Field(max_length=64, nullable=True)
    chat_type: str = Field(max_length=20, default="chat")  # chat, datasource
    datasource: int = Field(sa_column=Column(BigInteger, nullable=True))
    engine_type: str = Field(max_length=64)
    origin: int | None = Field(
        sa_column=Column(Integer, nullable=False, default=0)
    )  # 0: default, 1: mcp, 2: assistant
    brief_generate: bool = Field(default=False)
    recommended_question_answer: str = Field(sa_column=Column(Text, nullable=True))
    recommended_question: str = Field(sa_column=Column(Text, nullable=True))
    recommended_generate: bool = Field(default=False)


class ChatRecord(SQLModel, table=True):
    __tablename__ = "chat_record"
    id: int | None = Field(
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True)
    )
    chat_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    ai_modal_id: int | None = Field(sa_column=Column(BigInteger))
    first_chat: bool = Field(sa_column=Column(Boolean, nullable=True, default=False))
    create_time: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    finish_time: datetime = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    create_by: int = Field(sa_column=Column(BigInteger, nullable=True))
    datasource: int = Field(sa_column=Column(BigInteger, nullable=True))
    engine_type: str = Field(max_length=64, nullable=True)
    question: str = Field(sa_column=Column(Text, nullable=True))
    sql_answer: str = Field(sa_column=Column(Text, nullable=True))
    sql: str = Field(sa_column=Column(Text, nullable=True))
    sql_exec_result: str = Field(sa_column=Column(Text, nullable=True))
    data: str = Field(sa_column=Column(Text, nullable=True))
    chart_answer: str = Field(sa_column=Column(Text, nullable=True))
    chart: str = Field(sa_column=Column(Text, nullable=True))
    analysis: str = Field(sa_column=Column(Text, nullable=True))
    predict: str = Field(sa_column=Column(Text, nullable=True))
    predict_data: str = Field(sa_column=Column(Text, nullable=True))
    recommended_question_answer: str = Field(sa_column=Column(Text, nullable=True))
    recommended_question: str = Field(sa_column=Column(Text, nullable=True))
    datasource_select_answer: str = Field(sa_column=Column(Text, nullable=True))
    finish: bool = Field(sa_column=Column(Boolean, nullable=True, default=False))
    error: str = Field(sa_column=Column(Text, nullable=True))
    analysis_record_id: int = Field(sa_column=Column(BigInteger, nullable=True))
    predict_record_id: int = Field(sa_column=Column(BigInteger, nullable=True))
    regenerate_record_id: int = Field(sa_column=Column(BigInteger, nullable=True))


class ChatRecordResult(BaseModel):
    id: int | None = None
    chat_id: int | None = None
    ai_modal_id: int | None = None
    first_chat: bool = False
    create_time: datetime | None = None
    finish_time: datetime | None = None
    question: str | None = None
    sql_answer: str | None = None
    sql: str | None = None
    datasource: int | None = None
    data: str | None = None
    chart_answer: str | None = None
    chart: str | None = None
    analysis: str | None = None
    predict: str | None = None
    predict_data: str | None = None
    recommended_question: str | None = None
    datasource_select_answer: str | None = None
    finish: bool | None = None
    error: str | None = None
    analysis_record_id: int | None = None
    predict_record_id: int | None = None
    regenerate_record_id: int | None = None
    sql_reasoning_content: str | None = None
    chart_reasoning_content: str | None = None
    analysis_reasoning_content: str | None = None
    predict_reasoning_content: str | None = None
    duration: float | None = None  # 耗时字段（单位：秒）
    total_tokens: int | None = None  # token总消耗


class CreateChat(BaseModel):
    id: int | None = None
    question: str | None = None
    datasource: int | None = None
    origin: int | None = 0  # 0是页面上，mcp是1，小助手是2


class RenameChat(BaseModel):
    id: int | None = None
    brief: str = ""
    brief_generate: bool = True


class ChatInfo(BaseModel):
    id: int | None = None
    create_time: datetime | None = None
    create_by: int | None = None
    brief: str = ""
    chat_type: str = "chat"
    datasource: int | None = None
    engine_type: str = ""
    ds_type: str = ""
    datasource_name: str = ""
    datasource_exists: bool = True
    recommended_question: str | None = None
    recommended_generate: bool | None = False
    records: list[ChatRecord | dict[str, Any]] = []


class ChatLogHistoryItem(BaseModel):
    start_time: datetime | None = None
    finish_time: datetime | None = None
    duration: float | None = None  # 耗时字段（单位：秒）
    total_tokens: int | None = None  # token总消耗
    operate: str | None = None
    local_operation: bool | None = False
    message: str | dict[str, Any] | list[Any] | None = None
    error: bool | None = False


class ChatLogHistory(BaseModel):
    start_time: datetime | None = None
    finish_time: datetime | None = None
    duration: float | None = None  # 耗时字段（单位：秒）
    total_tokens: int | None = None  # token总消耗
    steps: list[ChatLogHistoryItem | dict[str, Any]] = []


class AiModelQuestion(BaseModel):
    question: str | None = None
    ai_modal_id: int | None = None
    ai_modal_name: str | None = None
    engine: str = ""
    db_schema: str = ""
    sql: str = ""
    rule: str = ""
    fields: str = ""
    data: str = ""
    lang: str = "简体中文"
    filter: list[Any] = []
    sub_query: list[dict[str, Any]] | None = None
    terminologies: str = ""
    data_training: str = ""
    custom_prompt: str = ""
    error_msg: str = ""
    regenerate_record_id: int | None = None

    def sql_sys_question(
        self, db_type: str | DB, enable_query_limit: bool = True
    ) -> str:
        _sql_template = _get_sql_example_template(db_type)
        _base_template = _get_sql_template()
        _process_check = (
            _sql_template.get("process_check")
            if _sql_template.get("process_check")
            else _base_template["process_check"]
        )
        _query_limit = (
            _base_template["query_limit"]
            if enable_query_limit
            else _base_template["no_query_limit"]
        )
        _other_rule = _sql_template["other_rule"].format(
            multi_table_condition=_base_template["multi_table_condition"]
        )
        _base_sql_rules = (
            _sql_template["quot_rule"]
            + _query_limit
            + _sql_template["limit_rule"]
            + _other_rule
        )
        _sql_examples = _sql_template["basic_example"]
        _example_engine = _sql_template["example_engine"]
        _example_answer_1 = (
            _sql_template["example_answer_1_with_limit"]
            if enable_query_limit
            else _sql_template["example_answer_1"]
        )
        _example_answer_2 = (
            _sql_template["example_answer_2_with_limit"]
            if enable_query_limit
            else _sql_template["example_answer_2"]
        )
        _example_answer_3 = (
            _sql_template["example_answer_3_with_limit"]
            if enable_query_limit
            else _sql_template["example_answer_3"]
        )
        return cast(
            str,
            _base_template["system"].format(
                engine=self.engine,
                schema=self.db_schema,
                question=self.question,
                lang=self.lang,
                terminologies=self.terminologies,
                data_training=self.data_training,
                custom_prompt=self.custom_prompt,
                process_check=_process_check,
                base_sql_rules=_base_sql_rules,
                basic_sql_examples=_sql_examples,
                example_engine=_example_engine,
                example_answer_1=_example_answer_1,
                example_answer_2=_example_answer_2,
                example_answer_3=_example_answer_3,
            ),
        )

    def sql_user_question(self, current_time: str, change_title: bool) -> str:
        _question = self.question
        if self.regenerate_record_id:
            _question = _get_sql_template()["regenerate_hint"] + self.question
        return cast(
            str,
            _get_sql_template()["user"].format(
                engine=self.engine,
                schema=self.db_schema,
                question=_question,
                rule=self.rule,
                current_time=current_time,
                error_msg=self.error_msg,
                change_title=change_title,
            ),
        )

    def chart_sys_question(self) -> str:
        return cast(
            str,
            _get_chart_template()["system"].format(
                sql=self.sql, question=self.question, lang=self.lang
            ),
        )

    def chart_user_question(
        self, chart_type: str | None = "", schema: str | None = ""
    ) -> str:
        return cast(
            str,
            _get_chart_template()["user"].format(
                sql=self.sql,
                question=self.question,
                rule=self.rule,
                chart_type=chart_type,
                schema=schema,
            ),
        )

    def analysis_sys_question(self) -> str:
        return cast(
            str,
            _get_analysis_template()["system"].format(
                lang=self.lang,
                terminologies=self.terminologies,
                custom_prompt=self.custom_prompt,
            ),
        )

    def analysis_user_question(self) -> str:
        return cast(
            str,
            _get_analysis_template()["user"].format(fields=self.fields, data=self.data),
        )

    def predict_sys_question(self) -> str:
        return cast(
            str,
            _get_predict_template()["system"].format(
                lang=self.lang, custom_prompt=self.custom_prompt
            ),
        )

    def predict_user_question(self) -> str:
        return cast(
            str,
            _get_predict_template()["user"].format(fields=self.fields, data=self.data),
        )

    def datasource_sys_question(self) -> str:
        return cast(str, _get_datasource_template()["system"].format(lang=self.lang))

    def datasource_user_question(self, datasource_list: str = "[]") -> str:
        return cast(
            str,
            _get_datasource_template()["user"].format(
                question=self.question, data=datasource_list
            ),
        )

    def guess_sys_question(self, articles_number: int = 4) -> str:
        return cast(
            str,
            _get_guess_question_template()["system"].format(
                lang=self.lang, articles_number=articles_number
            ),
        )

    def guess_user_question(self, old_questions: str = "[]") -> str:
        return cast(
            str,
            _get_guess_question_template()["user"].format(
                question=self.question,
                schema=self.db_schema,
                old_questions=old_questions,
            ),
        )

    def filter_sys_question(self) -> str:
        return cast(
            str,
            _get_permissions_template()["system"].format(
                lang=self.lang, engine=self.engine
            ),
        )

    def filter_user_question(self) -> str:
        return cast(
            str,
            _get_permissions_template()["user"].format(
                sql=self.sql, filter=self.filter
            ),
        )

    def dynamic_sys_question(self) -> str:
        return cast(
            str,
            _get_dynamic_template()["system"].format(
                lang=self.lang, engine=self.engine
            ),
        )

    def dynamic_user_question(self) -> str:
        return cast(
            str,
            _get_dynamic_template()["user"].format(
                sql=self.sql, sub_query=self.sub_query
            ),
        )


class ChatQuestion(AiModelQuestion):
    chat_id: int
    datasource_id: int | None = None


class ChatMcp(ChatQuestion):
    token: str


class ChatStart(BaseModel):
    username: str = Body(description="用户名")
    password: str = Body(description="密码")


class McpQuestion(BaseModel):
    question: str = Body(description="用户提问")
    chat_id: int = Body(description="会话ID")
    token: str = Body(description="token")
    stream: bool | None = Body(
        description="是否流式输出，默认为true开启, 关闭false则返回JSON对象",
        default=True,
    )
    lang: str | None = Body(description="语言：zh-CN|en|ko-KR", default="zh-CN")
    datasource_id: int | str | None = Body(
        description="数据源ID，仅当当前对话没有确定数据源时有效", default=None
    )


class AxisObj(BaseModel):
    name: str = ""
    value: str = ""
    type: str | None = None


class ExcelData(BaseModel):
    axis: list[AxisObj] = []
    data: list[dict[str, Any]] = []
    name: str = "Excel"


class McpAssistant(BaseModel):
    question: str = Body(description="用户提问")
    url: str = Body(description="第三方数据接口")
    authorization: str = Body(description="第三方接口凭证")
    stream: bool | None = Body(
        description="是否流式输出，默认为true开启, 关闭false则返回JSON对象",
        default=True,
    )
