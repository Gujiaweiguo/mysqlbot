import importlib
from typing import Any, cast

from common.core.config import settings

_aes_utils = importlib.import_module("sqlbot_xpack.aes_utils")
_secure_encryption = cast(Any, _aes_utils.SecureEncryption)

simple_aes_iv_text = "sqlbot_em_aes_iv"


def sqlbot_aes_encrypt(text: str, key: str | None = None) -> str:
    encrypted = _secure_encryption.encrypt_to_single_string(
        text, key or settings.SECRET_KEY
    )
    return cast(str, encrypted)


def sqlbot_aes_decrypt(text: str, key: str | None = None) -> str:
    decrypted = _secure_encryption.decrypt_from_single_string(
        text, key or settings.SECRET_KEY
    )
    return cast(str, decrypted)


def simple_aes_encrypt(
    text: str, key: str | None = None, ivtext: str | None = None
) -> str:
    encrypted = _secure_encryption.simple_aes_encrypt(
        text, key or settings.SECRET_KEY[:32], ivtext or simple_aes_iv_text
    )
    return cast(str, encrypted)


def simple_aes_decrypt(
    text: str, key: str | None = None, ivtext: str | None = None
) -> str:
    decrypted = _secure_encryption.simple_aes_decrypt(
        text, key or settings.SECRET_KEY[:32], ivtext or simple_aes_iv_text
    )
    return cast(str, decrypted)
