from datetime import datetime
from typing import Any, cast

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Identity, Integer, Text
from sqlmodel import Field, SQLModel


class DsPermission(SQLModel, table=True):
    __tablename__ = cast(Any, "ds_permission")

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger, Identity(always=True), nullable=False, primary_key=True
        ),
    )
    enable: bool = Field(sa_column=Column(Boolean, nullable=False))
    name: str | None = Field(default=None, max_length=128, nullable=True)
    auth_target_type: str | None = Field(default=None, max_length=128, nullable=True)
    auth_target_id: int | None = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    type: str = Field(max_length=64, nullable=False)
    ds_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    table_id: int | None = Field(
        default=None, sa_column=Column(BigInteger, nullable=True)
    )
    expression_tree: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    permissions: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    white_list_user: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    create_time: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )


class DsRules(SQLModel, table=True):
    __tablename__ = cast(Any, "ds_rules")

    id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, Identity(always=True), nullable=False, primary_key=True
        ),
    )
    enable: bool = Field(sa_column=Column(Boolean, nullable=False))
    name: str = Field(max_length=128, nullable=False)
    description: str | None = Field(default=None, max_length=512, nullable=True)
    permission_list: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    user_list: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    white_list_user: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    create_time: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    oid: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
