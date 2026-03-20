"""Tests for first-party crypto implementation."""

from __future__ import annotations

import base64
import os

import pytest

from common.xpack_compat.crypto_first_party import (
    FirstPartyAesCryptoProvider,
    FirstPartyCryptoProvider,
    decrypt_from_single_string,
    encrypt_to_single_string,
    simple_aes_decrypt,
    simple_aes_encrypt,
)


class TestFirstPartyCryptoProvider:
    """Test FirstPartyCryptoProvider async encryption."""

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_roundtrip(self) -> None:
        provider = FirstPartyCryptoProvider()
        plaintext = "test_secret_value"

        encrypted = await provider.sqlbot_encrypt(plaintext)
        decrypted = await provider.sqlbot_decrypt(encrypted)

        assert decrypted == plaintext

    @pytest.mark.asyncio
    async def test_encrypt_produces_different_ciphertext(self) -> None:
        provider = FirstPartyCryptoProvider()
        plaintext = "same_value"

        encrypted1 = await provider.sqlbot_encrypt(plaintext)
        encrypted2 = await provider.sqlbot_encrypt(plaintext)

        assert encrypted1 != encrypted2
        assert await provider.sqlbot_decrypt(encrypted1) == plaintext
        assert await provider.sqlbot_decrypt(encrypted2) == plaintext

    @pytest.mark.asyncio
    async def test_encrypt_unicode(self) -> None:
        provider = FirstPartyCryptoProvider()
        plaintext = "用户名密码"

        encrypted = await provider.sqlbot_encrypt(plaintext)
        decrypted = await provider.sqlbot_decrypt(encrypted)

        assert decrypted == plaintext

    @pytest.mark.asyncio
    async def test_encrypt_special_chars(self) -> None:
        provider = FirstPartyCryptoProvider()
        plaintext = "p@ssw0rd!#$%^&*()"

        encrypted = await provider.sqlbot_encrypt(plaintext)
        decrypted = await provider.sqlbot_decrypt(encrypted)

        assert decrypted == plaintext

    @pytest.mark.asyncio
    async def test_encrypt_format_is_base64_with_iv(self) -> None:
        provider = FirstPartyCryptoProvider()
        plaintext = "format_test"

        encrypted = await provider.sqlbot_encrypt(plaintext)
        raw = base64.b64decode(encrypted)

        assert len(raw) > 16
        assert raw[:16] != b"\x00" * 16


class TestFirstPartyAesCryptoProvider:
    """Test FirstPartyAesCryptoProvider AES operations."""

    def test_sqlbot_aes_roundtrip(self) -> None:
        provider = FirstPartyAesCryptoProvider()
        plaintext = "api_key_secret"

        encrypted = provider.sqlbot_aes_encrypt(plaintext)
        decrypted = provider.sqlbot_aes_decrypt(encrypted)

        assert decrypted == plaintext

    def test_sqlbot_aes_with_custom_key(self) -> None:
        provider = FirstPartyAesCryptoProvider()
        plaintext = "custom_key_test"
        custom_key = "my_32_character_secret_key_here"

        encrypted = provider.sqlbot_aes_encrypt(plaintext, key=custom_key)
        decrypted = provider.sqlbot_aes_decrypt(encrypted, key=custom_key)

        assert decrypted == plaintext

    def test_simple_aes_roundtrip(self) -> None:
        provider = FirstPartyAesCryptoProvider()
        plaintext = "database_password"

        encrypted = provider.simple_aes_encrypt(plaintext)
        decrypted = provider.simple_aes_decrypt(encrypted)

        assert decrypted == plaintext

    def test_simple_aes_deterministic(self) -> None:
        provider = FirstPartyAesCryptoProvider()
        plaintext = "deterministic_value"

        encrypted1 = provider.simple_aes_encrypt(plaintext)
        encrypted2 = provider.simple_aes_encrypt(plaintext)

        assert encrypted1 == encrypted2

    def test_simple_aes_with_custom_key_and_iv(self) -> None:
        provider = FirstPartyAesCryptoProvider()
        plaintext = "custom_params"
        custom_key = "32_character_key_for_aes_256____"
        custom_iv = "16_char_iv_12345"

        encrypted = provider.simple_aes_encrypt(
            plaintext, key=custom_key, ivtext=custom_iv
        )
        decrypted = provider.simple_aes_decrypt(
            encrypted, key=custom_key, ivtext=custom_iv
        )

        assert decrypted == plaintext


class TestEncryptToSingleString:
    """Test encrypt_to_single_string function."""

    def test_roundtrip(self) -> None:
        key = "test_secret_key"
        plaintext = "my_secret_data"

        encrypted = encrypt_to_single_string(plaintext, key)
        decrypted = decrypt_from_single_string(encrypted, key)

        assert decrypted == plaintext

    def test_produces_base64(self) -> None:
        key = "test_key"
        plaintext = "data"

        encrypted = encrypt_to_single_string(plaintext, key)

        base64.b64decode(encrypted)

    def test_different_ciphertext_same_plaintext(self) -> None:
        key = "test_key"
        plaintext = "same"

        encrypted1 = encrypt_to_single_string(plaintext, key)
        encrypted2 = encrypt_to_single_string(plaintext, key)

        assert encrypted1 != encrypted2
        assert decrypt_from_single_string(encrypted1, key) == plaintext
        assert decrypt_from_single_string(encrypted2, key) == plaintext

    def test_wrong_key_fails(self) -> None:
        key = "correct_key"
        wrong_key = "wrong_key___"
        plaintext = "secret"

        encrypted = encrypt_to_single_string(plaintext, key)

        with pytest.raises(Exception):
            decrypt_from_single_string(encrypted, wrong_key)


class TestSimpleAesEncrypt:
    """Test simple_aes_encrypt function."""

    def test_roundtrip(self) -> None:
        key = "32_character_key_for_aes_256____"
        iv = "16_char_iv_12345"
        plaintext = "test_data"

        encrypted = simple_aes_encrypt(plaintext, key, iv)
        decrypted = simple_aes_decrypt(encrypted, key, iv)

        assert decrypted == plaintext

    def test_deterministic(self) -> None:
        key = "32_character_key_for_aes_256____"
        iv = "16_char_iv_12345"
        plaintext = "same_every_time"

        encrypted1 = simple_aes_encrypt(plaintext, key, iv)
        encrypted2 = simple_aes_encrypt(plaintext, key, iv)

        assert encrypted1 == encrypted2

    def test_different_iv_different_ciphertext(self) -> None:
        key = "32_character_key_for_aes_256____"
        plaintext = "same_data"

        encrypted1 = simple_aes_encrypt(plaintext, key, "iv_number_one___")
        encrypted2 = simple_aes_encrypt(plaintext, key, "iv_number_two___")

        assert encrypted1 != encrypted2

    def test_key_truncation(self) -> None:
        long_key = "a" * 64
        plaintext = "test"

        encrypted = simple_aes_encrypt(plaintext, long_key, "16_char_iv_12345")
        decrypted = simple_aes_decrypt(encrypted, long_key, "16_char_iv_12345")

        assert decrypted == plaintext

    def test_key_padding(self) -> None:
        short_key = "short"
        plaintext = "test"

        encrypted = simple_aes_encrypt(plaintext, short_key, "16_char_iv_12345")
        decrypted = simple_aes_decrypt(encrypted, short_key, "16_char_iv_12345")

        assert decrypted == plaintext


class TestProviderSwitch:
    """Test that provider switch mechanism works."""

    def test_first_party_provider_used_by_default(self) -> None:
        from common.xpack_compat import providers

        providers._get_first_party_crypto_provider.cache_clear()
        providers._get_first_party_aes_crypto_provider.cache_clear()

        crypto_provider = providers.get_crypto_provider()
        aes_provider = providers.get_aes_crypto_provider()

        assert isinstance(crypto_provider, FirstPartyCryptoProvider)
        assert isinstance(aes_provider, FirstPartyAesCryptoProvider)
