from common.core.security_config import (
    SecurityConfig,
    get_security_config,
    validate_password_strength,
)


class TestSecurityConfig:
    def test_get_security_config_returns_defaults(self) -> None:
        config = get_security_config()

        assert config.verify_ssl_certificates is True
        assert config.default_request_timeout == 30
        assert config.min_password_length == 8

    def test_validate_password_strength_rejects_short_password(self) -> None:
        valid, message = validate_password_strength("Ab1!")

        assert valid is False
        assert "at least 8 characters" in message

    def test_validate_password_strength_rejects_missing_uppercase(self) -> None:
        valid, message = validate_password_strength("lowercase1!")

        assert valid is False
        assert "uppercase" in message

    def test_validate_password_strength_rejects_missing_lowercase(self) -> None:
        valid, message = validate_password_strength("UPPERCASE1!")

        assert valid is False
        assert "lowercase" in message

    def test_validate_password_strength_rejects_missing_digit(self) -> None:
        valid, message = validate_password_strength("Password!")

        assert valid is False
        assert "digit" in message

    def test_validate_password_strength_rejects_missing_special_character(self) -> None:
        valid, message = validate_password_strength("Password1")

        assert valid is False
        assert "special character" in message

    def test_validate_password_strength_accepts_valid_password(self) -> None:
        valid, message = validate_password_strength("Password1!")

        assert valid is True
        assert message == ""

    def test_validate_password_strength_honors_custom_config(self) -> None:
        config = SecurityConfig(
            min_password_length=4,
            require_password_uppercase=False,
            require_password_lowercase=False,
            require_password_digit=False,
            require_password_special=False,
        )

        valid, message = validate_password_strength("abcd", config)

        assert valid is True
        assert message == ""
