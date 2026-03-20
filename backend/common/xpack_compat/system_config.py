from typing import Any

from common.core.deps import SessionDep
from common.xpack_compat.providers import get_system_config_provider


async def get_group_args(*, session: SessionDep, flag: str | None = None) -> Any:
    return await get_system_config_provider().get_group_args(session=session, flag=flag)


async def save_group_args(
    *, session: SessionDep, sys_args: list[Any], file_mapping: dict[str, str] | None
) -> Any:
    return await get_system_config_provider().save_group_args(
        session=session, sys_args=sys_args, file_mapping=file_mapping
    )


def get_sys_arg_model() -> Any:
    return get_system_config_provider().get_sys_arg_model()
