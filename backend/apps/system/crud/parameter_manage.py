import json
from typing import Any

from fastapi import Request
from starlette.datastructures import UploadFile

from common.xpack_compat.file_utils import (
    check_file,
    delete_file,
    split_filename_and_flag,
    upload,
)
from common.xpack_compat.system_config import (
    get_group_args as compat_get_group_args,
    get_sys_arg_model,
    save_group_args as compat_save_group_args,
)
from common.core.deps import SessionDep

APPEARANCE_KEYS = {
    "bg",
    "customColor",
    "foot",
    "footContent",
    "help",
    "login",
    "mobileLogin",
    "mobileLoginBg",
    "name",
    "navigate",
    "navigateBg",
    "pc_welcome",
    "pc_welcome_desc",
    "showAbout",
    "showDoc",
    "showSlogan",
    "slogan",
    "themeColor",
    "web",
}


async def get_parameter_args(session: SessionDep) -> list[Any]:
    group_args = await compat_get_group_args(session=session)
    filtered = [x for x in group_args if not x.pkey.startswith("appearance.")]
    return filtered


async def get_groups(session: SessionDep, flag: str) -> list[Any]:
    group_args = await compat_get_group_args(session=session, flag=flag)
    return list(group_args)


async def get_appearance_args(session: SessionDep) -> list[Any]:
    group_args = await compat_get_group_args(session=session)
    return [x for x in group_args if x.pkey in APPEARANCE_KEYS]


async def save_parameter_args(session: SessionDep, request: Request) -> None:
    allow_file_mapping: dict[str, dict[str, Any]] = {}
    form_data = await request.form()
    files = form_data.getlist("files")
    json_text = form_data.get("data")
    if not isinstance(json_text, str):
        raise ValueError("Form field 'data' must be a JSON string")

    sys_arg_model = get_sys_arg_model()
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
            file_name, flag_name = split_filename_and_flag(origin_file_name)
            file.filename = file_name
            allow_limit_obj = allow_file_mapping.get(flag_name)
            if allow_limit_obj:
                file_types = allow_limit_obj.get("types")
                limit_file_size = allow_limit_obj.get("size")
                if not isinstance(file_types, list) or not all(
                    isinstance(file_type, str) for file_type in file_types
                ):
                    raise ValueError(f"Invalid allowed file types for [{flag_name}]")
                if not isinstance(limit_file_size, int):
                    raise ValueError(f"Invalid file size limit for [{flag_name}]")
                check_file(
                    file=file,
                    file_types=file_types,
                    limit_file_size=limit_file_size,
                )
            else:
                raise Exception(
                    f"The file [{file_name}] is not allowed to be uploaded!"
                )
            file_id = await upload(file)
            file_mapping[f"{flag_name}"] = file_id

    await compat_save_group_args(
        session=session, sys_args=sys_args, file_mapping=file_mapping
    )


async def save_appearance_args(session: SessionDep, request: Request) -> None:
    allow_file_mapping: dict[str, dict[str, Any]] = {
        "web": {"types": [".jpeg", ".jpg", ".png", ".gif", ".svg"], "size": 200 * 1024},
        "login": {
            "types": [".jpeg", ".jpg", ".png", ".gif", ".svg"],
            "size": 200 * 1024,
        },
        "bg": {
            "types": [".jpeg", ".jpg", ".png", ".gif", ".svg"],
            "size": 5 * 1024 * 1024,
        },
        "navigate": {
            "types": [".jpeg", ".jpg", ".png", ".gif", ".svg"],
            "size": 200 * 1024,
        },
        "mobileLogin": {
            "types": [".jpeg", ".jpg", ".png", ".gif", ".svg"],
            "size": 200 * 1024,
        },
        "mobileLoginBg": {
            "types": [".jpeg", ".jpg", ".png", ".gif", ".svg"],
            "size": 5 * 1024 * 1024,
        },
    }
    form_data = await request.form()
    files = form_data.getlist("files")
    json_text = form_data.get("data")
    if not isinstance(json_text, str):
        raise ValueError("Form field 'data' must be a JSON string")

    payload_list = [
        item
        for item in json.loads(json_text)
        if isinstance(item, dict) and "pkey" in item
    ]
    if not payload_list:
        return

    sys_arg_model = get_sys_arg_model()
    sys_args = [
        sys_arg_model(**{**item, "pkey": f"{item['pkey']}"}) for item in payload_list
    ]

    existing_args = {arg.pkey: arg for arg in await get_appearance_args(session)}
    file_mapping: dict[str, str] | None = None
    if files:
        file_mapping = {}
        for file in files:
            if not isinstance(file, UploadFile):
                continue
            origin_file_name = file.filename
            if origin_file_name is None:
                continue
            file_name, flag_name = split_filename_and_flag(origin_file_name)
            file.filename = file_name
            allow_limit_obj = allow_file_mapping.get(flag_name)
            if not allow_limit_obj:
                raise Exception(
                    f"The file [{file_name}] is not allowed to be uploaded!"
                )
            file_types = allow_limit_obj["types"]
            limit_file_size = allow_limit_obj["size"]
            check_file(
                file=file,
                file_types=file_types,
                limit_file_size=limit_file_size,
            )
            old_value = existing_args.get(flag_name)
            if old_value and old_value.ptype == "file" and old_value.pval:
                delete_file(old_value.pval)
            file_id = await upload(file)
            file_mapping[flag_name] = file_id

    for raw_arg in sys_args:
        if raw_arg.ptype == "file" and not (
            file_mapping and raw_arg.pkey in file_mapping
        ):
            current = existing_args.get(raw_arg.pkey)
            if (
                current
                and current.ptype == "file"
                and current.pval
                and not raw_arg.pval
            ):
                delete_file(current.pval)

    await compat_save_group_args(
        session=session, sys_args=sys_args, file_mapping=file_mapping
    )
