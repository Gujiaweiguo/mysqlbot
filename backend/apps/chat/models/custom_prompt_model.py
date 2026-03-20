from datetime import datetime
from enum import Enum
from typing import Any, cast

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Identity, JSON, Text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from apps.chat.models.chat_model import enum_values


class CustomPromptTypeEnum(str, Enum):
    GENERATE_SQL = "GENERATE_SQL"
    ANALYSIS = "ANALYSIS"
    PREDICT_DATA = "PREDICT_DATA"


class CustomPrompt(SQLModel, table=True):
    __tablename__ = cast(Any, "custom_prompt")

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger, Identity(always=True), nullable=False, primary_key=True
        ),
    )
    oid: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    type: CustomPromptTypeEnum | None = Field(
        default=None,
        sa_column=Column(
            SQLAlchemyEnum(
                CustomPromptTypeEnum,
                native_enum=False,
                values_callable=enum_values,
                length=20,
            ),
            nullable=True,
        ),
    )
    create_time: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=True)
    )
    name: str | None = Field(default=None, max_length=255, nullable=True)
    prompt: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    specific_ds: bool | None = Field(
        default=None, sa_column=Column(Boolean, nullable=True)
    )
    datasource_ids: list[object] | None = Field(
        default=None,
        sa_column=Column(
            JSON().with_variant(JSONB(astext_type=Text()), "postgresql"), nullable=True
        ),
    )
