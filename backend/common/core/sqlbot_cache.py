import re
from collections.abc import Callable
from functools import partial, wraps
from inspect import signature
from typing import Any

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache as original_cache

from common.core.config import settings
from common.utils.utils import SQLBotLogUtil


def custom_key_builder(
    func: Any,
    namespace: str = "",
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any],
    cacheName: str,
    keyExpression: str | None = None,
) -> str | list[str]:
    try:
        base_key = f"{namespace}:{cacheName}:"

        if keyExpression:
            sig = signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()

            # 支持args[0]格式
            if keyExpression.startswith("args["):
                if match := re.match(r"args\[(\d+)\]", keyExpression):
                    index = int(match.group(1))
                    value = bound_args.args[index]
                    if isinstance(value, list):
                        return [f"{base_key}{v}" for v in value]
                    return f"{base_key}{value}"

            # 支持属性路径格式
            parts = keyExpression.split(".")
            if not bound_args.arguments.get(parts[0]):
                return f"{base_key}{parts[0]}"
            value = bound_args.arguments[parts[0]]
            for part in parts[1:]:
                value = getattr(value, part)
            if isinstance(value, list):
                return [f"{base_key}{v}" for v in value]
            return f"{base_key}{value}"

        # 默认使用第一个参数作为key
        return f"{base_key}{args[0] if args else 'default'}"

    except Exception as e:
        SQLBotLogUtil.error(f"Key builder error: {str(e)}")
        raise ValueError(f"Invalid cache key generation: {e}") from e


def cache(
    expire: int = 60 * 60 * 24,
    namespace: str = "",
    *,
    cacheName: str,  # 必须提供cacheName
    keyExpression: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # 预先生成key builder
        used_key_builder = partial(
            custom_key_builder, cacheName=cacheName, keyExpression=keyExpression
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if (
                not settings.CACHE_TYPE
                or settings.CACHE_TYPE.lower() == "none"
                or not is_cache_initialized()
            ):
                return await func(*args, **kwargs)
            # 生成缓存键
            cache_key = used_key_builder(
                func=func,
                namespace=str(namespace) if namespace else "",
                args=args,
                kwargs=kwargs,
            )

            def cache_key_builder(*_: Any, **__: Any) -> str:
                if isinstance(cache_key, list):
                    return ",".join(str(item) for item in cache_key)
                return str(cache_key)

            return await original_cache(
                expire=expire,
                namespace=str(namespace) if namespace else "",
                key_builder=cache_key_builder,
            )(func)(*args, **kwargs)

        return wrapper

    return decorator


def clear_cache(
    namespace: str = "",
    *,
    cacheName: str,
    keyExpression: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if (
                not settings.CACHE_TYPE
                or settings.CACHE_TYPE.lower() == "none"
                or not is_cache_initialized()
            ):
                return await func(*args, **kwargs)
            cache_key = custom_key_builder(
                func=func,
                namespace=str(namespace) if namespace else "",
                args=args,
                kwargs=kwargs,
                cacheName=cacheName,
                keyExpression=keyExpression,
            )
            key_list = cache_key if isinstance(cache_key, list) else [cache_key]
            backend = FastAPICache.get_backend()
            for temp_cache_key in key_list:
                if await backend.get(temp_cache_key):
                    if settings.CACHE_TYPE.lower() == "redis":
                        redis_client = getattr(backend, "redis", None)
                        if redis_client is not None:
                            await redis_client.delete(temp_cache_key)
                        else:
                            await backend.clear(key=temp_cache_key)
                    else:
                        await backend.clear(key=temp_cache_key)
                    SQLBotLogUtil.debug(f"Cache cleared: {temp_cache_key}")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def init_sqlbot_cache() -> None:
    cache_type: str = settings.CACHE_TYPE
    if cache_type == "memory":
        FastAPICache.init(InMemoryBackend())
        SQLBotLogUtil.info("mySQLBot 使用内存缓存, 仅支持单进程模式")
    elif cache_type == "redis":
        import redis.asyncio as redis
        from fastapi_cache.backends.redis import RedisBackend
        from redis.asyncio.connection import ConnectionPool

        redis_url = settings.CACHE_REDIS_URL or "redis://localhost:6379/0"
        pool = ConnectionPool.from_url(url=redis_url)
        redis_client = redis.Redis(connection_pool=pool)
        FastAPICache.init(RedisBackend(redis_client), prefix="sqlbot-cache")
        SQLBotLogUtil.info("mySQLBot 使用Redis缓存, 可使用多进程模式")
    else:
        SQLBotLogUtil.warning("mySQLBot 未启用缓存, 可使用多进程模式")


def is_cache_initialized() -> bool:
    # 检查必要的属性是否存在
    if not hasattr(FastAPICache, "_backend") or not hasattr(FastAPICache, "_prefix"):
        return False

    # 检查属性值是否为 None
    if FastAPICache._backend is None or FastAPICache._prefix is None:
        return False

    # 尝试获取后端确认
    try:
        backend = FastAPICache.get_backend()
        return backend is not None
    except (AssertionError, AttributeError, Exception) as e:
        SQLBotLogUtil.debug(f"缓存初始化检查失败: {str(e)}")
        return False
