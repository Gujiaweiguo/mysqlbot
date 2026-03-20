from __future__ import annotations

import pytest

from apps.chat.task import llm


def test_is_license_valid_uses_compat_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "is_license_valid", lambda: False)

    assert llm._is_license_valid() is False
