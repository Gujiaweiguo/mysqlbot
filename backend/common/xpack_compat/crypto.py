from __future__ import annotations

from common.xpack_compat.providers import get_aes_crypto_provider, get_crypto_provider


async def sqlbot_decrypt(text: str) -> str:
    return await get_crypto_provider().sqlbot_decrypt(text)


async def sqlbot_encrypt(text: str) -> str:
    return await get_crypto_provider().sqlbot_encrypt(text)


def sqlbot_aes_encrypt(text: str, key: str | None = None) -> str:
    return get_aes_crypto_provider().sqlbot_aes_encrypt(text, key=key)


def sqlbot_aes_decrypt(text: str, key: str | None = None) -> str:
    return get_aes_crypto_provider().sqlbot_aes_decrypt(text, key=key)


def simple_aes_encrypt(
    text: str, key: str | None = None, ivtext: str | None = None
) -> str:
    return get_aes_crypto_provider().simple_aes_encrypt(text, key=key, ivtext=ivtext)


def simple_aes_decrypt(
    text: str, key: str | None = None, ivtext: str | None = None
) -> str:
    return get_aes_crypto_provider().simple_aes_decrypt(text, key=key, ivtext=ivtext)
