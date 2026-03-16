# Author: Junjun
# Date: 2026/1/26

from datetime import datetime
from typing import Any, cast

from sqlalchemy import BigInteger, Column, DateTime, Identity
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class SystemVariable(SQLModel, table=True):
    __tablename__ = cast(Any, "system_variable")
    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger, Identity(always=True), nullable=False, primary_key=True
        ),
    )
    name: str = Field(max_length=128, nullable=False)
    var_type: str = Field(max_length=128, nullable=False)
    type: str = Field(max_length=128, nullable=False)
    value: list[Any] = Field(sa_column=Column(JSONB, nullable=True))
    create_time: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    create_by: int | None = Field(
        default=None, sa_column=Column(BigInteger(), nullable=True)
    )
