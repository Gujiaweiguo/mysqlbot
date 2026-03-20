from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from typing import Any, cast

import pytest
from sqlmodel import SQLModel

from apps.chat.crud.custom_prompt import find_custom_prompts, get_custom_prompt_type
from apps.chat.models.custom_prompt_model import CustomPrompt


@pytest.fixture
def custom_prompt_tables(test_db_engine: Any) -> Generator[None, None, None]:
    tables = [cast(Any, CustomPrompt).__table__]
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)
    SQLModel.metadata.create_all(test_db_engine, tables=tables)
    yield
    SQLModel.metadata.drop_all(test_db_engine, tables=tables)


def test_find_custom_prompts_returns_oid_scoped_generate_sql_prompt(
    custom_prompt_tables: None,
    test_db: Any,
) -> None:
    test_db.add(
        CustomPrompt(
            id=1,
            oid=8,
            type=get_custom_prompt_type("GENERATE_SQL"),
            create_time=datetime.now(),
            name="sql",
            prompt="Use finance naming",
            specific_ds=False,
            datasource_ids=None,
        )
    )
    test_db.commit()

    prompt_text, prompt_list = find_custom_prompts(
        test_db,
        get_custom_prompt_type("GENERATE_SQL"),
        8,
        None,
    )

    assert prompt_text == "Use finance naming"
    assert [item["name"] for item in prompt_list] == ["sql"]


def test_find_custom_prompts_includes_matching_datasource_scoped_analysis_prompt(
    custom_prompt_tables: None,
    test_db: Any,
) -> None:
    test_db.add(
        CustomPrompt(
            id=1,
            oid=8,
            type=get_custom_prompt_type("ANALYSIS"),
            create_time=datetime.now(),
            name="general",
            prompt="General analysis guidance",
            specific_ds=False,
            datasource_ids=None,
        )
    )
    test_db.add(
        CustomPrompt(
            id=2,
            oid=8,
            type=get_custom_prompt_type("ANALYSIS"),
            create_time=datetime.now(),
            name="scoped",
            prompt="Datasource-specific analysis guidance",
            specific_ds=True,
            datasource_ids=[55],
        )
    )
    test_db.commit()

    prompt_text, prompt_list = find_custom_prompts(
        test_db,
        get_custom_prompt_type("ANALYSIS"),
        8,
        55,
    )

    assert prompt_text == (
        "General analysis guidance\n\nDatasource-specific analysis guidance"
    )
    assert [item["name"] for item in prompt_list] == ["general", "scoped"]


def test_find_custom_prompts_returns_empty_when_no_predict_prompt_matches(
    custom_prompt_tables: None,
    test_db: Any,
) -> None:
    prompt_text, prompt_list = find_custom_prompts(
        test_db,
        get_custom_prompt_type("PREDICT_DATA"),
        99,
        12,
    )

    assert prompt_text == ""
    assert prompt_list == []
