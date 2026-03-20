from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter


class LicenseDetailSchema(BaseModel):
    corporation: str = "Community Edition"
    expired: str = ""
    count: int = 0
    version: str = "Community"
    edition: str = "Community"
    serialNo: str = ""
    remark: str = ""
    isv: str = ""


class LicenseStatusSchema(BaseModel):
    status: str = "valid"
    license: LicenseDetailSchema = LicenseDetailSchema()


router = APIRouter(
    tags=["system/license"], prefix="/system/license", include_in_schema=False
)


@router.get("")
async def get_license_status() -> LicenseStatusSchema:
    return LicenseStatusSchema()


@router.get("/version")
async def get_license_version() -> str:
    return "community"
