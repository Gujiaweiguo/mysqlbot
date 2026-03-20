from __future__ import annotations

from typing import Any

from fastapi import Request

from common.core.deps import SessionDep


class FirstPartyAuthProvider:
    async def logout(self, session: SessionDep, request: Request, dto: Any) -> Any:
        _ = session
        _ = request
        _ = dto
        return None
