from common.xpack_compat.providers import get_license_provider


def is_license_valid() -> bool:
    return get_license_provider().is_valid()
