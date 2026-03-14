import base64

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

key = b"SQLBot1234567890"


def aes_encrypt(data: str) -> bytes:
    raw_data = bytes(data, "utf-8")
    cipher = AES.new(key, AES.MODE_ECB)
    padded_data = pad(raw_data, AES.block_size)
    encrypt = cipher.encrypt(padded_data)
    return base64.b64encode(encrypt)


def aes_decrypt(encrypted_data: bytes) -> str:
    encrypted_data = base64.b64decode(encrypted_data)
    cipher = AES.new(key, AES.MODE_ECB)
    text = cipher.decrypt(encrypted_data)
    decrypted_text = unpad(text, AES.block_size)
    return decrypted_text.decode("utf-8")
