from __future__ import annotations


import pytest


class TestCryptoWrapperContract:
    @pytest.mark.asyncio
    async def test_crypto_wrappers_delegate_to_compat_entrypoints(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import common.utils.crypto as crypto_module

        calls: list[tuple[str, str]] = []

        async def fake_sqlbot_decrypt(text: str) -> str:
            calls.append(("decrypt", text))
            return f"decrypted::{text}"

        async def fake_sqlbot_encrypt(text: str) -> str:
            calls.append(("encrypt", text))
            return f"encrypted::{text}"

        monkeypatch.setattr(crypto_module, "compat_sqlbot_decrypt", fake_sqlbot_decrypt)
        monkeypatch.setattr(crypto_module, "compat_sqlbot_encrypt", fake_sqlbot_encrypt)

        assert await crypto_module.sqlbot_decrypt("alice") == "decrypted::alice"
        assert await crypto_module.sqlbot_encrypt("secret") == "encrypted::secret"
        assert calls == [("decrypt", "alice"), ("encrypt", "secret")]


class TestAesCryptoWrapperContract:
    def test_aes_wrappers_use_secret_key_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import common.utils.aes_crypto as aes_crypto_module

        calls: list[tuple[str, tuple[str, str | None, str | None]]] = []

        def fake_sqlbot_aes_encrypt(text: str, key: str | None = None) -> str:
            calls.append(("sqlbot_aes_encrypt", (text, key, None)))
            return f"enc::{text}::{key}"

        def fake_sqlbot_aes_decrypt(text: str, key: str | None = None) -> str:
            calls.append(("sqlbot_aes_decrypt", (text, key, None)))
            return f"dec::{text}::{key}"

        def fake_simple_aes_encrypt(
            text: str, key: str | None = None, ivtext: str | None = None
        ) -> str:
            calls.append(("simple_aes_encrypt", (text, key, ivtext)))
            return f"simple-enc::{text}::{key}::{ivtext}"

        def fake_simple_aes_decrypt(
            text: str, key: str | None = None, ivtext: str | None = None
        ) -> str:
            calls.append(("simple_aes_decrypt", (text, key, ivtext)))
            return f"simple-dec::{text}::{key}::{ivtext}"

        monkeypatch.setattr(
            aes_crypto_module, "compat_sqlbot_aes_encrypt", fake_sqlbot_aes_encrypt
        )
        monkeypatch.setattr(
            aes_crypto_module, "compat_sqlbot_aes_decrypt", fake_sqlbot_aes_decrypt
        )
        monkeypatch.setattr(
            aes_crypto_module, "compat_simple_aes_encrypt", fake_simple_aes_encrypt
        )
        monkeypatch.setattr(
            aes_crypto_module, "compat_simple_aes_decrypt", fake_simple_aes_decrypt
        )

        assert aes_crypto_module.sqlbot_aes_encrypt("secret") == "enc::secret::None"
        assert aes_crypto_module.sqlbot_aes_decrypt("cipher") == "dec::cipher::None"
        assert (
            aes_crypto_module.simple_aes_encrypt("demo")
            == "simple-enc::demo::None::None"
        )
        assert (
            aes_crypto_module.simple_aes_decrypt("blob")
            == "simple-dec::blob::None::None"
        )
        assert calls == [
            ("sqlbot_aes_encrypt", ("secret", None, None)),
            ("sqlbot_aes_decrypt", ("cipher", None, None)),
            ("simple_aes_encrypt", ("demo", None, None)),
            ("simple_aes_decrypt", ("blob", None, None)),
        ]

    def test_simple_aes_wrappers_accept_explicit_key_and_iv(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import common.utils.aes_crypto as aes_crypto_module

        calls: list[tuple[str, tuple[str, str | None, str | None]]] = []

        def fake_simple_aes_encrypt(
            text: str, key: str | None = None, ivtext: str | None = None
        ) -> str:
            calls.append(("simple_aes_encrypt", (text, key, ivtext)))
            return f"simple-enc::{text}::{key}::{ivtext}"

        def fake_simple_aes_decrypt(
            text: str, key: str | None = None, ivtext: str | None = None
        ) -> str:
            calls.append(("simple_aes_decrypt", (text, key, ivtext)))
            return f"simple-dec::{text}::{key}::{ivtext}"

        monkeypatch.setattr(
            aes_crypto_module, "compat_simple_aes_encrypt", fake_simple_aes_encrypt
        )
        monkeypatch.setattr(
            aes_crypto_module, "compat_simple_aes_decrypt", fake_simple_aes_decrypt
        )

        assert (
            aes_crypto_module.simple_aes_encrypt(
                "demo", key="custom-key", ivtext="custom-iv"
            )
            == "simple-enc::demo::custom-key::custom-iv"
        )
        assert (
            aes_crypto_module.simple_aes_decrypt(
                "blob", key="custom-key", ivtext="custom-iv"
            )
            == "simple-dec::blob::custom-key::custom-iv"
        )
        assert calls == [
            ("simple_aes_encrypt", ("demo", "custom-key", "custom-iv")),
            ("simple_aes_decrypt", ("blob", "custom-key", "custom-iv")),
        ]
