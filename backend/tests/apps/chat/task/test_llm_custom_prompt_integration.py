from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlmodel import Session

from apps.chat.models.chat_model import OperationEnum
from apps.chat.task import llm


def test_filter_custom_prompts_populates_prompt_and_log_when_license_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "_is_license_valid", lambda: True)
    monkeypatch.setattr(
        llm,
        "_find_custom_prompts",
        lambda *_args: ("prompt body", [{"name": "prompt-1"}]),
    )
    monkeypatch.setattr(llm, "start_log", lambda **_kwargs: "started")
    monkeypatch.setattr(
        llm,
        "end_log",
        lambda **_kwargs: {"state": "ended", "full_message": _kwargs["full_message"]},
    )

    service = llm.LLMService.__new__(llm.LLMService)
    service.current_assistant = None
    service.current_user = cast(Any, SimpleNamespace(oid=7))
    service.current_logs = {}
    service.record = cast(Any, SimpleNamespace(id=99))
    service.chat_question = cast(Any, SimpleNamespace(custom_prompt=""))

    service.filter_custom_prompts(cast(Session, object()), object(), oid=7, ds_id=3)

    assert service.chat_question.custom_prompt == "prompt body"
    assert cast(Any, service.current_logs[OperationEnum.FILTER_CUSTOM_PROMPT]) == {
        "state": "ended",
        "full_message": [{"name": "prompt-1"}],
    }


def test_filter_custom_prompts_skips_lookup_when_license_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []

    monkeypatch.setattr(llm, "_is_license_valid", lambda: False)

    def fake_find_custom_prompts(*_args: object) -> tuple[str, list[dict[str, object]]]:
        called.append("lookup")
        return "prompt body", []

    monkeypatch.setattr(llm, "_find_custom_prompts", fake_find_custom_prompts)

    service = llm.LLMService.__new__(llm.LLMService)
    service.current_assistant = None
    service.current_user = cast(Any, SimpleNamespace(oid=7))
    service.current_logs = {}
    service.record = cast(Any, SimpleNamespace(id=99))
    service.chat_question = cast(Any, SimpleNamespace(custom_prompt=""))

    service.filter_custom_prompts(cast(Session, object()), object(), oid=7, ds_id=3)

    assert service.chat_question.custom_prompt == ""
    assert called == []
    assert OperationEnum.FILTER_CUSTOM_PROMPT not in service.current_logs
