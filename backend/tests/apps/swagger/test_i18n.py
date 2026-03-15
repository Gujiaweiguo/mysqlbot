import json

import pytest

from apps.swagger import i18n as swagger_i18n


class TestSwaggerI18n:
    def test_load_translation_and_fallback(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(swagger_i18n, "LOCALES_DIR", tmp_path)
        swagger_i18n._translations_cache.clear()
        (tmp_path / "en.json").write_text(
            json.dumps({"hello": "Hello"}), encoding="utf-8"
        )

        assert swagger_i18n.load_translation("en") == {"hello": "Hello"}
        assert swagger_i18n.load_translation("zh") == {"hello": "Hello"}
        assert swagger_i18n.get_translation("en") == {"hello": "Hello"}

    def test_load_translation_raises_for_missing_default(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(swagger_i18n, "LOCALES_DIR", tmp_path)
        swagger_i18n._translations_cache.clear()

        with pytest.raises(FileNotFoundError):
            swagger_i18n.load_translation("en")

    def test_load_translation_rejects_invalid_json_payloads(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(swagger_i18n, "LOCALES_DIR", tmp_path)
        swagger_i18n._translations_cache.clear()
        (tmp_path / "en.json").write_text("[]", encoding="utf-8")

        with pytest.raises(ValueError, match="JSON object"):
            swagger_i18n.load_translation("en")

    def test_load_translation_rejects_malformed_json(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(swagger_i18n, "LOCALES_DIR", tmp_path)
        swagger_i18n._translations_cache.clear()
        (tmp_path / "en.json").write_text("{bad json", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid JSON"):
            swagger_i18n.load_translation("en")
