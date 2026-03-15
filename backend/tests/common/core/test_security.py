from datetime import timedelta

import jwt

from common.core import security


class TestSecurity:
    def test_create_access_token_round_trip(self) -> None:
        token = security.create_access_token({"sub": "demo"}, timedelta(minutes=5))
        decoded = jwt.decode(
            token,
            security.settings.SECRET_KEY,
            algorithms=[security.ALGORITHM],
        )

        assert decoded["sub"] == "demo"
        assert "exp" in decoded

    def test_password_hash_and_verify(self) -> None:
        hashed = security.get_password_hash("Password1!")

        assert hashed != "Password1!"
        assert security.verify_password("Password1!", hashed) is True
        assert security.verify_password("wrong", hashed) is False

    def test_md5_helpers(self) -> None:
        md5_password = security.md5pwd("abc123")

        assert security.verify_md5pwd("abc123", md5_password) is True
        assert security.verify_md5pwd("other", md5_password) is False

    def test_default_password_helpers(self) -> None:
        assert security.default_pwd() == security.settings.DEFAULT_PWD
        assert security.default_md5_pwd() == security.md5pwd(
            security.settings.DEFAULT_PWD
        )
