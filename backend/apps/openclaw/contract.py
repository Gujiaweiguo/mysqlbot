from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "v1"
CONTRACT_ROLE_STATEMENT = (
    "mysqlbot is the sole NL-query/analysis engine; OpenClaw is a caller only."
)
DEFAULT_TRANSPORT = "http-json"
DEFAULT_TIMEOUT_SECONDS = 120
STREAMING_SUPPORT = False
AUTH_HEADER = "X-SQLBOT-ASK-TOKEN"
AUTH_SCHEME = "sk"


class OpenClawOperation:
    SESSION_BIND: ClassVar[str] = "session.bind"
    QUESTION_EXECUTE: ClassVar[str] = "question.execute"
    ANALYSIS_EXECUTE: ClassVar[str] = "analysis.execute"
    DATASOURCE_LIST: ClassVar[str] = "datasource.list"


class OpenClawErrorCode:
    AUTH_INVALID: ClassVar[str] = "AUTH_INVALID"
    AUTH_EXPIRED: ClassVar[str] = "AUTH_EXPIRED"
    AUTH_DISABLED: ClassVar[str] = "AUTH_DISABLED"
    VALIDATION_ERROR: ClassVar[str] = "VALIDATION_ERROR"
    DATASOURCE_NOT_FOUND: ClassVar[str] = "DATASOURCE_NOT_FOUND"
    SESSION_INVALID: ClassVar[str] = "SESSION_INVALID"
    EXECUTION_TIMEOUT: ClassVar[str] = "EXECUTION_TIMEOUT"
    CONCURRENCY_EXCEEDED: ClassVar[str] = "CONCURRENCY_EXCEEDED"
    INTEGRATION_DISABLED: ClassVar[str] = "INTEGRATION_DISABLED"
    EXECUTION_FAILURE: ClassVar[str] = "EXECUTION_FAILURE"
    LLM_FAILURE: ClassVar[str] = "LLM_FAILURE"
    INTERNAL_ERROR: ClassVar[str] = "INTERNAL_ERROR"


class OpenClawContractBase(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    version: str = Field(default=CONTRACT_VERSION)


class OpenClawSessionBindRequest(OpenClawContractBase):
    operation: str = Field(default=OpenClawOperation.SESSION_BIND)
    conversation_id: str = Field(min_length=1)
    chat_id: int | None = None
    datasource_id: int | None = None
    language: str = Field(default="zh-CN", min_length=2)


class OpenClawQuestionRequest(OpenClawContractBase):
    operation: str = Field(default=OpenClawOperation.QUESTION_EXECUTE)
    conversation_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    chat_id: int | None = None
    datasource_id: int | None = None
    language: str = Field(default="zh-CN", min_length=2)


class OpenClawAnalysisRequest(OpenClawContractBase):
    operation: str = Field(default=OpenClawOperation.ANALYSIS_EXECUTE)
    conversation_id: str = Field(min_length=1)
    chat_id: int = Field(gt=0)
    record_id: int = Field(gt=0)
    action_type: str = Field(default="analysis", min_length=1)
    language: str = Field(default="zh-CN", min_length=2)


class OpenClawDatasourceListRequest(OpenClawContractBase):
    operation: str = Field(default=OpenClawOperation.DATASOURCE_LIST)
    conversation_id: str = Field(min_length=1)
    language: str = Field(default="zh-CN", min_length=2)


class OpenClawSuccessEnvelope(OpenClawContractBase):
    status: str = Field(default="success")
    operation: str
    data: dict[str, object]


class OpenClawErrorEnvelope(OpenClawContractBase):
    status: str = Field(default="error")
    operation: str
    error_code: str
    message: str = Field(min_length=1)
    detail: dict[str, object] | None = None


def all_openclaw_operations() -> tuple[str, ...]:
    return (
        OpenClawOperation.SESSION_BIND,
        OpenClawOperation.QUESTION_EXECUTE,
        OpenClawOperation.ANALYSIS_EXECUTE,
        OpenClawOperation.DATASOURCE_LIST,
    )


def all_openclaw_error_codes() -> tuple[str, ...]:
    return (
        OpenClawErrorCode.AUTH_INVALID,
        OpenClawErrorCode.AUTH_EXPIRED,
        OpenClawErrorCode.AUTH_DISABLED,
        OpenClawErrorCode.VALIDATION_ERROR,
        OpenClawErrorCode.DATASOURCE_NOT_FOUND,
        OpenClawErrorCode.SESSION_INVALID,
        OpenClawErrorCode.EXECUTION_TIMEOUT,
        OpenClawErrorCode.CONCURRENCY_EXCEEDED,
        OpenClawErrorCode.INTEGRATION_DISABLED,
        OpenClawErrorCode.EXECUTION_FAILURE,
        OpenClawErrorCode.LLM_FAILURE,
        OpenClawErrorCode.INTERNAL_ERROR,
    )
