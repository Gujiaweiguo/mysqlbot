from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from starlette.datastructures import UploadFile

from common.core.config import settings


def _upload_dir() -> Path:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _file_size(file: UploadFile) -> int:
    current_pos = file.file.tell()
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(current_pos)
    return size


class FirstPartyFileUtilsProvider:
    def get_file_path(self, *, file_id: str) -> str:
        return str((_upload_dir() / Path(file_id).name).resolve())

    def split_filename_and_flag(self, filename: str | None) -> tuple[str, str]:
        if not filename:
            return "", ""
        file_name, separator, flag = filename.rpartition(",")
        if separator:
            return file_name, flag
        return filename, ""

    def check_file(
        self, *, file: UploadFile, file_types: list[str], limit_file_size: int
    ) -> None:
        filename = (file.filename or "").lower()
        if file_types and not any(
            filename.endswith(file_type.lower()) for file_type in file_types
        ):
            raise ValueError("文件类型不支持")
        if limit_file_size > 0 and _file_size(file) > limit_file_size:
            raise ValueError("文件大小超过限制")

    def delete_file(self, file_id: str) -> None:
        file_path = _upload_dir() / Path(file_id).name
        if file_path.exists():
            file_path.unlink()

    async def upload(self, file: UploadFile) -> str:
        suffix = Path(file.filename or "").suffix
        file_id = f"{uuid4().hex}{suffix}"
        file_path = _upload_dir() / file_id
        content = await file.read()
        file_path.write_bytes(content)
        await file.seek(0)
        return file_id
