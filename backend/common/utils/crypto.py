import importlib
from collections.abc import Awaitable, Callable
from typing import cast

_xpack_core = importlib.import_module("sqlbot_xpack.core")
_xpack_sqlbot_decrypt = cast(
    Callable[[str], Awaitable[str]], _xpack_core.sqlbot_decrypt
)
_xpack_sqlbot_encrypt = cast(
    Callable[[str], Awaitable[str]], _xpack_core.sqlbot_encrypt
)


async def sqlbot_decrypt(text: str) -> str:
    return await _xpack_sqlbot_decrypt(text)


async def sqlbot_encrypt(text: str) -> str:
    return await _xpack_sqlbot_encrypt(text)
