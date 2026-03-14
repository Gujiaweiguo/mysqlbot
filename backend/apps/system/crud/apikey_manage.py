from sqlmodel import Session, select

from apps.system.models.system_model import ApiKeyModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from common.core.sqlbot_cache import cache, clear_cache
from common.utils.utils import SQLBotLogUtil


@cache(
    namespace=CacheNamespace.AUTH_INFO.value,
    cacheName=CacheName.ASK_INFO.value,
    keyExpression="access_key",
)
async def get_api_key(session: Session, access_key: str) -> ApiKeyModel | None:
    query = select(ApiKeyModel).where(ApiKeyModel.access_key == access_key)
    return session.exec(query).first()


@clear_cache(
    namespace=CacheNamespace.AUTH_INFO.value,
    cacheName=CacheName.ASK_INFO.value,
    keyExpression="access_key",
)
async def clear_api_key_cache(access_key: str) -> None:
    SQLBotLogUtil.info(f"Api key cache for [{access_key}] has been cleaned")
