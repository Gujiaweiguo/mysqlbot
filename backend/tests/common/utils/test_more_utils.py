import logging
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from common.utils.utils import (
    SQLBotLogUtil,
    extract_nested_json,
    setup_logging,
    deepcopy_ignore_extra,
    equals_ignore_case,
    generate_password_reset_token,
    get_domain_list,
    get_origin_from_referer,
    origin_match_domain,
    prepare_for_orjson,
    prepare_model_arg,
    verify_password_reset_token,
)


def build_request(referer: str | None) -> Request:
    headers = [] if referer is None else [(b"referer", referer.encode())]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": headers,
    }
    return Request(scope)


class TestUtilityHelpers:
    def test_password_reset_token_round_trip(self) -> None:
        token = generate_password_reset_token("demo@example.com")

        assert verify_password_reset_token(token) == "demo@example.com"
        assert verify_password_reset_token("bad-token") is None

    def test_deepcopy_ignore_extra_only_copies_shared_attributes(self) -> None:
        source = SimpleNamespace(name=["alice"], age=18, ignored="x")
        dest = SimpleNamespace(name=None, age=None)

        copied = deepcopy_ignore_extra(source, dest)

        assert copied.name == ["alice"]
        assert copied.age == 18
        source.name.append("bob")
        assert copied.name == ["alice"]

    def test_prepare_for_orjson_handles_nested_types(self) -> None:
        prepared = prepare_for_orjson({"raw": b"hi", "items": [b"x", {"ok": 1}]})

        assert prepared == {"raw": "aGk=", "items": ["eA==", {"ok": 1}]}
        assert prepare_for_orjson(None) is None

    def test_prepare_model_arg_parses_json_strings(self) -> None:
        assert prepare_model_arg('{"a": 1}') == {"a": 1}
        assert prepare_model_arg("[1, 2]") == [1, 2]
        assert prepare_model_arg("plain") == "plain"
        assert prepare_model_arg("{bad json") == "{bad json"
        assert prepare_model_arg(3) == 3
        assert prepare_model_arg("   [1]") == [1]

    def test_get_origin_from_referer_extracts_origin(self) -> None:
        assert (
            get_origin_from_referer(build_request("https://example.com/path"))
            == "https://example.com"
        )
        assert (
            get_origin_from_referer(build_request("http://example.com:8080/path"))
            == "http://example.com:8080"
        )
        assert get_origin_from_referer(build_request(None)) is None

    def test_domain_helpers(self) -> None:
        assert (
            origin_match_domain("https://a.com", "https://b.com;https://a.com/") is True
        )
        assert origin_match_domain("https://a.com", "") is False
        assert get_domain_list(" https://a.com/; https://b.com ,,") == [
            "https://a.com",
            "https://b.com",
        ]
        assert equals_ignore_case("Test", "demo", "test") is True
        assert equals_ignore_case(None, "demo", None) is True
        assert equals_ignore_case("Test", "demo") is False
        assert get_domain_list("") == []
        assert origin_match_domain("https://a.com", "https://b.com") is False

    def test_extract_nested_json_handles_mismatched_brackets(self) -> None:
        text = '{] prefix {"ok": true}'

        assert extract_nested_json(text) == '{"ok": true}'

    def test_extract_nested_json_skips_invalid_complete_json(self) -> None:
        text = 'prefix {"bad": } suffix {"ok": 1}'

        assert extract_nested_json(text) == '{"ok": 1}'

    @pytest.mark.parametrize(
        ("referer", "expected"),
        [
            ("https://example.com/path", "https://example.com"),
            ("http://example.com:8080/path", "http://example.com:8080"),
            ("https://example.com:443/path", "https://example.com"),
            ("notaurl", None),
        ],
    )
    def test_get_origin_from_referer_variants(
        self, referer: str, expected: str | None
    ) -> None:
        assert get_origin_from_referer(build_request(referer)) == expected

    def test_get_origin_from_referer_returns_original_on_parse_error(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            "common.utils.utils.urlparse",
            lambda _value: (_ for _ in ()).throw(ValueError("boom")),
        )

        assert (
            get_origin_from_referer(build_request("https://example.com"))
            == "https://example.com"
        )

    def test_sqlbotlogutil_get_logger_falls_back_when_frame_missing(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr("common.utils.utils.inspect.currentframe", lambda: None)

        logger = SQLBotLogUtil._get_logger()

        assert logger.name == "__main__"

    def test_equals_ignore_case_skips_none_candidates(self) -> None:
        assert equals_ignore_case("Test", None, "TEST") is True

    def test_setup_logging_and_log_util_methods(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        from common.utils import utils as utils_module

        monkeypatch.setattr(utils_module.settings, "LOG_DIR", str(tmp_path))
        monkeypatch.setattr(utils_module.settings, "LOG_FORMAT", "%(message)s")
        monkeypatch.setattr(utils_module.settings, "LOG_LEVEL", "DEBUG")
        monkeypatch.setattr(utils_module.settings, "SQL_DEBUG", True)

        root_logger = logging.getLogger()
        sql_logger = logging.getLogger("sqlalchemy.engine")
        original_root_handlers = list(root_logger.handlers)
        original_sql_handlers = list(sql_logger.handlers)
        root_logger.handlers.clear()
        sql_logger.handlers.clear()

        try:
            setup_logging()
            with caplog.at_level(logging.DEBUG):
                SQLBotLogUtil.debug("debug message")
                SQLBotLogUtil.info("info message")
                SQLBotLogUtil.warning("warn message")
                SQLBotLogUtil.error("error message", exc_info=False)
                SQLBotLogUtil.critical("critical message")

            assert root_logger.handlers
            assert sql_logger.handlers
            assert (tmp_path / "debug.log").exists()
            assert (tmp_path / "info.log").exists()
            assert (tmp_path / "warn.log").exists()
            assert (tmp_path / "error.log").exists()
        finally:
            root_logger.handlers = original_root_handlers
            sql_logger.handlers = original_sql_handlers

    def test_log_util_methods_noop_when_logger_disabled(self, monkeypatch) -> None:
        silent_logger = logging.getLogger("silent-test")
        silent_logger.setLevel(logging.CRITICAL + 10)

        monkeypatch.setattr(
            SQLBotLogUtil, "_get_logger", staticmethod(lambda: silent_logger)
        )

        SQLBotLogUtil.debug("debug message")
        SQLBotLogUtil.info("info message")
        SQLBotLogUtil.warning("warn message")
        SQLBotLogUtil.error("error message", exc_info=False)
        SQLBotLogUtil.exception("exception message")
        SQLBotLogUtil.critical("critical message")
