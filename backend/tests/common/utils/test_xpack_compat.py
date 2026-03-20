from __future__ import annotations

from fastapi import FastAPI
import pytest

from common.xpack_compat import auth as compat_auth
from common.xpack_compat import crypto as compat_crypto
from common.xpack_compat import file_utils as compat_file_utils
from common.xpack_compat import license as compat_license
from common.xpack_compat import startup as compat_startup
from common.xpack_compat import system_config as compat_system_config
from common.xpack_compat.auth_first_party import FirstPartyAuthProvider
from common.xpack_compat.crypto_first_party import (
    FirstPartyAesCryptoProvider,
    FirstPartyCryptoProvider,
)
from common.xpack_compat.file_utils_first_party import FirstPartyFileUtilsProvider
from common.xpack_compat.license_first_party import FirstPartyLicenseProvider
from common.xpack_compat.providers import (
    get_aes_crypto_provider,
    get_auth_provider,
    get_crypto_provider,
    get_file_utils_provider,
    get_license_provider,
    get_system_config_provider,
    get_startup_hooks,
)
from common.xpack_compat.startup_first_party import FirstPartyStartupHooks
from common.xpack_compat.system_config_first_party import FirstPartySystemConfigProvider


class TestXpackCompatProviders:
    def test_provider_entrypoints_return_first_party_implementations(self) -> None:
        assert isinstance(get_startup_hooks(), FirstPartyStartupHooks)
        assert isinstance(get_crypto_provider(), FirstPartyCryptoProvider)
        assert isinstance(get_aes_crypto_provider(), FirstPartyAesCryptoProvider)
        assert isinstance(get_auth_provider(), FirstPartyAuthProvider)
        assert isinstance(get_file_utils_provider(), FirstPartyFileUtilsProvider)
        assert isinstance(get_license_provider(), FirstPartyLicenseProvider)
        assert isinstance(get_system_config_provider(), FirstPartySystemConfigProvider)


class TestXpackCompatEntrypoints:
    def test_startup_entrypoints_delegate_to_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        app = FastAPI()
        calls: list[tuple[str, object | None]] = []

        class FakeStartupHooks:
            def init_fastapi_app(self, incoming_app: FastAPI) -> None:
                calls.append(("init_fastapi_app", incoming_app))

            async def clean_xpack_cache(self) -> None:
                calls.append(("clean_xpack_cache", None))

            async def monitor_app(self, incoming_app: FastAPI) -> None:
                calls.append(("monitor_app", incoming_app))

        monkeypatch.setattr(
            compat_startup, "get_startup_hooks", lambda: FakeStartupHooks()
        )

        compat_startup.init_fastapi_app(app)

        assert calls == [("init_fastapi_app", app)]

    async def test_crypto_entrypoints_delegate_to_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[str, tuple[object, ...]]] = []

        class FakeCryptoProvider:
            async def sqlbot_decrypt(self, text: str) -> str:
                calls.append(("sqlbot_decrypt", (text,)))
                return f"dec::{text}"

            async def sqlbot_encrypt(self, text: str) -> str:
                calls.append(("sqlbot_encrypt", (text,)))
                return f"enc::{text}"

        class FakeAesCryptoProvider:
            def sqlbot_aes_encrypt(self, text: str, key: str | None = None) -> str:
                calls.append(("sqlbot_aes_encrypt", (text, key)))
                return "aes-enc"

            def sqlbot_aes_decrypt(self, text: str, key: str | None = None) -> str:
                calls.append(("sqlbot_aes_decrypt", (text, key)))
                return "aes-dec"

            def simple_aes_encrypt(
                self, text: str, key: str | None = None, ivtext: str | None = None
            ) -> str:
                calls.append(("simple_aes_encrypt", (text, key, ivtext)))
                return "simple-aes-enc"

            def simple_aes_decrypt(
                self, text: str, key: str | None = None, ivtext: str | None = None
            ) -> str:
                calls.append(("simple_aes_decrypt", (text, key, ivtext)))
                return "simple-aes-dec"

        monkeypatch.setattr(
            compat_crypto, "get_crypto_provider", lambda: FakeCryptoProvider()
        )
        monkeypatch.setattr(
            compat_crypto, "get_aes_crypto_provider", lambda: FakeAesCryptoProvider()
        )

        assert await compat_crypto.sqlbot_decrypt("cipher") == "dec::cipher"
        assert await compat_crypto.sqlbot_encrypt("secret") == "enc::secret"
        assert compat_crypto.sqlbot_aes_encrypt("secret", key="key") == "aes-enc"
        assert compat_crypto.sqlbot_aes_decrypt("cipher", key="key") == "aes-dec"
        assert (
            compat_crypto.simple_aes_encrypt("plain", key="key", ivtext="iv")
            == "simple-aes-enc"
        )
        assert (
            compat_crypto.simple_aes_decrypt("blob", key="key", ivtext="iv")
            == "simple-aes-dec"
        )
        assert calls == [
            ("sqlbot_decrypt", ("cipher",)),
            ("sqlbot_encrypt", ("secret",)),
            ("sqlbot_aes_encrypt", ("secret", "key")),
            ("sqlbot_aes_decrypt", ("cipher", "key")),
            ("simple_aes_encrypt", ("plain", "key", "iv")),
            ("simple_aes_decrypt", ("blob", "key", "iv")),
        ]


class TestXpackCompatAuth:
    async def test_auth_logout_delegates_to_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from typing import Any, cast

        from fastapi import Request

        calls: list[tuple[str, tuple[object, ...]]] = []

        class FakeAuthProvider:
            async def logout(self, session: Any, request: Request, dto: Any) -> Any:
                calls.append(("logout", (session, request, dto)))
                return {"logged_out": True}

        monkeypatch.setattr(
            compat_auth, "get_auth_provider", lambda: FakeAuthProvider()
        )

        result = await compat_auth.logout(
            cast(Any, "session"), cast(Any, "request"), cast(Any, "dto")
        )

        assert result == {"logged_out": True}
        assert calls == [("logout", ("session", "request", "dto"))]


class TestXpackCompatLicense:
    def test_license_valid_delegates_to_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []

        class FakeLicenseProvider:
            def is_valid(self) -> bool:
                calls.append("is_valid")
                return True

        monkeypatch.setattr(
            compat_license, "get_license_provider", lambda: FakeLicenseProvider()
        )

        assert compat_license.is_license_valid() is True
        assert calls == ["is_valid"]


class TestXpackCompatSystemConfig:
    async def test_system_config_delegates_to_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from typing import Any, cast

        calls: list[tuple[str, tuple[object, ...]]] = []

        class FakeSystemConfigProvider:
            async def get_group_args(
                self, *, session: object, flag: str | None = None
            ) -> object:
                calls.append(("get_group_args", (session, flag)))
                return ["arg"]

            async def save_group_args(
                self,
                *,
                session: object,
                sys_args: list[object],
                file_mapping: dict[str, str] | None,
            ) -> object:
                calls.append(("save_group_args", (session, sys_args, file_mapping)))
                return None

            def get_sys_arg_model(self) -> object:
                calls.append(("get_sys_arg_model", ()))
                return "SysArgModel"

        monkeypatch.setattr(
            compat_system_config,
            "get_system_config_provider",
            lambda: FakeSystemConfigProvider(),
        )

        assert await compat_system_config.get_group_args(
            session=cast(Any, "session")
        ) == ["arg"]
        assert compat_system_config.get_sys_arg_model() == "SysArgModel"
        assert (
            await compat_system_config.save_group_args(
                session=cast(Any, "session"),
                sys_args=["x"],
                file_mapping={"logo": "1"},
            )
            is None
        )
        assert calls == [
            ("get_group_args", ("session", None)),
            ("get_sys_arg_model", ()),
            ("save_group_args", ("session", ["x"], {"logo": "1"})),
        ]


class TestXpackCompatFileUtils:
    async def test_file_utils_delegates_to_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from typing import Any, cast

        from starlette.datastructures import UploadFile

        calls: list[tuple[str, tuple[object, ...]]] = []

        class FakeFileUtilsProvider:
            def get_file_path(self, *, file_id: str) -> str:
                calls.append(("get_file_path", (file_id,)))
                return f"/tmp/{file_id}"

            def split_filename_and_flag(self, filename: str | None) -> tuple[str, str]:
                calls.append(("split_filename_and_flag", (filename,)))
                return ("logo.png", "logo")

            def check_file(
                self,
                *,
                file: object,
                file_types: list[str],
                limit_file_size: int,
            ) -> None:
                calls.append(("check_file", (file, file_types, limit_file_size)))

            def delete_file(self, file_id: str) -> None:
                calls.append(("delete_file", (file_id,)))

            async def upload(self, file: object) -> str:
                calls.append(("upload", (file,)))
                return "uploaded-id"

        monkeypatch.setattr(
            compat_file_utils,
            "get_file_utils_provider",
            lambda: FakeFileUtilsProvider(),
        )

        file_obj = cast(UploadFile, cast(Any, object()))
        assert compat_file_utils.get_file_path(file_id="abc") == "/tmp/abc"
        assert compat_file_utils.split_filename_and_flag("logo__logo.png") == (
            "logo.png",
            "logo",
        )
        compat_file_utils.check_file(
            file=cast(Any, file_obj), file_types=[".png"], limit_file_size=1024
        )
        compat_file_utils.delete_file("abc")
        assert await compat_file_utils.upload(cast(Any, file_obj)) == "uploaded-id"
        assert calls == [
            ("get_file_path", ("abc",)),
            ("split_filename_and_flag", ("logo__logo.png",)),
            ("check_file", (file_obj, [".png"], 1024)),
            ("delete_file", ("abc",)),
            ("upload", (file_obj,)),
        ]
