from __future__ import annotations

from fastapi import FastAPI

from common.xpack_compat.providers import get_startup_hooks


def init_fastapi_app(app: FastAPI) -> None:
    get_startup_hooks().init_fastapi_app(app)


async def clean_xpack_cache() -> None:
    await get_startup_hooks().clean_xpack_cache()


async def monitor_app(app: FastAPI) -> None:
    await get_startup_hooks().monitor_app(app)
