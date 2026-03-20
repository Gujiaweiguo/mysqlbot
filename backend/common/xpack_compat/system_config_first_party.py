from __future__ import annotations

from typing import Any, cast

from sqlmodel import col, select

from apps.system.models.sys_arg_model import SysArgModel
from common.core.deps import SessionDep


def _normalize_pval(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


class FirstPartySystemConfigProvider:
    async def get_group_args(
        self, *, session: SessionDep, flag: str | None = None
    ) -> list[SysArgModel]:
        stmt = select(SysArgModel).order_by(
            col(SysArgModel.sort_no), col(SysArgModel.id)
        )
        if flag is not None:
            stmt = stmt.where(col(SysArgModel.pkey).like(f"{flag}.%"))
        return list(session.exec(stmt))

    async def save_group_args(
        self,
        *,
        session: SessionDep,
        sys_args: list[Any],
        file_mapping: dict[str, str] | None,
    ) -> None:
        mapping = file_mapping or {}
        for raw_arg in sys_args:
            arg = cast(SysArgModel, raw_arg)
            current = session.exec(
                select(SysArgModel).where(col(SysArgModel.pkey) == arg.pkey)
            ).first()
            pval = mapping.get(arg.pkey, _normalize_pval(arg.pval))
            ptype = "file" if arg.pkey in mapping else (arg.ptype or "str")
            sort_no = arg.sort_no or 1
            if current is None:
                session.add(
                    cast(
                        SysArgModel,
                        SysArgModel.model_validate(
                            {
                                "pkey": arg.pkey,
                                "pval": pval,
                                "ptype": ptype,
                                "sort_no": sort_no,
                            }
                        ),
                    )
                )
                continue
            current.pval = pval
            current.ptype = ptype
            current.sort_no = sort_no
            session.add(current)
        session.commit()

    def get_sys_arg_model(self) -> type[SysArgModel]:
        return SysArgModel
