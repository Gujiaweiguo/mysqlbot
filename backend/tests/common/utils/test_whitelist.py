from common.core.config import settings
from common.utils.whitelist import WhitelistChecker


class TestWhitelistChecker:
    def test_matches_direct_and_prefixed_paths(self) -> None:
        checker = WhitelistChecker(["/health", "/assets/*"])

        assert checker.is_whitelisted("/health") is True
        assert checker.is_whitelisted(f"{settings.API_V1_STR}/health") is True
        assert checker.is_whitelisted("/assets/app.js") is True

    def test_add_path_supports_dynamic_wildcards(self) -> None:
        checker = WhitelistChecker(["/health"])
        checker.add_path("/docs/*")

        assert checker.is_whitelisted("/docs/index.html") is True

    def test_rejects_unknown_path(self) -> None:
        checker = WhitelistChecker(["/health"])

        assert checker.is_whitelisted("/private") is False

    def test_handles_context_prefix_and_duplicate_additions(self, monkeypatch) -> None:
        checker = WhitelistChecker(["/health"])
        monkeypatch.setattr("common.utils.whitelist.settings.CONTEXT_PATH", "/ctx")
        checker.add_path("/health")

        assert checker.is_whitelisted("/ctx/health") is True

    def test_logs_invalid_regex_patterns(self, monkeypatch) -> None:
        captured: list[str] = []
        monkeypatch.setattr(
            "common.utils.whitelist.SQLBotLogUtil.error",
            lambda msg: captured.append(msg),
        )

        WhitelistChecker(["*["])

        assert captured

    def test_treats_api_prefix_root_as_root_path(self) -> None:
        checker = WhitelistChecker(["/"])

        assert checker.is_whitelisted(settings.API_V1_STR) is True

    def test_duplicate_wildcard_path_does_not_break_checker(self) -> None:
        checker = WhitelistChecker(["/docs/*"])
        checker.add_path("/docs/*")

        assert checker.is_whitelisted("/docs/page") is True

    def test_add_plain_path_without_wildcard(self) -> None:
        checker = WhitelistChecker([])
        checker.add_path("/plain")

        assert checker.is_whitelisted("/plain") is True
