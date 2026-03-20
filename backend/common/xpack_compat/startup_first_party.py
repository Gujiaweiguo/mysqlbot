from __future__ import annotations

from fastapi import FastAPI


class FirstPartyStartupHooks:
    def init_fastapi_app(self, app: FastAPI) -> None:
        _ = app

    async def clean_xpack_cache(self) -> None:
        return None

    async def monitor_app(self, app: FastAPI) -> None:
        _ = app
        return None
