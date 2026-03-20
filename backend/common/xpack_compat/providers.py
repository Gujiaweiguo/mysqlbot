from __future__ import annotations

from functools import lru_cache
from common.xpack_compat.contracts import (
    XpackAuthProvider,
    XpackAesCryptoProvider,
    XpackCryptoProvider,
    XpackFileUtilsProvider,
    XpackLicenseProvider,
    XpackSystemConfigProvider,
    XpackStartupHooks,
)


@lru_cache(maxsize=1)
def _get_first_party_crypto_provider() -> XpackCryptoProvider:
    from common.xpack_compat.crypto_first_party import FirstPartyCryptoProvider

    return FirstPartyCryptoProvider()


@lru_cache(maxsize=1)
def _get_first_party_aes_crypto_provider() -> XpackAesCryptoProvider:
    from common.xpack_compat.crypto_first_party import FirstPartyAesCryptoProvider

    return FirstPartyAesCryptoProvider()


@lru_cache(maxsize=1)
def _get_first_party_startup_hooks() -> XpackStartupHooks:
    from common.xpack_compat.startup_first_party import FirstPartyStartupHooks

    return FirstPartyStartupHooks()


@lru_cache(maxsize=1)
def _get_first_party_auth_provider() -> XpackAuthProvider:
    from common.xpack_compat.auth_first_party import FirstPartyAuthProvider

    return FirstPartyAuthProvider()


@lru_cache(maxsize=1)
def _get_first_party_license_provider() -> XpackLicenseProvider:
    from common.xpack_compat.license_first_party import FirstPartyLicenseProvider

    return FirstPartyLicenseProvider()


@lru_cache(maxsize=1)
def _get_first_party_system_config_provider() -> XpackSystemConfigProvider:
    from common.xpack_compat.system_config_first_party import (
        FirstPartySystemConfigProvider,
    )

    return FirstPartySystemConfigProvider()


@lru_cache(maxsize=1)
def _get_first_party_file_utils_provider() -> XpackFileUtilsProvider:
    from common.xpack_compat.file_utils_first_party import FirstPartyFileUtilsProvider

    return FirstPartyFileUtilsProvider()


def get_startup_hooks() -> XpackStartupHooks:
    return _get_first_party_startup_hooks()


def get_crypto_provider() -> XpackCryptoProvider:
    return _get_first_party_crypto_provider()


def get_aes_crypto_provider() -> XpackAesCryptoProvider:
    return _get_first_party_aes_crypto_provider()


def get_auth_provider() -> XpackAuthProvider:
    return _get_first_party_auth_provider()


def get_license_provider() -> XpackLicenseProvider:
    return _get_first_party_license_provider()


def get_system_config_provider() -> XpackSystemConfigProvider:
    return _get_first_party_system_config_provider()


def get_file_utils_provider() -> XpackFileUtilsProvider:
    return _get_first_party_file_utils_provider()
