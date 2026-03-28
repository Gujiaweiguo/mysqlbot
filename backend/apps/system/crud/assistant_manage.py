import secrets
from typing import Protocol

from fastapi import FastAPI, Request
from sqlmodel import Session, col, select
from starlette.middleware.cors import CORSMiddleware

from apps.system.models.system_model import AssistantModel
from apps.system.schemas.system_schema import AssistantBase
from common.core.config import settings
from common.utils.time import get_timestamp

from common.utils.utils import get_domain_list

DEFAULT_EMBEDDED_ASSISTANT_NAME = "Default Embedded Assistant"


class _ExecResult(Protocol):
    def first(self) -> AssistantModel | None: ...


class _EmbeddedAssistantSession(Protocol):
    def exec(self, statement: object) -> _ExecResult: ...

    def add(self, instance: object, _warn: bool = True, /) -> None: ...

    def commit(self) -> None: ...


def ensure_default_embedded_assistant(*, session: _EmbeddedAssistantSession) -> bool:
    existing = session.exec(
        select(AssistantModel).where(
            col(AssistantModel.type) == 4,
            col(AssistantModel.oid) == 1,
        )
    ).first()
    if existing is not None:
        return False

    model = AssistantModel(
        name=DEFAULT_EMBEDDED_ASSISTANT_NAME,
        domain=settings.FRONTEND_HOST,
        type=4,
        configuration="{}",
        description="Auto-created embedded assistant",
        app_id=secrets.token_hex(8),
        app_secret=secrets.token_hex(16),
        oid=1,
    )
    model.create_time = get_timestamp()
    session.add(model)
    session.commit()
    return True


def dynamic_upgrade_cors(request: Request, session: Session) -> None:
    list_result = session.exec(
        select(AssistantModel).order_by(col(AssistantModel.create_time))
    ).all()

    seen: set[str] = set()
    unique_domains: list[str] = []
    for item in list_result:
        if item.domain:
            for domain in get_domain_list(item.domain):
                domain = domain.strip()
                if domain and domain not in seen:
                    seen.add(domain)
                    unique_domains.append(domain)
    app: FastAPI = request.app
    cors_middleware = None
    for middleware in app.user_middleware:
        if getattr(middleware, "cls", None) is CORSMiddleware:
            cors_middleware = middleware
            break
    if cors_middleware:
        updated_origins = list(set(settings.all_cors_origins + unique_domains))
        cors_middleware.kwargs["allow_origins"] = updated_origins


async def save(
    request: Request,
    session: Session,
    creator: AssistantBase,
    oid: int | None = 1,
) -> AssistantModel:
    db_model = AssistantModel.model_validate(creator)
    db_model.create_time = get_timestamp()
    db_model.oid = oid
    session.add(db_model)
    session.commit()
    dynamic_upgrade_cors(request=request, session=session)
    return db_model
