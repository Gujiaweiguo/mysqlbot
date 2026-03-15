import json

from starlette.requests import Request

from common.utils.locale import I18n, I18nHelper


def build_request(accept_language: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(b"accept-language", accept_language.encode())],
    }
    return Request(scope)


class TestI18n:
    def test_missing_locale_dir_is_created(self, tmp_path) -> None:
        locale_dir = tmp_path / "locales"
        i18n = I18n(str(locale_dir))

        assert locale_dir.exists() is True
        assert i18n.translations == {}

    def test_get_language_and_helper_calls(self, tmp_path) -> None:
        locale_dir = tmp_path / "locales"
        locale_dir.mkdir()
        (locale_dir / "en.json").write_text(
            json.dumps({"greet": {"hello": "Hello {name}"}}),
            encoding="utf-8",
        )

        i18n = I18n(str(locale_dir))
        helper = i18n(None, lang="en")

        assert isinstance(helper, I18nHelper)
        assert i18n.get_language(lang="EN") == "en"
        assert i18n.get_language(request=build_request("fr-FR,fr")) == "zh-cn"
        assert helper("greet.hello", name="Alice") == "Hello Alice"
        assert helper("greet.hello", missing="x") == "Hello {name}"
        assert i18n("greet.hello", lang="en", name="Bob") == "Hello Bob"
        assert (
            i18n(request=None, lang="en", key="greet.hello", name="Eve") == "Hello Eve"
        )

    def test_nested_translation_falls_back_to_key(self, tmp_path) -> None:
        locale_dir = tmp_path / "locales"
        locale_dir.mkdir()
        (locale_dir / "en.json").write_text(
            json.dumps({"flat": "value"}), encoding="utf-8"
        )

        helper = I18n(str(locale_dir))(None, lang="en")

        assert helper("flat") == "value"
        assert helper("missing.path") == "missing.path"
