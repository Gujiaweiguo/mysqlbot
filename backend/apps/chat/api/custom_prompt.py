import asyncio
import hashlib
import io
import os
import uuid
from datetime import datetime
from typing import Any, cast

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session, col, select

from apps.chat.crud.custom_prompt import get_custom_prompt_type
from apps.chat.models.chat_model import AxisObj
from apps.chat.models.custom_prompt_model import CustomPrompt, CustomPromptTypeEnum
from apps.datasource.models.datasource import CoreDatasource
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.config import settings
from common.core.db import engine
from common.core.deps import CurrentUser, SessionDep, Trans
from common.utils.data_format import DataFormat
from common.utils.excel import get_excel_column_count

router = APIRouter(tags=["CustomPrompt"], prefix="/system/custom_prompt")

path = settings.EXCEL_PATH
session_maker = scoped_session(sessionmaker(bind=engine, class_=Session))


def _resolve_type(prompt_type: str) -> CustomPromptTypeEnum:
    return get_custom_prompt_type(prompt_type)


def _datasource_name_map(session: SessionDep, oid: int) -> dict[int, str]:
    rows = list(
        session.exec(select(CoreDatasource).where(col(CoreDatasource.oid) == oid)).all()
    )
    return {cast(int, row.id): row.name for row in rows if row.id is not None}


def _prompt_to_dict(
    prompt: CustomPrompt, datasource_name_map: dict[int, str]
) -> dict[str, Any]:
    datasource_ids = [
        int(str(item)) for item in (prompt.datasource_ids or []) if str(item).isdigit()
    ]
    datasource_names = [
        datasource_name_map[ds_id]
        for ds_id in datasource_ids
        if ds_id in datasource_name_map
    ]
    return {
        "id": prompt.id,
        "type": prompt.type.value if prompt.type else None,
        "name": prompt.name or "",
        "prompt": prompt.prompt or "",
        "specific_ds": bool(prompt.specific_ds),
        "datasource_ids": datasource_ids,
        "datasource_names": datasource_names,
        "create_time": prompt.create_time.isoformat() if prompt.create_time else None,
    }


def _list_prompts(
    session: SessionDep,
    *,
    oid: int,
    prompt_type: CustomPromptTypeEnum,
    name: str | None,
    dslist: str | None,
) -> list[CustomPrompt]:
    query = select(CustomPrompt).where(
        col(CustomPrompt.oid) == oid,
        col(CustomPrompt.type) == prompt_type,
    )
    if name:
        query = query.where(col(CustomPrompt.name).contains(name))
    prompts = list(
        session.exec(query.order_by(col(CustomPrompt.create_time).desc())).all()
    )
    ds_values = [int(item) for item in (dslist or "").split("_") if item.isdigit()]
    if not ds_values:
        return prompts
    filtered: list[CustomPrompt] = []
    for prompt in prompts:
        if not prompt.specific_ds:
            continue
        datasource_ids = [
            int(str(item))
            for item in (prompt.datasource_ids or [])
            if str(item).isdigit()
        ]
        if any(ds_id in datasource_ids for ds_id in ds_values):
            filtered.append(prompt)
    return filtered


@router.get("/{prompt_type}/page/{current_page}/{page_size}")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def pager(
    session: SessionDep,
    current_user: CurrentUser,
    prompt_type: str,
    current_page: int,
    page_size: int,
    name: str | None = Query(default=None),
    dslist: str | None = Query(default=None),
) -> dict[str, Any]:
    prompt_enum = _resolve_type(prompt_type)
    prompts = _list_prompts(
        session,
        oid=current_user.oid,
        prompt_type=prompt_enum,
        name=name,
        dslist=dslist,
    )
    datasource_name_map = _datasource_name_map(session, current_user.oid)
    start = max(current_page - 1, 0) * page_size
    end = start + page_size
    page_items = [
        _prompt_to_dict(item, datasource_name_map) for item in prompts[start:end]
    ]
    return {
        "current_page": current_page,
        "page_size": page_size,
        "total_count": len(prompts),
        "total_pages": (len(prompts) + page_size - 1) // page_size,
        "data": page_items,
    }


@router.get("/{id}")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def get_one(
    session: SessionDep, current_user: CurrentUser, id: int
) -> dict[str, Any]:
    prompt = session.get(CustomPrompt, id)
    if prompt is None or prompt.oid != current_user.oid:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _prompt_to_dict(prompt, _datasource_name_map(session, current_user.oid))


@router.put("")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def create_or_update(
    session: SessionDep, current_user: CurrentUser, payload: dict[str, Any]
) -> int:
    prompt = session.get(CustomPrompt, payload.get("id")) if payload.get("id") else None
    if prompt is None:
        prompt = CustomPrompt(
            oid=current_user.oid,
            type=_resolve_type(str(payload.get("type"))),
            create_time=datetime.now(),
        )
    elif prompt.oid != current_user.oid:
        raise HTTPException(status_code=403, detail="No permission")
    prompt.name = cast(str | None, payload.get("name"))
    prompt.prompt = cast(str | None, payload.get("prompt"))
    prompt.type = _resolve_type(str(payload.get("type")))
    prompt.specific_ds = bool(payload.get("specific_ds"))
    prompt.datasource_ids = [
        int(item)
        for item in cast(list[Any], payload.get("datasource_ids") or [])
        if str(item).isdigit()
    ]
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return cast(int, prompt.id)


@router.delete("")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def delete(
    session: SessionDep, current_user: CurrentUser, id_list: list[int]
) -> None:
    for item_id in id_list:
        prompt = session.get(CustomPrompt, item_id)
        if prompt and prompt.oid == current_user.oid:
            session.delete(prompt)
    session.commit()


@router.get("/{prompt_type}/export")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def export_excel(
    session: SessionDep,
    current_user: CurrentUser,
    trans: Trans,
    prompt_type: str,
    name: str | None = Query(default=None),
) -> StreamingResponse:
    prompt_enum = _resolve_type(prompt_type)
    prompts = _list_prompts(
        session,
        oid=current_user.oid,
        prompt_type=prompt_enum,
        name=name,
        dslist=None,
    )
    datasource_name_map = _datasource_name_map(session, current_user.oid)

    data_list = []
    for prompt in prompts:
        item = _prompt_to_dict(prompt, datasource_name_map)
        data_list.append(
            {
                "name": item["name"],
                "prompt": item["prompt"],
                "all_data_sources": "N" if item["specific_ds"] else "Y",
                "datasource": ", ".join(item["datasource_names"]),
            }
        )

    fields = [
        AxisObj(name=trans("i18n_prompt.prompt_word_name"), value="name"),
        AxisObj(name=trans("i18n_prompt.prompt_word_content"), value="prompt"),
        AxisObj(name=trans("i18n_training.effective_data_sources"), value="datasource"),
        AxisObj(name=trans("i18n_training.all_data_sources"), value="all_data_sources"),
    ]
    md_data, field_names = DataFormat.convert_object_array_for_pandas(fields, data_list)
    df = pd.DataFrame(md_data, columns=cast(Any, field_names))
    buffer = io.BytesIO()
    with pd.ExcelWriter(
        cast(Any, buffer),
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_numbers": False}},
    ) as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
    buffer.seek(0)
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/template")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def excel_template(trans: Trans) -> StreamingResponse:
    data_list = [
        {
            "name": trans("i18n_prompt.prompt_word_name_template_example_1"),
            "prompt": trans("i18n_prompt.prompt_word_content_template_example_1"),
            "all_data_sources": "Y",
            "datasource": "",
        },
        {
            "name": trans("i18n_prompt.prompt_word_name_template_example_2"),
            "prompt": trans("i18n_prompt.prompt_word_content_template_example_2"),
            "all_data_sources": "N",
            "datasource": trans(
                "i18n_training.effective_data_sources_template_example_1"
            ),
        },
    ]
    fields = [
        AxisObj(name=trans("i18n_prompt.prompt_word_name"), value="name"),
        AxisObj(name=trans("i18n_prompt.prompt_word_content"), value="prompt"),
        AxisObj(name=trans("i18n_training.effective_data_sources"), value="datasource"),
        AxisObj(name=trans("i18n_training.all_data_sources"), value="all_data_sources"),
    ]
    md_data, field_names = DataFormat.convert_object_array_for_pandas(fields, data_list)
    df = pd.DataFrame(md_data, columns=cast(Any, field_names))
    buffer = io.BytesIO()
    with pd.ExcelWriter(
        cast(Any, buffer),
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_numbers": False}},
    ) as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
    buffer.seek(0)
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/{prompt_type}/uploadExcel")
@require_permissions(permission=SqlbotPermission(role=["ws_admin"]))
async def upload_excel(
    prompt_type: str,
    trans: Trans,
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    allowed = {"xlsx", "xls"}
    filename_value = file.filename or ""
    if not filename_value.lower().endswith(tuple(allowed)):
        raise HTTPException(400, "Only support .xlsx/.xls")

    os.makedirs(path, exist_ok=True)
    base_filename = f"{filename_value.split('.')[0]}_{hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:10]}"
    ext_name = filename_value.split(".")[-1] if "." in filename_value else "xlsx"
    filename = f"{base_filename}.{ext_name}"
    save_path = os.path.join(path, filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    prompt_enum = _resolve_type(prompt_type)

    def inner() -> dict[str, Any]:
        session = session_maker()
        datasource_map = {
            row.name: cast(int, row.id)
            for row in session.exec(
                select(CoreDatasource).where(
                    col(CoreDatasource.oid) == current_user.oid
                )
            ).all()
            if row.id is not None
        }
        sheet_names = pd.ExcelFile(save_path).sheet_names
        success_count = 0
        failed_count = 0
        for sheet_name in sheet_names:
            if get_excel_column_count(save_path, str(sheet_name)) < 4:
                raise Exception(trans("i18n_excel_import.col_num_not_match"))
            df = pd.read_excel(
                save_path,
                sheet_name=sheet_name,
                engine="calamine",
                header=0,
                usecols=[0, 1, 2, 3],
                dtype=str,
            ).fillna("")
            for _, row in df.iterrows():
                name = row[0].strip() if pd.notna(row[0]) else ""
                prompt_text = row[1].strip() if pd.notna(row[1]) else ""
                datasource_names = (
                    [d.strip() for d in row[2].split(",") if d.strip()]
                    if pd.notna(row[2]) and row[2].strip()
                    else []
                )
                all_data_sources = bool(
                    pd.notna(row[3]) and row[3].lower().strip() in ["y", "yes", "true"]
                )
                datasource_ids = [
                    datasource_map[item]
                    for item in datasource_names
                    if item in datasource_map
                ]
                if not name or not prompt_text:
                    failed_count += 1
                    continue
                prompt = CustomPrompt(
                    oid=current_user.oid,
                    type=prompt_enum,
                    create_time=datetime.now(),
                    name=name,
                    prompt=prompt_text,
                    specific_ds=not all_data_sources,
                    datasource_ids=cast(
                        list[object], [] if all_data_sources else datasource_ids
                    ),
                )
                session.add(prompt)
                success_count += 1
        session.commit()
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "duplicate_count": 0,
            "original_count": success_count + failed_count,
            "error_excel_filename": None,
        }

    return await asyncio.to_thread(inner)
