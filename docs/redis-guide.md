# Redis 完整学习指南

## 目录
1. [什么是 Redis](#什么是-redis)
2. [为什么需要 Redis](#为什么需要-redis)
3. [Redis 数据类型](#redis-数据类型)
4. [项目中的 Redis 配置](#项目中的-redis-配置)
5. [基本使用](#基本使用)
6. [缓存策略](#缓存策略)
7. [缓存装饰器使用](#缓存装饰器使用)
8. [实战示例](#实战示例)
9. [最佳实践](#最佳实践)
10. [常见问题](#常见问题)

---

## 什么是 Redis？

**Redis** (REmote DIctionary Server) 是一个开源的**内存数据库**，常用作：
- **缓存**（最常用）
- 消息队列
- Session 存储
- 排行榜
- 计数器

### 核心特点

1. **超快速度** 🚀
   - 数据存储在内存中
   - 读写速度极快（每秒数万次操作）
   - 比数据库快 10-100 倍

2. **支持多种数据结构**
   - String (字符串)
   - Hash (哈希表)
   - List (列表)
   - Set (集合)
   - Sorted Set (有序集合)

3. **持久化**
   - 数据可以保存到硬盘
   - 重启后不会丢失

### 类比前端

```javascript
// 前端 localStorage（浏览器本地存储）
localStorage.setItem('user', JSON.stringify({name: 'Alice'}));
const user = JSON.parse(localStorage.getItem('user'));

// Redis（服务端内存存储，多用户共享）
await redis.set('user:1', JSON.stringify({name: 'Alice'}));
const user = JSON.parse(await redis.get('user:1'));
```

**区别**：
- localStorage: 浏览器端，每个用户独立
- Redis: 服务器端，所有用户共享

---

## 为什么需要 Redis？

###  1. **加速数据访问** 🚀

```python
# ❌ 没有缓存：每次都查数据库（慢）
async def get_user(user_id: int):
    user = await db.query(User).filter(User.id == user_id).first()
    return user  # 耗时: 50ms

# ✅ 有缓存：第一次查数据库，之后走缓存（快）
async def get_user(user_id: int):
    # 先查缓存
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return cached  # 耗时: 1ms（快 50 倍！）

    # 缓存未命中，查数据库
    user = await db.query(User).filter(User.id == user_id).first()

    # 存入缓存
    await redis.set(f"user:{user_id}", user, ttl=300)

    return user
```

### 2. **减轻数据库压力** 💪

```
场景：1000 个用户同时访问热门文章

没有缓存:
  1000 次数据库查询 → 数据库崩溃 💥

有缓存:
  第 1 次查数据库
  后 999 次查 Redis → 数据库轻松 ✅
```

### 3. **Session 存储** 🔐

```python
# 用户登录后，Session 存入 Redis
await redis.set(f"session:{session_id}", user_data, ttl=3600)

# 后续请求快速验证
user = await redis.get(f"session:{session_id}")
```

### 4. **API 限流** 🚦

```python
# 限制每个 IP 每分钟最多 100 次请求
async def rate_limit(ip: str):
    key = f"rate_limit:{ip}"
    count = await redis.increment(key)

    if count == 1:
        await redis.expire(key, 60)  # 60 秒后过期

    if count > 100:
        raise HTTPException(status_code=429, detail="请求过快")
```

---

## Redis 数据类型

### 1. String（字符串）

最基本的类型，可以存储字符串、数字、JSON。

```python
# 设置值
await redis.set("key", "value")
await redis.set("user:1:name", "Alice")
await redis.set("count", 0)

# 获取值
value = await redis.get("key")  # "value"

# 设置过期时间
await redis.setex("temp", 300, "data")  # 300 秒后过期

# 递增/递减（用于计数）
await redis.incr("count")  # count 变成 1
await redis.incr("count")  # count 变成 2
await redis.decr("count")  # count 变成 1
```

**使用场景**：
- 缓存 JSON 数据
- 计数器（浏览量、点赞数）
- Session 存储

### 2. Hash（哈希表）

适合存储对象，类似 Python 的字典。

```python
# 设置哈希
await redis.hset("user:1", mapping={
    "name": "Alice",
    "email": "alice@example.com",
    "age": 25
})

# 获取单个字段
name = await redis.hget("user:1", "name")  # "Alice"

# 获取所有字段
user = await redis.hgetall("user:1")
# {"name": "Alice", "email": "alice@example.com", "age": "25"}

# 修改单个字段
await redis.hset("user:1", "age", 26)
```

**使用场景**：
- 存储用户信息
- 存储配置

### 3. List（列表）

有序列表，可以从两端添加/删除元素。

```python
# 添加元素
await redis.lpush("messages", "message1")  # 左侧添加
await redis.rpush("messages", "message2")  # 右侧添加

# 获取列表
messages = await redis.lrange("messages", 0, -1)  # 获取所有
# ["message1", "message2"]

# 弹出元素
msg = await redis.lpop("messages")  # 左侧弹出
msg = await redis.rpop("messages")  # 右侧弹出
```

**使用场景**：
- 消息队列
- 最新动态列表
- 任务队列

### 4. Set（集合）

无序、不重复的集合。

```python
# 添加元素
await redis.sadd("tags:post:123", "Python", "FastAPI", "Redis")

# 获取所有元素
tags = await redis.smembers("tags:post:123")
# {"Python", "FastAPI", "Redis"}

# 检查元素是否存在
exists = await redis.sismember("tags:post:123", "Python")  # True

# 集合运算
await redis.sadd("user:1:following", "user:2", "user:3")
await redis.sadd("user:2:following", "user:3", "user:4")

# 交集（共同关注）
common = await redis.sinter("user:1:following", "user:2:following")
# {"user:3"}
```

**使用场景**：
- 标签系统
- 好友关系
- 去重

### 5. Sorted Set（有序集合）

带分数的集合，自动按分数排序。

```python
# 添加元素（带分数）
await redis.zadd("leaderboard", {
    "user:1": 100,  # 用户1: 100分
    "user:2": 200,  # 用户2: 200分
    "user:3": 150   # 用户3: 150分
})

# 获取排名前 3（分数从高到低）
top3 = await redis.zrevrange("leaderboard", 0, 2, withscores=True)
# [("user:2", 200), ("user:3", 150), ("user:1", 100)]

# 增加分数
await redis.zincrby("leaderboard", 50, "user:1")  # user:1 += 50

# 获取某人的排名
rank = await redis.zrevrank("leaderboard", "user:1")  # 排名（从0开始）
```

**使用场景**：
- 排行榜
- 热门文章
- 优先级队列

---

## 项目中的 Redis 配置

### 1. 环境变量配置 (`.env`)

```env
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_PASSWORD="root"
REDIS_DB=0
REDIS_CACHE_TTL=300
```

### 2. 配置类 (`core/config.py`)

```python
class Settings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_CACHE_TTL: int = 300

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
```

### 3. Redis 客户端 (`core/redis.py`)

已创建的工具：
- `get_redis()`: 获取 Redis 客户端
- `close_redis()`: 关闭连接
- `RedisCache`: 缓存工具类
- `redis_cache`: 全局缓存实例

---

## 基本使用

### 方式 1: 直接使用 Redis 客户端

```python
from core.redis import get_redis

async def example():
    redis = await get_redis()

    # 设置值
    await redis.set("key", "value")

    # 获取值
    value = await redis.get("key")

    # 删除值
    await redis.delete("key")
```

### 方式 2: 使用封装的 RedisCache 类

```python
from core.redis import redis_cache

async def example():
    # 设置缓存（JSON 自动序列化）
    await redis_cache.set("user:1", {"name": "Alice", "age": 25}, ttl=300)

    # 获取缓存（自动反序列化）
    user = await redis_cache.get("user:1")

    # 删除缓存
    await redis_cache.delete("user:1")

    # 检查存在
    exists = await redis_cache.exists("user:1")

    # 递增计数
    views = await redis_cache.increment("post:123:views")

    # 批量删除
    await redis_cache.delete_pattern("user:*")
```

### 方式 3: 使用缓存装饰器（推荐）⭐

```python
from utils.cache import cache

@cache(ttl=600, key_prefix="user")
async def get_user(user_id: int):
    # 第一次调用：执行函数并缓存结果
    # 后续调用：直接返回缓存（10分钟内）
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
```

---

## 缓存策略

### 1. Cache-Aside（旁路缓存）

**最常用的策略** ⭐

```python
async def get_user(user_id: int):
    # 1. 查缓存
    user = await redis_cache.get(f"user:{user_id}")
    if user:
        return user  # 缓存命中

    # 2. 缓存未命中，查数据库
    user = await db.query(User).filter(User.id == user_id).first()

    # 3. 写入缓存
    if user:
        await redis_cache.set(f"user:{user_id}", user, ttl=300)

    return user
```

**流程**：
```
查询 → 查缓存 → 命中? 返回 : 查DB → 写缓存 → 返回
```

### 2. Write-Through（写穿）

```python
async def update_user(user_id: int, data: dict):
    # 1. 更新数据库
    await db.update(User).where(User.id == user_id).values(**data)

    # 2. 同时更新缓存
    user = await db.query(User).filter(User.id == user_id).first()
    await redis_cache.set(f"user:{user_id}", user, ttl=300)
```

### 3. Write-Behind（写回）

```python
async def update_user(user_id: int, data: dict):
    # 1. 先更新缓存
    await redis_cache.set(f"user:{user_id}", data, ttl=300)

    # 2. 异步更新数据库（通过消息队列）
    await task_queue.send("update_user_db", user_id=user_id, data=data)
```

### 4. Refresh-Ahead（预刷新）

```python
async def get_popular_posts():
    posts = await redis_cache.get("popular_posts")

    if posts:
        # 如果缓存快过期，后台刷新
        ttl = await redis_cache.ttl("popular_posts")
        if ttl < 60:  # 剩余时间 < 1 分钟
            asyncio.create_task(refresh_popular_posts())

        return posts

    return await refresh_popular_posts()
```

---

## 缓存装饰器使用

### 1. 基础用法

```python
from utils.cache import cache

@cache(ttl=300)
async def get_user(user_id: int):
    """缓存 5 分钟"""
    return await db.query(User).filter(User.id == user_id).first()
```

### 2. 指定键前缀

```python
@cache(ttl=600, key_prefix="user")
async def get_user_profile(user_id: int):
    """缓存键: user:get_user_profile:{hash}"""
    return user_data
```

### 3. 自定义缓存键

```python
@cache(
    ttl=300,
    key_builder=lambda user_id, status: f"users:{status}:{user_id}"
)
async def get_user_by_status(user_id: int, status: str):
    """缓存键: users:active:123"""
    return user_data
```

### 4. 缓存失效装饰器

```python
from utils.cache import cache_invalidate

@cache_invalidate("user:*")
async def update_user(user_id: int, data: dict):
    """更新用户后，自动清除所有 user:* 缓存"""
    await db.update(User).where(User.id == user_id).values(**data)
```

### 5. 手动清除缓存

```python
@cache(ttl=300)
async def get_user(user_id: int):
    return user_data

# 调用函数
user = await get_user(1)

# 手动清除缓存
await get_user.clear_cache(1)
```

### 6. 使用缓存管理器

```python
from utils.cache import CacheManager

# 创建用户缓存管理器
user_cache = CacheManager(prefix="user", ttl=600)

# 设置缓存
await user_cache.set("1", user_data)

# 获取缓存
user = await user_cache.get("1")

# 清除所有用户缓存
await user_cache.clear_all()

# 获取或设置
user = await user_cache.get_or_set(
    key="1",
    func=lambda: get_user_from_db(1),
    ttl=600
)
```

---

## 实战示例

### 示例 1: 用户信息缓存

```python
from utils.cache import cache, cache_invalidate

class UserService:
    @staticmethod
    @cache(ttl=600, key_prefix="user")
    async def get_user_by_id(db: AsyncSession, user_id: int):
        """查询用户（带缓存）"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    @cache_invalidate("user:*")
    async def update_user(db: AsyncSession, user: User, data: dict):
        """更新用户（自动清除缓存）"""
        for key, value in data.items():
            setattr(user, key, value)
        await db.commit()
        return user
```

### 示例 2: 热门文章缓存

```python
@cache(ttl=3600, key_prefix="posts")
async def get_hot_posts(limit: int = 10):
    """获取热门文章（缓存 1 小时）"""
    result = await db.execute(
        select(Post).order_by(Post.views.desc()).limit(limit)
    )
    return result.scalars().all()
```

### 示例 3: API 限流

```python
from core.redis import redis_cache
from fastapi import HTTPException

async def rate_limit(user_id: int, max_requests: int = 100, window: int = 60):
    """
    限流：每分钟最多 100 次请求

    参数:
        user_id: 用户 ID
        max_requests: 最大请求数
        window: 时间窗口（秒）
    """
    key = f"rate_limit:user:{user_id}"

    # 递增计数
    count = await redis_cache.increment(key)

    # 第一次请求，设置过期时间
    if count == 1:
        await redis_cache.expire(key, window)

    # 超过限制
    if count > max_requests:
        raise HTTPException(
            status_code=429,
            detail=f"请求过快，请在 {window} 秒后重试"
        )

# 使用
@app.get("/api/data")
async def get_data(current_user: User = Depends(get_current_user)):
    await rate_limit(current_user.id)
    return {"data": "..."}
```

### 示例 4: 文章浏览量计数

```python
from core.redis import redis_cache

async def increment_post_views(post_id: int):
    """增加文章浏览量"""
    # Redis 计数
    views = await redis_cache.increment(f"post:{post_id}:views")

    # 每 100 次同步到数据库
    if views % 100 == 0:
        await db.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(views=views)
        )

    return views

@app.get("/posts/{post_id}")
async def get_post(post_id: int):
    # 增加浏览量
    views = await increment_post_views(post_id)

    # 获取文章
    post = await get_post_by_id(post_id)
    post.views = views

    return post
```

### 示例 5: Session 存储

```python
import secrets
from core.redis import redis_cache

async def create_session(user_id: int) -> str:
    """创建 Session"""
    # 生成 Session ID
    session_id = secrets.token_urlsafe(32)

    # 存储 Session 数据
    await redis_cache.set(
        f"session:{session_id}",
        {"user_id": user_id, "created_at": datetime.now().isoformat()},
        ttl=3600  # 1 小时
    )

    return session_id

async def get_session(session_id: str) -> dict:
    """获取 Session"""
    return await redis_cache.get(f"session:{session_id}")

async def delete_session(session_id: str):
    """删除 Session（登出）"""
    await redis_cache.delete(f"session:{session_id}")
```

### 示例 6: 排行榜

```python
from core.redis import get_redis

async def update_leaderboard(user_id: int, score: int):
    """更新排行榜分数"""
    redis = await get_redis()
    await redis.zadd("leaderboard", {f"user:{user_id}": score})

async def get_top_users(limit: int = 10):
    """获取排行榜前 N 名"""
    redis = await get_redis()
    top = await redis.zrevrange("leaderboard", 0, limit - 1, withscores=True)

    return [
        {"user_id": user.split(":")[1], "score": int(score)}
        for user, score in top
    ]

async def get_user_rank(user_id: int):
    """获取用户排名"""
    redis = await get_redis()
    rank = await redis.zrevrank("leaderboard", f"user:{user_id}")
    return rank + 1 if rank is not None else None
```

---

## 最佳实践

### ✅ 1. 合理设置过期时间

```python
# 用户信息: 5-10 分钟
@cache(ttl=600)
async def get_user(user_id: int):
    ...

# 热门数据: 1 小时
@cache(ttl=3600)
async def get_hot_posts():
    ...

# 静态数据: 24 小时
@cache(ttl=86400)
async def get_categories():
    ...
```

### ✅ 2. 使用有意义的键名

```python
# ✅ 好的键名（有层次结构）
user:123:profile
user:123:settings
post:456:comments
session:abc123

# ❌ 不好的键名
user123
p456
s1
```

### ✅ 3. 序列化复杂对象

```python
import json

# 存储
user_data = {"id": 1, "name": "Alice", "age": 25}
await redis.set("user:1", json.dumps(user_data))

# 读取
data = await redis.get("user:1")
user = json.loads(data)
```

### ✅ 4. 缓存空结果

```python
@cache(ttl=300)
async def get_user(user_id: int):
    user = await db.query(User).filter(User.id == user_id).first()

    # 即使用户不存在也缓存（避免缓存穿透）
    if not user:
        return None  # 缓存 None 值

    return user
```

### ✅ 5. 避免缓存雪崩

```python
import random

# 给 TTL 加上随机值，避免大量缓存同时过期
ttl = 300 + random.randint(0, 60)  # 300-360 秒
await redis_cache.set("key", "value", ttl=ttl)
```

### ✅ 6. 使用管道批量操作

```python
redis = await get_redis()

# 批量设置
async with redis.pipeline() as pipe:
    for i in range(100):
        pipe.set(f"key:{i}", f"value:{i}")
    await pipe.execute()
```

### ✅ 7. 监控缓存命中率

```python
async def get_with_stats(key: str):
    value = await redis_cache.get(key)

    if value:
        await redis_cache.increment("cache:hits")
    else:
        await redis_cache.increment("cache:misses")

    return value

# 查看命中率
hits = await redis_cache.get("cache:hits") or 0
misses = await redis_cache.get("cache:misses") or 0
hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0
print(f"缓存命中率: {hit_rate:.2%}")
```

---

## 常见问题

### Q1: 缓存穿透（Cache Penetration）

**问题**: 查询不存在的数据，每次都打到数据库

```python
# 查询 user_id=99999（不存在）
user = await get_user(99999)  # 每次都查数据库
```

**解决**：缓存空结果

```python
@cache(ttl=300)
async def get_user(user_id: int):
    user = await db.query(User).filter(User.id == user_id).first()

    # 即使不存在也缓存
    return user  # 可能是 None
```

### Q2: 缓存雪崩（Cache Avalanche）

**问题**: 大量缓存同时过期，数据库压力剧增

**解决**：TTL 加随机值

```python
import random

ttl = 300 + random.randint(0, 60)  # 300-360 秒
await redis_cache.set("key", "value", ttl=ttl)
```

### Q3: 缓存击穿（Cache Breakdown）

**问题**: 热点数据过期，大量请求同时打到数据库

**解决**：使用锁

```python
import asyncio

_locks = {}

async def get_user(user_id: int):
    # 先查缓存
    user = await redis_cache.get(f"user:{user_id}")
    if user:
        return user

    # 获取锁
    if user_id not in _locks:
        _locks[user_id] = asyncio.Lock()

    async with _locks[user_id]:
        # 再次查缓存（可能已被其他线程写入）
        user = await redis_cache.get(f"user:{user_id}")
        if user:
            return user

        # 查数据库
        user = await db.query(User).filter(User.id == user_id).first()

        # 写缓存
        await redis_cache.set(f"user:{user_id}", user, ttl=300)

        return user
```

### Q4: 数据一致性问题

**问题**: 数据库更新了，缓存还是旧数据

**解决**：更新时清除缓存

```python
@cache_invalidate("user:*")
async def update_user(user_id: int, data: dict):
    # 更新数据库
    await db.update(User).where(User.id == user_id).values(**data)
    # 自动清除缓存
```

### Q5: Redis 内存不足

**解决**：
1. 设置过期时间
2. 使用 LRU 淘汰策略
3. 增加内存
4. 删除不需要的键

```python
# 批量删除旧缓存
await redis_cache.delete_pattern("old_data:*")
```

---

## 总结

### 核心要点

1. **Redis 是什么？**
   - 内存数据库
   - 速度极快
   - 支持多种数据结构

2. **为什么用 Redis？**
   - 加速数据访问
   - 减轻数据库压力
   - Session 存储
   - 限流、计数

3. **如何使用？**
   - 缓存装饰器（推荐）
   - RedisCache 工具类
   - 直接使用 Redis 客户端

4. **最佳实践**
   - 合理设置 TTL
   - 有意义的键名
   - 缓存空结果
   - 避免缓存雪崩

### 使用建议

| 场景 | TTL | 数据类型 |
|------|-----|---------|
| 用户信息 | 5-10 分钟 | String/Hash |
| 热门数据 | 1 小时 | String/List |
| 静态数据 | 24 小时 | String/Hash |
| 计数器 | 永久 | String |
| 排行榜 | 实时更新 | Sorted Set |
| Session | 30 分钟 | String/Hash |

### 快速开始

```python
# 1. 导入
from utils.cache import cache

# 2. 使用装饰器
@cache(ttl=300, key_prefix="user")
async def get_user(user_id: int):
    return await db.query(User).filter(User.id == user_id).first()

# 3. 调用（第一次查DB，后续走缓存）
user = await get_user(1)
```

就这么简单！🎉

Redis 是现代 Web 开发的必备技能，掌握它能让你的应用性能提升数倍！
