"""First-party crypto implementation for sqlbot encryption.

This module provides a first-party replacement for the previous external crypto operations,
allowing the project to eventually remove the compiled dependency.

Encryption format:
- encrypt_to_single_string: Base64(IV + AES-256-CBC ciphertext)
- simple_aes_encrypt: Base64(AES-256-CBC ciphertext) with explicit IV

Both use PKCS7 padding for compatibility with standard AES implementations.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
import secrets
from typing import Final

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from common.core.config import settings
from common.utils.utils import SQLBotLogUtil

_DEFAULT_IV_LENGTH: Final[int] = 16
_AES_BLOCK_SIZE: Final[int] = 128


def _derive_key(key: str, length: int = 32) -> bytes:
    return hashlib.sha256(key.encode()).digest()[:length]


def _pad_pkcs7(data: bytes) -> bytes:
    padder = padding.PKCS7(_AES_BLOCK_SIZE).padder()
    return padder.update(data) + padder.finalize()


def _unpad_pkcs7(data: bytes) -> bytes:
    unpadder = padding.PKCS7(_AES_BLOCK_SIZE).unpadder()
    return unpadder.update(data) + unpadder.finalize()


class FirstPartyCryptoProvider:
    """First-party implementation of async sqlbot_encrypt/sqlbot_decrypt.

    Uses AES-256-CBC with random IV per encryption.
    Format: Base64(IV[16] + ciphertext)
    """

    async def sqlbot_encrypt(self, text: str) -> str:
        iv = secrets.token_bytes(_DEFAULT_IV_LENGTH)
        key = _derive_key(settings.SECRET_KEY)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padded = _pad_pkcs7(text.encode())
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        return base64.b64encode(iv + ciphertext).decode()

    async def sqlbot_decrypt(self, text: str) -> str:
        try:
            raw = base64.b64decode(text)
            iv = raw[:_DEFAULT_IV_LENGTH]
            ciphertext = raw[_DEFAULT_IV_LENGTH:]
            key = _derive_key(settings.SECRET_KEY)
            cipher = Cipher(
                algorithms.AES(key), modes.CBC(iv), backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()
            return _unpad_pkcs7(padded).decode()
        except (binascii.Error, ValueError) as exc:
            SQLBotLogUtil.warning("sqlbot_decrypt fallback to plaintext: %s", exc)
            return text


class FirstPartyAesCryptoProvider:
    def sqlbot_aes_encrypt(self, text: str, key: str | None = None) -> str:
        return encrypt_to_single_string(text, key or settings.SECRET_KEY)

    def sqlbot_aes_decrypt(self, text: str, key: str | None = None) -> str:
        return decrypt_from_single_string(text, key or settings.SECRET_KEY)

    def simple_aes_encrypt(
        self, text: str, key: str | None = None, ivtext: str | None = None
    ) -> str:
        return simple_aes_encrypt(
            text,
            key or settings.SECRET_KEY[:32],
            ivtext or "sqlbot_em_aes_iv",
        )

    def simple_aes_decrypt(
        self, text: str, key: str | None = None, ivtext: str | None = None
    ) -> str:
        return simple_aes_decrypt(
            text,
            key or settings.SECRET_KEY[:32],
            ivtext or "sqlbot_em_aes_iv",
        )


def encrypt_to_single_string(text: str, key: str) -> str:
    """Encrypt text to a single base64-encoded string.

    Format: Base64(IV[16] + AES-256-CBC ciphertext with PKCS7 padding)
    """
    iv = secrets.token_bytes(_DEFAULT_IV_LENGTH)
    derived_key = _derive_key(key)
    cipher = Cipher(
        algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend()
    )
    encryptor = cipher.encryptor()
    padded = _pad_pkcs7(text.encode())
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode()


def decrypt_from_single_string(text: str, key: str) -> str:
    """Decrypt text from a single base64-encoded string.

    Expected format: Base64(IV[16] + AES-256-CBC ciphertext with PKCS7 padding)
    """
    raw = base64.b64decode(text)
    iv = raw[:_DEFAULT_IV_LENGTH]
    ciphertext = raw[_DEFAULT_IV_LENGTH:]
    derived_key = _derive_key(key)
    cipher = Cipher(
        algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend()
    )
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return _unpad_pkcs7(padded).decode()


def simple_aes_encrypt(text: str, key: str, ivtext: str) -> str:
    """Simple AES encryption with explicit key and IV.

    Uses AES-256-CBC with PKCS7 padding.
    Key must be 32 bytes (will be truncated/padded if needed).
    IV must be 16 bytes (will be truncated/padded if needed).
    """
    key_bytes = key[:32].ljust(32, "\x00").encode()
    iv_bytes = ivtext[:16].ljust(16, "\x00").encode()
    cipher = Cipher(
        algorithms.AES(key_bytes), modes.CBC(iv_bytes), backend=default_backend()
    )
    encryptor = cipher.encryptor()
    padded = _pad_pkcs7(text.encode())
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode()


def simple_aes_decrypt(text: str, key: str, ivtext: str) -> str:
    """Simple AES decryption with explicit key and IV.

    Uses AES-256-CBC with PKCS7 padding.
    Key must be 32 bytes (will be truncated/padded if needed).
    IV must be 16 bytes (will be truncated/padded if needed).
    """
    key_bytes = key[:32].ljust(32, "\x00").encode()
    iv_bytes = ivtext[:16].ljust(16, "\x00").encode()
    ciphertext = base64.b64decode(text)
    cipher = Cipher(
        algorithms.AES(key_bytes), modes.CBC(iv_bytes), backend=default_backend()
    )
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return _unpad_pkcs7(padded).decode()
