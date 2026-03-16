from datetime import datetime
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel
from sqlmodel import BigInteger, Field, SQLModel


class OperationModules(str, Enum):
    CHAT = "chat"  # 问数
    DATASOURCE = "datasource"  # 数据源
    DASHBOARD = "dashboard"  # 仪表板
    MEMBER = "member"  # 成员
    PERMISSION = "permission"  # 权限
    RULES = "rules"  # q组
    TERMINOLOGY = "terminology"  # 术语
    DATA_TRAINING = "data_training"  # SQL 示例库
    PROMPT_WORDS = "prompt_words"  # 自定义提示词
    USER = "user"  # 用户
    WORKSPACE = "workspace"  # 工作空间
    AI_MODEL = "ai_model"  # AI 模型
    APPLICATION = "application"  # 嵌入式管理 应用
    THEME = "theme"  # 外观配置
    PARAMS_SETTING = "params_setting"  # 参数配置
    API_KEY = "api_key"  # api key
    LOG_SETTING = "log_setting"  # api key
    SETTING = "setting"  # 设置
    SYSTEM_MANAGEMENT = "system_management"  # 系统管理
    OPT_LOG = "opt_log"  # 操作日志


class OperationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class OperationType(str, Enum):
    CREATE = "create"
    DELETE = "delete"
    UPDATE = "update"
    RESET_PWD = "reset_pwd"
    UPDATE_PWD = "update_pwd"
    UPDATE_STATUS = "update_status"
    UPDATE_TABLE_RELATION = "update_table_relation"
    EDIT = "edit"
    LOGIN = "login"
    VIEW = "view"
    EXPORT = "export"
    IMPORT = "import"
    ADD = "add"
    CREATE_OR_UPDATE = "create_or_update"
    ANALYSIS = "analysis"
    PREDICTION = "prediction"


class SystemLogsResource(SQLModel, table=True):
    __tablename__ = cast(Any, "sys_logs_resource")
    id: int | None = Field(default=None, primary_key=True)
    log_id: int | None = Field(default=None, sa_type=BigInteger)
    resource_id: str | None = Field(default=None)
    resource_name: str | None = Field(default=None)
    module: str | None = Field(default=None)


class SystemLog(SQLModel, table=True):
    __tablename__ = cast(Any, "sys_logs")
    id: int | None = Field(default=None, primary_key=True)
    operation_type: str | None = Field(default=None)
    operation_detail: str | None = Field(default=None)
    user_id: int | None = Field(default=None, sa_type=BigInteger)
    operation_status: str | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)
    execution_time: int = Field(
        default=0, description="执行时间(毫秒)", sa_type=BigInteger
    )
    error_message: str | None = Field(default=None)
    create_time: datetime = Field(default_factory=datetime.now)
    module: str | None = Field(default=None)
    oid: int | None = Field(default=None, sa_type=BigInteger)
    resource_id: str | None = Field(default=None)
    request_method: str | None = Field(default=None)
    request_path: str | None = Field(default=None)
    remark: str | None = Field(default=None)
    user_name: str | None = Field(default=None)
    resource_name: str | None = Field(default=None)


class SystemLogInfo(BaseModel):
    id: str = Field(default=None)
    operation_type_name: str = Field(default=None)
    operation_detail_info: str = Field(default=None)
    user_name: str = Field(default=None)
    resource_name: str = Field(default=None)
    operation_status: str = Field(default=None)
    ip_address: str | None = Field(default=None)
    create_time: datetime = Field(default_factory=datetime.now)
    oid_list: str = Field(default=None)
    remark: str = Field(default=None)


class SystemLogInfoResult(BaseModel):
    id: str = Field(default=None)
    operation_type_name: str = Field(default=None)
    operation_detail_info: str = Field(default=None)
    user_name: str = Field(default=None)
    resource_name: str = Field(default=None)
    operation_status: str = Field(default=None)
    operation_status_name: str = Field(default=None)
    ip_address: str | None = Field(default=None)
    create_time: datetime = Field(default_factory=datetime.now)
    oid_name: str = Field(default=None)
    oid: str = Field(default=None)
    error_message: str = Field(default=None)
    remark: str = Field(default=None)
