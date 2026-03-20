from typing import cast

from sqlmodel import col, select

from apps.chat.models.custom_prompt_model import CustomPrompt, CustomPromptTypeEnum
from common.core.deps import SessionDep


def get_custom_prompt_type(enum_name: str) -> CustomPromptTypeEnum:
    return CustomPromptTypeEnum[enum_name]


def get_custom_prompt_model() -> type[CustomPrompt]:
    return CustomPrompt


def find_custom_prompts(
    session: SessionDep,
    custom_prompt_type: object,
    oid: int | None,
    ds_id: int | None,
) -> tuple[str, list[dict[str, object]]]:
    if oid is None or not isinstance(custom_prompt_type, CustomPromptTypeEnum):
        return "", []

    prompts = list(
        session.exec(
            select(CustomPrompt)
            .where(
                col(CustomPrompt.oid) == oid,
                col(CustomPrompt.type) == custom_prompt_type,
            )
            .order_by(col(CustomPrompt.id))
        )
    )

    selected: list[CustomPrompt] = []
    for prompt in prompts:
        if prompt.specific_ds:
            if ds_id is None:
                continue
            datasource_ids = prompt.datasource_ids or []
            if ds_id not in datasource_ids and str(ds_id) not in datasource_ids:
                continue
        selected.append(prompt)

    prompt_text = "\n\n".join(
        prompt.prompt
        for prompt in selected
        if isinstance(prompt.prompt, str) and prompt.prompt
    )
    prompt_list = cast(
        list[dict[str, object]],
        [
            {
                "id": prompt.id or 0,
                "name": prompt.name or "",
                "prompt": prompt.prompt or "",
                "specific_ds": bool(prompt.specific_ds),
                "datasource_ids": prompt.datasource_ids or [],
            }
            for prompt in selected
        ],
    )
    return prompt_text, prompt_list
