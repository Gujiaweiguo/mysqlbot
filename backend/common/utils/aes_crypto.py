from common.xpack_compat.crypto import simple_aes_decrypt as compat_simple_aes_decrypt
from common.xpack_compat.crypto import simple_aes_encrypt as compat_simple_aes_encrypt
from common.xpack_compat.crypto import sqlbot_aes_decrypt as compat_sqlbot_aes_decrypt
from common.xpack_compat.crypto import sqlbot_aes_encrypt as compat_sqlbot_aes_encrypt

simple_aes_iv_text = "sqlbot_em_aes_iv"


def sqlbot_aes_encrypt(text: str, key: str | None = None) -> str:
    return compat_sqlbot_aes_encrypt(text, key=key)


def sqlbot_aes_decrypt(text: str, key: str | None = None) -> str:
    return compat_sqlbot_aes_decrypt(text, key=key)


def simple_aes_encrypt(
    text: str, key: str | None = None, ivtext: str | None = None
) -> str:
    return compat_simple_aes_encrypt(text, key=key, ivtext=ivtext)


def simple_aes_decrypt(
    text: str, key: str | None = None, ivtext: str | None = None
) -> str:
    return compat_simple_aes_decrypt(text, key=key, ivtext=ivtext)
