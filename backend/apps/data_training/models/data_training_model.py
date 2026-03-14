from datetime import datetime
from importlib import import_module
from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Identity, Text
from sqlmodel import Field, SQLModel

VECTOR = cast(Any, import_module("pgvector.sqlalchemy").VECTOR)


class DataTraining(SQLModel, table=True):
    __tablename__ = cast(Any, "data_training")

    id: int | None = Field(
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True)
    )
    oid: int | None = Field(sa_column=Column(BigInteger, nullable=True, default=1))
    datasource: int | None = Field(sa_column=Column(BigInteger, nullable=True))
    create_time: datetime | None = Field(
        sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    question: str | None = Field(max_length=255)
    description: str | None = Field(sa_column=Column(Text, nullable=True))
    embedding: list[float] | None = Field(sa_column=Column(VECTOR(), nullable=True))
    enabled: bool | None = Field(sa_column=Column(Boolean, default=True))
    advanced_application: int | None = Field(
        sa_column=Column(BigInteger, nullable=True)
    )


class DataTrainingInfo(BaseModel):
    id: int | None = None
    oid: int | None = None
    datasource: int | None = None
    datasource_name: str | None = None
    create_time: datetime | None = None
    question: str | None = None
    description: str | None = None
    enabled: bool | None = True
    advanced_application: int | None = None
    advanced_application_name: str | None = None


class DataTrainingInfoResult(BaseModel):
    id: str | None = None
    oid: str | None = None
    datasource: int | None = None
    datasource_name: str | None = None
    create_time: datetime | None = None
    question: str | None = None
    description: str | None = None
    enabled: bool | None = True
    advanced_application: str | None = None
    advanced_application_name: str | None = None
