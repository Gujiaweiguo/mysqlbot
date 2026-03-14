import json
from importlib import import_module
from typing import Any

from fastapi import Request
from starlette.datastructures import UploadFile

from common.core.deps import SessionDep


def _get_group_args(*, session: SessionDep, flag: str | None = None) -> Any:
    module = import_module("sqlbot_xpack.config.arg_manage")
    get_group_args = module.get_group_args
    if flag is None:
        return get_group_args(session=session)
    return get_group_args(session=session, flag=flag)


def _save_group_args(
    *, session: SessionDep, sys_args: list[Any], file_mapping: dict[str, str] | None
) -> Any:
    module = import_module("sqlbot_xpack.config.arg_manage")
    save_group_args = module.save_group_args
    return save_group_args(
        session=session, sys_args=sys_args, file_mapping=file_mapping
    )


def _get_sys_arg_model() -> Any:
    module = import_module("sqlbot_xpack.config.model")
    return module.SysArgModel


def _get_sqlbot_file_utils() -> Any:
    module = import_module("sqlbot_xpack.file_utils")
    return module.SQLBotFileUtils


async def get_parameter_args(session: SessionDep) -> list[Any]:
    group_args = await _get_group_args(session=session)
    filtered = [x for x in group_args if not x.pkey.startswith("appearance.")]
    return filtered


async def get_groups(session: SessionDep, flag: str) -> list[Any]:
    group_args = await _get_group_args(session=session, flag=flag)
    return list(group_args)


async def save_parameter_args(session: SessionDep, request: Request) -> None:
    allow_file_mapping: dict[str, dict[str, Any]] = {}
    form_data = await request.form()
    files = form_data.getlist("files")
    json_text = form_data.get("data")
    if not isinstance(json_text, str):
        raise ValueError("Form field 'data' must be a JSON string")

    sys_arg_model = _get_sys_arg_model()
    file_utils = _get_sqlbot_file_utils()
    sys_args = [
        sys_arg_model(**{**item, "pkey": f"{item['pkey']}"})
        for item in json.loads(json_text)
        if "pkey" in item
    ]
    if not sys_args:
        return

    file_mapping: dict[str, str] | None = None
    if files:
        file_mapping = {}
        for file in files:
            if not isinstance(file, UploadFile):
                continue
            origin_file_name = file.filename
            if origin_file_name is None:
                continue
            file_name, flag_name = file_utils.split_filename_and_flag(origin_file_name)
            file.filename = file_name
            allow_limit_obj = allow_file_mapping.get(flag_name)
            if allow_limit_obj:
                file_utils.check_file(
                    file=file,
                    file_types=allow_limit_obj.get("types"),
                    limit_file_size=allow_limit_obj.get("size"),
                )
            else:
                raise Exception(
                    f"The file [{file_name}] is not allowed to be uploaded!"
                )
            file_id = await file_utils.upload(file)
            file_mapping[f"{flag_name}"] = file_id

    await _save_group_args(
        session=session, sys_args=sys_args, file_mapping=file_mapping
    )
