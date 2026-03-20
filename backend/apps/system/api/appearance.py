import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from apps.system.crud.parameter_manage import get_appearance_args, save_appearance_args
from common.core.deps import SessionDep
from common.xpack_compat.file_utils import get_file_path


class AppearanceArgSchema(BaseModel):
    pkey: str
    pval: str | None = None
    ptype: str
    sort_no: int


router = APIRouter(
    tags=["system/appearance"],
    prefix="/system/appearance",
    include_in_schema=False,
)


@router.get("/ui", response_model=list[AppearanceArgSchema])
async def get_ui_args(session: SessionDep) -> list[AppearanceArgSchema]:
    return await get_appearance_args(session)


@router.get("/picture/{file_id}")
async def picture(
    file_id: Annotated[str, Path(description="file_id")],
) -> StreamingResponse:
    file_path = get_file_path(file_id=file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "image/svg+xml" if file_id.lower().endswith(".svg") else "image/jpeg"

    def iterfile() -> Iterator[bytes]:
        with open(file_path, mode="rb") as f:
            yield from f

    return StreamingResponse(iterfile(), media_type=media_type)


@router.post("")
async def save_ui_args(session: SessionDep, request: Request) -> None:
    await save_appearance_args(session, request)
