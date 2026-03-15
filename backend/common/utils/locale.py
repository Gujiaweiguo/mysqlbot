import json
from pathlib import Path
from typing import Any, overload

from fastapi import Request


class I18n:
    def __init__(self, locale_dir: str = "locales"):
        self.locale_dir = Path(locale_dir)
        self.translations: dict[str, dict[str, Any]] = {}
        self.load_translations()

    def load_translations(self) -> None:
        if not self.locale_dir.exists():
            self.locale_dir.mkdir()
            return

        for lang_file in self.locale_dir.glob("*.json"):
            with open(lang_file, encoding="utf-8") as f:
                self.translations[lang_file.stem.lower()] = json.load(f)

    def get_language(
        self, request: Request | None = None, lang: str | None = None
    ) -> str:
        primary_lang: str | None = None
        if lang is not None:
            primary_lang = lang.lower()
        elif request is not None:
            accept_language = request.headers.get("accept-language", "en")
            primary_lang = accept_language.split(",")[0].lower()

        return primary_lang if primary_lang in self.translations else "zh-cn"

    @overload
    def __call__(
        self,
        request: Request,
        lang: str | None = None,
        *,
        key: None = None,
        **kwargs: Any,
    ) -> "I18nHelper": ...

    @overload
    def __call__(
        self,
        request: None = None,
        lang: str | None = None,
        *,
        key: None = None,
        **kwargs: Any,
    ) -> "I18nHelper": ...

    @overload
    def __call__(
        self,
        request: str,
        lang: str | None = None,
        *,
        key: None = None,
        **kwargs: Any,
    ) -> str: ...

    @overload
    def __call__(
        self,
        request: Request | None = None,
        lang: str | None = None,
        *,
        key: str,
        **kwargs: Any,
    ) -> str: ...

    def __call__(
        self,
        request: Request | str | None = None,
        lang: str | None = None,
        *,
        key: str | None = None,
        **kwargs: Any,
    ) -> "I18nHelper | str":
        if key is not None:
            helper = I18nHelper(
                self, request if isinstance(request, Request) else None, lang
            )
            return helper(key, **kwargs)

        if isinstance(request, str):
            helper = I18nHelper(self, None, lang)
            return helper(request, **kwargs)

        return I18nHelper(self, request, lang)


class I18nHelper:
    def __init__(
        self, i18n: I18n, request: Request | None = None, lang: str | None = None
    ):
        self.i18n = i18n
        self.request = request
        self.lang = i18n.get_language(request, lang)

    def _get_nested_translation(self, data: dict[str, Any], key_path: str) -> str:
        keys = key_path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return key_path  # 如果找不到，返回原键

        return current if isinstance(current, str) else key_path

    def __call__(self, arg_key: str, **kwargs: Any) -> str:
        lang_data = self.i18n.translations.get(self.lang, {})
        text = self._get_nested_translation(lang_data, arg_key)

        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text
