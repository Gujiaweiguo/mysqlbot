import asyncio
import atexit
import io
import os
import tempfile
import threading
import uuid
from collections.abc import Callable
from typing import Any, cast

import pandas as pd
from fastapi import HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from apps.system.models.user import UserModel
from common.core.deps import SessionDep

I18nTranslator = Callable[[str], str]


class RowValidator:
    def __init__(
        self,
        success: bool = False,
        row: list[Any] | None = None,
        error_info: dict[int, str] | None = None,
    ) -> None:
        self.success = success
        self.row = row or []
        self.dict_data: dict[str, Any] = {}
        self.error_info = error_info or {}


class CellValidator:
    def __init__(
        self,
        success: bool = False,
        value: str | int | list[Any] | None = None,
        message: str | None = None,
    ) -> None:
        self.success = success
        self.value = value
        self.message = message


class UploadResultDTO(BaseModel):
    successCount: int
    errorCount: int
    dataKey: str | None = None


async def downTemplate(trans: I18nTranslator) -> StreamingResponse:
    def inner() -> io.BytesIO:
        data: dict[str, list[Any]] = {
            trans("i18n_user.account"): ["sqlbot1", "sqlbot2"],
            trans("i18n_user.name"): ["sqlbot_employee1", "sqlbot_employee2"],
            trans("i18n_user.email"): ["employee1@sqlbot.com", "employee2@sqlbot.com"],
            trans("i18n_user.workspace"): [
                trans("i18n_default_workspace"),
                trans("i18n_default_workspace"),
            ],
            trans("i18n_user.role"): [
                trans("i18n_user.administrator"),
                trans("i18n_user.ordinary_member"),
            ],
            trans("i18n_user.status"): [
                trans("i18n_user.status_enabled"),
                trans("i18n_user.status_disabled"),
            ],
            trans("i18n_user.origin"): [
                trans("i18n_user.local_creation"),
                trans("i18n_user.local_creation"),
            ],
            trans("i18n_user.platform_user_id"): [None, None],
        }
        df = pd.DataFrame(data)
        buffer = io.BytesIO()
        with pd.ExcelWriter(
            cast(Any, buffer),
            engine="xlsxwriter",
            engine_kwargs={"options": {"strings_to_numbers": False}},
        ) as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)

            workbook = writer.book
            worksheet = writer.sheets["Sheet1"]

            header_format = workbook.add_format(
                {
                    "bold": True,
                    "font_size": 12,
                    "font_name": "微软雅黑",
                    "align": "center",
                    "valign": "vcenter",
                    "border": 0,
                    "text_wrap": False,
                }
            )

            for i, col in enumerate(df.columns):
                max_length = max(
                    len(str(col).encode("utf-8")) * 1.1,
                    (df[col].astype(str)).apply(len).max(),
                )
                worksheet.set_column(i, i, max_length + 12)
                worksheet.write(0, i, col, header_format)

            worksheet.set_row(0, 30)
            for row in range(1, len(df) + 1):
                worksheet.set_row(row, 25)

        buffer.seek(0)
        return io.BytesIO(buffer.getvalue())

    result = await asyncio.to_thread(inner)
    return StreamingResponse(
        result,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


async def batchUpload(
    session: SessionDep, trans: I18nTranslator, file: Any
) -> UploadResultDTO:
    allowed_extensions = {"xlsx", "xls"}
    filename = getattr(file, "filename", None)
    if not isinstance(filename, str) or not filename.lower().endswith(
        tuple(allowed_extensions)
    ):
        raise HTTPException(status_code=400, detail="Only support .xlsx/.xls")

    na_values = ["", "NA", "N/A", "NULL"]
    df: Any
    read_attr = file.read if hasattr(file, "read") else None
    if read_attr is not None and asyncio.iscoroutinefunction(read_attr):
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, na_values=na_values)
    elif hasattr(file, "file"):
        fobj = file.file
        try:
            fobj.seek(0)
        except Exception:
            pass
        df = pd.read_excel(fobj, sheet_name=0, na_values=na_values)
    else:
        try:
            file.seek(0)
        except Exception:
            pass
        df = pd.read_excel(file, sheet_name=0, na_values=na_values)

    head_list: list[str] = [str(col) for col in list(df.columns)]
    i18n_head_list = get_i18n_head_list()
    if not validate_head(
        trans=trans, head_i18n_list=i18n_head_list, head_list=head_list
    ):
        raise HTTPException(status_code=400, detail="Excel header validation failed")

    success_list: list[dict[str, Any]] = []
    error_list: list[RowValidator] = []
    for row in df.itertuples():
        row_validator = validate_row(
            trans=trans, head_i18n_list=i18n_head_list, row=row
        )
        if row_validator.success:
            success_list.append(row_validator.dict_data)
        else:
            error_list.append(row_validator)

    error_file_id = generate_error_file(error_list, head_list) if error_list else None
    result = UploadResultDTO(
        successCount=len(success_list),
        errorCount=len(error_list),
        dataKey=error_file_id,
    )

    if success_list:
        user_po_list = [UserModel.model_validate(row_data) for row_data in success_list]
        session.add_all(user_po_list)
        session.commit()
    return result


def get_i18n_head_list() -> list[str]:
    return [
        "i18n_user.account",
        "i18n_user.name",
        "i18n_user.email",
        "i18n_user.workspace",
        "i18n_user.role",
        "i18n_user.status",
        "i18n_user.origin",
        "i18n_user.platform_user_id",
    ]


def validate_head(
    trans: I18nTranslator, head_i18n_list: list[str], head_list: list[str]
) -> bool:
    if len(head_list) != len(head_i18n_list):
        return False
    for i, i18n_key in enumerate(head_i18n_list):
        if head_list[i] != trans(i18n_key):
            return False
    return True


def validate_row(
    trans: I18nTranslator, head_i18n_list: list[str], row: Any
) -> RowValidator:
    validator = RowValidator(success=True, row=[], error_info={})
    for i, i18n_key in enumerate(head_i18n_list):
        col_name = trans(i18n_key)
        row_value = getattr(row, col_name)
        validator.row.append(row_value)

        attr_name = i18n_key.split(".")[-1]
        method_name = f"validate_{attr_name}"
        cell_validator = dynamic_call(method_name, row_value)
        if not cell_validator.success:
            validator.success = False
            validator.error_info[i] = cell_validator.message or ""
        else:
            validator.dict_data[attr_name] = cell_validator.value
    return validator


def generate_error_file(error_list: list[RowValidator], head_list: list[str]) -> str:
    if not error_list:
        return ""

    df_rows: list[list[Any]] = [err.row for err in error_list]
    df = pd.DataFrame(df_rows, columns=cast(Any, head_list))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp_name = tmp.name
    tmp.close()

    with pd.ExcelWriter(
        tmp_name,
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_numbers": False}},
    ) as writer:
        df.to_excel(writer, sheet_name="Errors", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Errors"]
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 12,
                "font_name": "微软雅黑",
                "align": "center",
                "valign": "vcenter",
                "border": 0,
                "text_wrap": False,
            }
        )

        for i, col in enumerate(df.columns):
            max_length = max(
                len(str(col).encode("utf-8")) * 1.1,
                (df[col].astype(str)).apply(len).max() if len(df) > 0 else 0,
            )
            worksheet.set_column(i, i, max_length + 12)
            worksheet.write(0, i, col, header_format)

        worksheet.set_row(0, 30)
        for row_idx in range(1, len(df) + 1):
            worksheet.set_row(row_idx, 25)

        red_format = workbook.add_format({"font_color": "red"})
        for sheet_row_idx, err in enumerate(error_list, start=1):
            for col_idx, message in err.error_info.items():
                if message:
                    worksheet.write_comment(sheet_row_idx, col_idx, str(message))
                    try:
                        cell_value = df.iat[sheet_row_idx - 1, col_idx]
                    except Exception:
                        cell_value = None
                    worksheet.write(sheet_row_idx, col_idx, cell_value, red_format)

    file_id = uuid.uuid4().hex
    with _TEMP_FILE_LOCK:
        _TEMP_FILE_MAP[file_id] = tmp_name
    return file_id


def download_error_file(file_id: str) -> FileResponse:
    if not file_id:
        raise HTTPException(status_code=400, detail="file_id required")

    with _TEMP_FILE_LOCK:
        file_path = _TEMP_FILE_MAP.get(file_id)

    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")

    tempdir = tempfile.gettempdir()
    try:
        common = os.path.commonpath([tempdir, os.path.abspath(file_path)])
    except Exception:
        raise HTTPException(status_code=403, detail="Unauthorized file access")

    if os.path.abspath(common) != os.path.abspath(tempdir):
        raise HTTPException(status_code=403, detail="Unauthorized file access")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(file_path),
    )


def validate_account(value: str) -> CellValidator:
    return CellValidator(True, value, "")


def validate_name(value: str) -> CellValidator:
    return CellValidator(True, value, "")


def validate_email(value: str) -> CellValidator:
    return CellValidator(True, value, "")


def validate_workspace(value: str) -> CellValidator:
    return CellValidator(True, value, "")


def validate_role(value: str) -> CellValidator:
    return CellValidator(True, value, "")


def validate_status(value: str) -> CellValidator:
    if value == "已启用":
        return CellValidator(True, 1, "")
    if value == "已禁用":
        return CellValidator(True, 0, "")
    return CellValidator(False, None, "状态只能是已启用或已禁用")


def validate_origin(value: str) -> CellValidator:
    if value == "本地创建":
        return CellValidator(True, 0, "")
    return CellValidator(False, None, "不支持当前来源")


def validate_platform_id(value: str) -> CellValidator:
    return CellValidator(True, value, "")


_method_cache: dict[str, Callable[..., CellValidator]] = {
    "validate_account": validate_account,
    "validate_name": validate_name,
    "validate_email": validate_email,
    "validate_workspace": validate_workspace,
    "validate_role": validate_role,
    "validate_status": validate_status,
    "validate_origin": validate_origin,
    "validate_platform_user_id": validate_platform_id,
}


def dynamic_call(method_name: str, *args: Any, **kwargs: Any) -> CellValidator:
    func = _method_cache.get(method_name)
    if func is None:
        raise AttributeError(f"Function '{method_name}' not found")
    return func(*args, **kwargs)


_TEMP_FILE_MAP: dict[str, str] = {}
_TEMP_FILE_LOCK = threading.Lock()


def _cleanup_temp_files() -> None:
    with _TEMP_FILE_LOCK:
        for _fid, path in list(_TEMP_FILE_MAP.items()):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        _TEMP_FILE_MAP.clear()


atexit.register(_cleanup_temp_files)
