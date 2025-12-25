"""
===========================================
Redis 工具模块 (Redis Utility Module)
===========================================

作用：
  提供 Redis 连接和常用操作的封装

为什么需要 Redis？
  1. 缓存：加速数据访问，减少数据库压力
  2. Session 存储：存储用户会话
  3. 消息队列：简单的任务队列
  4. 限流：API 访问频率控制
  5. 分布式锁：多服务器协调

类比前端：
  - 类似浏览器的 localStorage
  - 但是在服务端，多个用户共享
  - 速度更快，支持过期时间
"""

import redis.asyncio as redis
from redis.asyncio import Redis
from typing import Optional, Any
import json
from core.config import settings


# ============================================================
# Redis 连接池（全局单例）
# ============================================================

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """
    获取 Redis 客户端（异步）

    使用连接池，提高性能

    为什么用连接池？
      - 重用连接，避免频繁建立/关闭
      - 类似数据库连接池

    使用示例:
        redis_client = await get_redis()
        await redis_client.set("key", "value")
        value = await redis_client.get("key")
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,  # 自动解码为字符串
            max_connections=10,     # 连接池大小
        )

    return _redis_client


async def close_redis():
    """
    关闭 Redis 连接

    应该在应用关闭时调用

    在 main.py 的 shutdown 事件中调用：
        @app.on_event("shutdown")
        async def shutdown():
            await close_redis()
    """
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None


# ============================================================
# Redis 工具类
# ============================================================

class RedisCache:
    """
    Redis 缓存工具类

    封装常用的缓存操作

    使用示例:
        cache = RedisCache()

        # 设置缓存
        await cache.set("user:1", {"name": "Alice"}, ttl=300)

        # 获取缓存
        user = await cache.get("user:1")

        # 删除缓存
        await cache.delete("user:1")
    """

    def __init__(self):
        self.client: Optional[Redis] = None

    async def _get_client(self) -> Redis:
        """获取 Redis 客户端"""
        if self.client is None:
            self.client = await get_redis()
        return self.client

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存

        参数:
            key: 缓存键
            value: 缓存值（支持 dict, list, str, int 等）
            ttl: 过期时间（秒），None 表示永不过期

        返回:
            bool: 是否成功

        示例:
            await cache.set("user:1", {"name": "Alice"}, ttl=300)
        """
        client = await self._get_client()

        # 如果是复杂对象（dict, list），转为 JSON
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)

        if ttl:
            return await client.setex(key, ttl, value)
        else:
            return await client.set(key, value)

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        参数:
            key: 缓存键

        返回:
            缓存值，不存在返回 None

        示例:
            user = await cache.get("user:1")
        """
        client = await self._get_client()
        value = await client.get(key)

        if value is None:
            return None

        # 尝试解析 JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # 不是 JSON，直接返回字符串
            return value

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        参数:
            key: 缓存键

        返回:
            bool: 是否成功删除

        示例:
            await cache.delete("user:1")
        """
        client = await self._get_client()
        result = await client.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        参数:
            key: 缓存键

        返回:
            bool: 是否存在

        示例:
            if await cache.exists("user:1"):
                print("缓存存在")
        """
        client = await self._get_client()
        return await client.exists(key) > 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        设置缓存过期时间

        参数:
            key: 缓存键
            ttl: 过期时间（秒）

        返回:
            bool: 是否成功

        示例:
            await cache.expire("user:1", 600)  # 10分钟后过期
        """
        client = await self._get_client()
        return await client.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        """
        获取缓存剩余过期时间

        参数:
            key: 缓存键

        返回:
            int: 剩余秒数
                -1: 永不过期
                -2: 键不存在

        示例:
            remaining = await cache.ttl("user:1")
            print(f"还有 {remaining} 秒过期")
        """
        client = await self._get_client()
        return await client.ttl(key)

    async def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有缓存

        参数:
            pattern: 模式（支持 * 通配符）

        返回:
            int: 删除的键数量

        示例:
            # 删除所有用户缓存
            await cache.delete_pattern("user:*")

            # 删除所有帖子缓存
            await cache.delete_pattern("post:*")
        """
        client = await self._get_client()

        # 查找匹配的键
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)

        # 批量删除
        if keys:
            return await client.delete(*keys)
        return 0

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        递增计数器

        参数:
            key: 计数器键
            amount: 递增量（默认 1）

        返回:
            int: 递增后的值

        使用场景:
            - 访问计数
            - API 限流
            - 点赞数统计

        示例:
            # 文章浏览次数 +1
            views = await cache.increment("post:123:views")
            print(f"浏览次数: {views}")
        """
        client = await self._get_client()
        return await client.incrby(key, amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        递减计数器

        参数:
            key: 计数器键
            amount: 递减量（默认 1）

        返回:
            int: 递减后的值

        示例:
            remaining = await cache.decrement("api:limit:user:1")
        """
        client = await self._get_client()
        return await client.decrby(key, amount)

    async def set_hash(
        self,
        key: str,
        data: dict,
        ttl: Optional[int] = None
    ) -> bool:
        """
        存储哈希表（适合存储对象）

        参数:
            key: 哈希表键
            data: 字典数据
            ttl: 过期时间（秒）

        返回:
            bool: 是否成功

        使用场景:
            - 存储用户信息
            - 存储配置

        示例:
            await cache.set_hash("user:1", {
                "name": "Alice",
                "email": "alice@example.com",
                "age": 25
            }, ttl=600)
        """
        client = await self._get_client()

        # 转换值为字符串
        str_data = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in data.items()}

        await client.hset(key, mapping=str_data)

        if ttl:
            await client.expire(key, ttl)

        return True

    async def get_hash(self, key: str) -> Optional[dict]:
        """
        获取哈希表

        参数:
            key: 哈希表键

        返回:
            dict: 哈希表数据，不存在返回 None

        示例:
            user = await cache.get_hash("user:1")
            print(user["name"])
        """
        client = await self._get_client()
        data = await client.hgetall(key)

        if not data:
            return None

        # 尝试解析 JSON 值
        result = {}
        for k, v in data.items():
            try:
                result[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                result[k] = v

        return result

    async def add_to_set(self, key: str, *values: Any) -> int:
        """
        添加元素到集合

        参数:
            key: 集合键
            values: 要添加的值

        返回:
            int: 添加的元素数量

        使用场景:
            - 标签系统
            - 关注列表
            - 去重

        示例:
            # 添加标签
            await cache.add_to_set("post:123:tags", "Python", "FastAPI", "Redis")
        """
        client = await self._get_client()
        str_values = [json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                      for v in values]
        return await client.sadd(key, *str_values)

    async def get_set(self, key: str) -> set:
        """
        获取集合所有元素

        参数:
            key: 集合键

        返回:
            set: 集合元素

        示例:
            tags = await cache.get_set("post:123:tags")
            print(tags)  # {"Python", "FastAPI", "Redis"}
        """
        client = await self._get_client()
        values = await client.smembers(key)

        result = set()
        for v in values:
            try:
                result.add(json.loads(v))
            except (json.JSONDecodeError, TypeError):
                result.add(v)

        return result


# ============================================================
# 创建全局缓存实例
# ============================================================

redis_cache = RedisCache()
"""
全局 Redis 缓存实例

使用示例:
    from core.redis import redis_cache

    # 设置缓存
    await redis_cache.set("key", "value", ttl=300)

    # 获取缓存
    value = await redis_cache.get("key")

    # 删除缓存
    await redis_cache.delete("key")
"""
