from starlette.datastructures import UploadFile

from common.xpack_compat.providers import get_file_utils_provider


def get_file_path(*, file_id: str) -> str:
    return get_file_utils_provider().get_file_path(file_id=file_id)


def split_filename_and_flag(filename: str | None) -> tuple[str, str]:
    return get_file_utils_provider().split_filename_and_flag(filename)


def check_file(
    *, file: UploadFile, file_types: list[str], limit_file_size: int
) -> None:
    get_file_utils_provider().check_file(
        file=file, file_types=file_types, limit_file_size=limit_file_size
    )


def delete_file(file_id: str) -> None:
    get_file_utils_provider().delete_file(file_id)


async def upload(file: UploadFile) -> str:
    return await get_file_utils_provider().upload(file)
