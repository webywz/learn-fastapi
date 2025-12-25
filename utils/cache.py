"""
===========================================
缓存装饰器模块 (Cache Decorator Module)
===========================================

作用：
  提供简单易用的缓存装饰器

为什么需要装饰器？
  - 代码更简洁
  - 自动处理缓存逻辑
  - 类似前端的 React.memo 或 useMemo

使用示例:
    @cache(ttl=300, key_prefix="user")
    async def get_user(user_id: int):
        # 查询数据库
        return user_data
"""

from functools import wraps
from typing import Optional, Callable, Any
import hashlib
import json
from core.redis import redis_cache
from core.config import settings


def cache(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    key_builder: Optional[Callable] = None
):
    """
    缓存装饰器

    自动缓存函数结果，下次调用时直接从 Redis 读取

    参数:
        ttl: 缓存过期时间（秒），None 使用默认值
        key_prefix: 缓存键前缀（用于区分不同类型的缓存）
        key_builder: 自定义缓存键生成函数

    使用示例:

        # 基础用法
        @cache(ttl=300)
        async def get_user(user_id: int):
            # 第一次调用时执行，结果缓存 5 分钟
            # 5 分钟内再次调用，直接返回缓存
            return await db.query(User).filter(User.id == user_id).first()

        # 指定前缀
        @cache(ttl=600, key_prefix="user")
        async def get_user_profile(user_id: int):
            return user_data

        # 自定义缓存键
        @cache(ttl=300, key_builder=lambda user_id, status: f"users:{status}:{user_id}")
        async def get_user_by_status(user_id: int, status: str):
            return user_data

    工作原理:
        1. 根据函数名和参数生成缓存键
        2. 检查 Redis 中是否有缓存
        3. 有缓存: 直接返回
        4. 无缓存: 执行函数 → 存入 Redis → 返回结果
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 构建缓存键
            if key_builder:
                # 使用自定义键生成函数
                cache_key = key_builder(*args, **kwargs)
            else:
                # 默认键生成逻辑
                cache_key = _build_cache_key(func, key_prefix, args, kwargs)

            # 尝试从缓存获取
            cached_value = await redis_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 缓存未命中，执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            cache_ttl = ttl if ttl is not None else settings.REDIS_CACHE_TTL
            await redis_cache.set(cache_key, result, ttl=cache_ttl)

            return result

        # 添加清除缓存的方法
        async def clear_cache(*args, **kwargs):
            """
            清除特定调用的缓存

            示例:
                await get_user.clear_cache(user_id=1)
            """
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = _build_cache_key(func, key_prefix, args, kwargs)

            await redis_cache.delete(cache_key)

        wrapper.clear_cache = clear_cache

        return wrapper

    return decorator


def _build_cache_key(
    func: Callable,
    prefix: str,
    args: tuple,
    kwargs: dict
) -> str:
    """
    构建缓存键

    格式: {prefix}:{function_name}:{params_hash}

    参数:
        func: 被装饰的函数
        prefix: 键前缀
        args: 位置参数
        kwargs: 关键字参数

    返回:
        str: 缓存键

    示例:
        get_user(1) → "user:get_user:a1b2c3d4"
        get_posts(user_id=1, status="published") → "post:get_posts:e5f6g7h8"
    """
    # 函数名
    func_name = func.__name__

    # 将参数序列化为字符串
    params_str = json.dumps({
        "args": args,
        "kwargs": kwargs
    }, sort_keys=True, ensure_ascii=False)

    # 生成参数哈希（避免键太长）
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]

    # 构建键
    if prefix:
        return f"{prefix}:{func_name}:{params_hash}"
    return f"{func_name}:{params_hash}"


def cache_invalidate(key_pattern: str):
    """
    缓存失效装饰器

    在函数执行后，删除匹配模式的所有缓存

    使用场景:
        - 数据更新后，清除相关缓存
        - 用户修改信息后，清除用户缓存

    参数:
        key_pattern: 缓存键模式（支持 * 通配符）

    使用示例:

        @cache_invalidate("user:*")
        async def update_user(user_id: int, data: dict):
            # 更新用户
            await db.update(User).where(User.id == user_id).values(**data)
            # 函数执行后，自动删除所有 user:* 的缓存
            return True

        @cache_invalidate("post:{post_id}:*")
        async def update_post(post_id: int, data: dict):
            # 更新帖子
            await db.update(Post).where(Post.id == post_id).values(**data)
            # 自动删除该帖子的所有缓存
            return True
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 执行函数
            result = await func(*args, **kwargs)

            # 构建实际的键模式（替换占位符）
            pattern = key_pattern
            if "{" in pattern:
                # 支持模板变量，如 "post:{post_id}:*"
                # 从 kwargs 中提取变量
                pattern = pattern.format(**kwargs)

            # 删除匹配的缓存
            await redis_cache.delete_pattern(pattern)

            return result

        return wrapper

    return decorator


class CacheManager:
    """
    缓存管理器

    提供更灵活的缓存控制

    使用示例:
        cache_manager = CacheManager(prefix="user", ttl=600)

        # 手动设置缓存
        await cache_manager.set("1", user_data)

        # 手动获取缓存
        user = await cache_manager.get("1")

        # 清除所有用户缓存
        await cache_manager.clear_all()
    """

    def __init__(self, prefix: str, ttl: Optional[int] = None):
        """
        初始化缓存管理器

        参数:
            prefix: 缓存键前缀
            ttl: 默认过期时间
        """
        self.prefix = prefix
        self.ttl = ttl if ttl is not None else settings.REDIS_CACHE_TTL

    def _make_key(self, key: str) -> str:
        """生成完整的缓存键"""
        return f"{self.prefix}:{key}"

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置缓存

        参数:
            key: 缓存键（会自动添加前缀）
            value: 缓存值
            ttl: 过期时间（可选，默认使用初始化时的 ttl）
        """
        cache_key = self._make_key(key)
        cache_ttl = ttl if ttl is not None else self.ttl
        await redis_cache.set(cache_key, value, ttl=cache_ttl)

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        参数:
            key: 缓存键

        返回:
            缓存值，不存在返回 None
        """
        cache_key = self._make_key(key)
        return await redis_cache.get(cache_key)

    async def delete(self, key: str):
        """
        删除缓存

        参数:
            key: 缓存键
        """
        cache_key = self._make_key(key)
        await redis_cache.delete(cache_key)

    async def clear_all(self):
        """
        清除所有带该前缀的缓存

        示例:
            user_cache = CacheManager(prefix="user")
            await user_cache.clear_all()  # 删除所有 user:* 缓存
        """
        pattern = f"{self.prefix}:*"
        await redis_cache.delete_pattern(pattern)

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        参数:
            key: 缓存键

        返回:
            bool: 是否存在
        """
        cache_key = self._make_key(key)
        return await redis_cache.exists(cache_key)

    async def get_or_set(
        self,
        key: str,
        func: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        获取缓存，如果不存在则执行函数并缓存结果

        参数:
            key: 缓存键
            func: 如果缓存不存在，执行此函数获取数据
            ttl: 过期时间

        返回:
            缓存值或函数返回值

        示例:
            user_cache = CacheManager(prefix="user")

            user = await user_cache.get_or_set(
                key="1",
                func=lambda: get_user_from_db(1),
                ttl=600
            )
        """
        # 尝试获取缓存
        cached = await self.get(key)
        if cached is not None:
            return cached

        # 缓存不存在，执行函数
        if callable(func):
            result = await func() if asyncio.iscoroutinefunction(func) else func()
        else:
            result = func

        # 存入缓存
        await self.set(key, result, ttl=ttl)

        return result


# ============================================================
# 导入 asyncio（用于 get_or_set）
# ============================================================
import asyncio
