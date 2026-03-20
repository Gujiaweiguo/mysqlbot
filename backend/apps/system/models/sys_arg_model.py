from typing import Any, cast

from sqlmodel import Field

from common.core.models import SnowflakeBase


class SysArgBase:
    pkey: str = Field(max_length=255, nullable=False)
    pval: str | None = Field(default=None, max_length=255, nullable=True)
    ptype: str = Field(default="str", max_length=255, nullable=False)
    sort_no: int = Field(default=1, nullable=False)


class SysArgModel(SnowflakeBase, SysArgBase, table=True):
    __tablename__ = cast(Any, "sys_arg")
