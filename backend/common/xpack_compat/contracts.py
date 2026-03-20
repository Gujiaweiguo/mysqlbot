from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, Protocol

from fastapi import FastAPI, Request
from starlette.datastructures import UploadFile

from common.core.deps import SessionDep


class XpackStartupHooks(Protocol):
    def init_fastapi_app(self, app: FastAPI) -> None: ...

    def clean_xpack_cache(self) -> Awaitable[None]: ...

    def monitor_app(self, app: FastAPI) -> Awaitable[None]: ...


class XpackCryptoProvider(Protocol):
    def sqlbot_decrypt(self, text: str) -> Awaitable[str]: ...

    def sqlbot_encrypt(self, text: str) -> Awaitable[str]: ...


class XpackAesCryptoProvider(Protocol):
    def sqlbot_aes_encrypt(self, text: str, key: str | None = None) -> str: ...

    def sqlbot_aes_decrypt(self, text: str, key: str | None = None) -> str: ...

    def simple_aes_encrypt(
        self, text: str, key: str | None = None, ivtext: str | None = None
    ) -> str: ...

    def simple_aes_decrypt(
        self, text: str, key: str | None = None, ivtext: str | None = None
    ) -> str: ...


class XpackAuthProvider(Protocol):
    def logout(
        self, session: SessionDep, request: Request, dto: Any
    ) -> Awaitable[Any]: ...


class XpackLicenseProvider(Protocol):
    def is_valid(self) -> bool: ...


class XpackSystemConfigProvider(Protocol):
    def get_group_args(
        self, *, session: SessionDep, flag: str | None = None
    ) -> Any: ...

    def save_group_args(
        self,
        *,
        session: SessionDep,
        sys_args: list[Any],
        file_mapping: dict[str, str] | None,
    ) -> Any: ...

    def get_sys_arg_model(self) -> Any: ...


class XpackFileUtilsProvider(Protocol):
    def get_file_path(self, *, file_id: str) -> str: ...

    def split_filename_and_flag(self, filename: str | None) -> tuple[str, str]: ...

    def check_file(
        self, *, file: UploadFile, file_types: list[str], limit_file_size: int
    ) -> None: ...

    def delete_file(self, file_id: str) -> None: ...

    def upload(self, file: UploadFile) -> Awaitable[str]: ...
