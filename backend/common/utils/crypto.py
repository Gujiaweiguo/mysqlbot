from common.xpack_compat.crypto import sqlbot_decrypt as compat_sqlbot_decrypt
from common.xpack_compat.crypto import sqlbot_encrypt as compat_sqlbot_encrypt


async def sqlbot_decrypt(text: str) -> str:
    return await compat_sqlbot_decrypt(text)


async def sqlbot_encrypt(text: str) -> str:
    return await compat_sqlbot_encrypt(text)
