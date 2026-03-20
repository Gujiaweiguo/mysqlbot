from typing import Any

from fastapi import Request

from common.core.deps import SessionDep
from common.xpack_compat.providers import get_auth_provider


async def logout(session: SessionDep, request: Request, dto: Any) -> Any:
    return await get_auth_provider().logout(session, request, dto)
