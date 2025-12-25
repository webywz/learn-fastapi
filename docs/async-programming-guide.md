# Python 异步编程完整指南

## 目录
1. [什么是异步编程](#什么是异步编程)
2. [同步 vs 异步](#同步-vs-异步)
3. [async/await 语法](#asyncawait-语法)
4. [asyncio 核心概念](#asyncio-核心概念)
5. [异步数据库操作](#异步数据库操作)
6. [异步 HTTP 请求](#异步-http-请求)
7. [并发执行](#并发执行)
8. [常见陷阱](#常见陷阱)
9. [最佳实践](#最佳实践)
10. [实战示例](#实战示例)

---

## 什么是异步编程？

### 基本概念

**异步编程（Asynchronous Programming）** 允许程序在等待某个操作完成时，继续执行其他任务，而不是傻傻地等待。

### 类比前端（给你这个前端开发者）

```javascript
// JavaScript 异步
async function fetchData() {
    const response = await fetch('/api/users');  // 等待网络请求
    const data = await response.json();
    return data;
}
```

```python
# Python 异步（几乎一样！）
async def fetch_data():
    response = await client.get('/api/users')  # 等待网络请求
    data = await response.json()
    return data
```

**Python 的异步编程和 JavaScript 的 async/await 非常相似！**

---

## 同步 vs 异步

### 生活中的例子

#### 🐌 同步（Synchronous）
```
你去餐厅点餐：
1. 点餐 → 站在柜台等 5 分钟 → 拿到食物
2. 什么都不能做，只能等
3. 效率低下
```

#### 🚀 异步（Asynchronous）
```
你去餐厅点餐：
1. 点餐 → 拿到取餐号码 → 坐下玩手机
2. 等待期间可以做其他事
3. 叫号后去取餐
4. 效率高
```

### 代码对比

#### 同步代码（慢）

```python
import time
import requests

def fetch_user(user_id):
    """同步获取用户数据（阻塞）"""
    response = requests.get(f'https://api.example.com/users/{user_id}')
    return response.json()

def main():
    start = time.time()

    # 串行执行，一个接一个
    user1 = fetch_user(1)  # 等待 1 秒
    user2 = fetch_user(2)  # 等待 1 秒
    user3 = fetch_user(3)  # 等待 1 秒

    print(f"总耗时: {time.time() - start}秒")  # 约 3 秒

main()
```

**耗时**: 1秒 + 1秒 + 1秒 = **3秒**

#### 异步代码（快）

```python
import asyncio
import httpx
import time

async def fetch_user(user_id):
    """异步获取用户数据（非阻塞）"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f'https://api.example.com/users/{user_id}')
        return response.json()

async def main():
    start = time.time()

    # 并发执行，同时进行
    results = await asyncio.gather(
        fetch_user(1),  # 同时开始
        fetch_user(2),  # 同时开始
        fetch_user(3),  # 同时开始
    )

    print(f"总耗时: {time.time() - start}秒")  # 约 1 秒

asyncio.run(main())
```

**耗时**: max(1秒, 1秒, 1秒) = **1秒** 🚀

---

## async/await 语法

### 基本语法

#### 1. 定义异步函数

```python
# 同步函数
def sync_function():
    return "Hello"

# 异步函数（加上 async 关键字）
async def async_function():
    return "Hello"
```

#### 2. 调用异步函数

```python
# ❌ 错误：不能直接调用
result = async_function()  # 返回的是 coroutine 对象，不是结果

# ✅ 正确：使用 await
result = await async_function()  # 在异步函数中

# ✅ 正确：使用 asyncio.run（程序入口）
result = asyncio.run(async_function())  # 在同步代码中
```

### 与 JavaScript 对比

| JavaScript | Python |
|------------|--------|
| `async function foo() {}` | `async def foo():` |
| `await foo()` | `await foo()` |
| `Promise.all([...])` | `asyncio.gather(...)` |
| `Promise.race([...])` | `asyncio.wait(..., return_when=FIRST_COMPLETED)` |
| `setTimeout()` | `asyncio.sleep()` |

### 示例：等待多个任务

```python
# JavaScript
async function getUsers() {
    const [user1, user2, user3] = await Promise.all([
        fetchUser(1),
        fetchUser(2),
        fetchUser(3)
    ]);
}

# Python（几乎一样）
async def get_users():
    user1, user2, user3 = await asyncio.gather(
        fetch_user(1),
        fetch_user(2),
        fetch_user(3)
    )
```

---

## asyncio 核心概念

### 1. Coroutine（协程）

协程是可以暂停和恢复的函数。

```python
async def my_coroutine():
    print("开始")
    await asyncio.sleep(1)  # 暂停 1 秒
    print("结束")
    return "完成"

# 创建协程对象
coro = my_coroutine()

# 运行协程
result = asyncio.run(coro)
```

### 2. Event Loop（事件循环）

事件循环负责调度和执行异步任务。

```python
import asyncio

async def say_hello():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

# 方式 1: 使用 asyncio.run（推荐）
asyncio.run(say_hello())

# 方式 2: 手动管理事件循环（不推荐）
loop = asyncio.get_event_loop()
loop.run_until_complete(say_hello())
loop.close()
```

### 3. Task（任务）

Task 是对协程的封装，允许并发执行。

```python
async def main():
    # 创建任务（立即开始执行）
    task1 = asyncio.create_task(say_hello())
    task2 = asyncio.create_task(say_hello())

    # 等待任务完成
    await task1
    await task2

asyncio.run(main())
```

### 4. asyncio.sleep()

异步版的 `time.sleep()`。

```python
# ❌ 错误：time.sleep 会阻塞整个程序
import time
async def wrong():
    time.sleep(1)  # 阻塞！其他协程也会停止

# ✅ 正确：使用 asyncio.sleep
async def correct():
    await asyncio.sleep(1)  # 不阻塞，其他协程可以运行
```

---

## 异步数据库操作

### SQLAlchemy 异步示例

你的项目已经使用了异步数据库，让我们看看如何使用：

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User

async def get_user_by_id(db: AsyncSession, user_id: int):
    """
    异步查询用户

    注意：
    - db.execute() 是异步的，需要 await
    - result.scalar_one_or_none() 是同步的，不需要 await
    """
    # 执行查询（异步）
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    # 获取结果（同步）
    user = result.scalar_one_or_none()
    return user

async def create_user(db: AsyncSession, username: str, email: str):
    """异步创建用户"""
    user = User(username=username, email=email, hashed_password="...")

    # 添加到会话（同步）
    db.add(user)

    # 提交到数据库（异步）
    await db.commit()

    # 刷新对象以获取生成的 ID（异步）
    await db.refresh(user)

    return user

async def get_all_users(db: AsyncSession):
    """异步查询所有用户"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users
```

### 在 FastAPI 中使用

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    FastAPI 路由函数

    注意：
    - 路由函数是 async def
    - 数据库操作使用 await
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/users")
async def create_user_endpoint(
    username: str,
    email: str,
    db: AsyncSession = Depends(get_db)
):
    user = await create_user(db, username, email)
    return user
```

---

## 异步 HTTP 请求

### 使用 httpx（异步版的 requests）

```python
import httpx
import asyncio

async def fetch_url(url: str):
    """异步获取单个 URL"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

async def fetch_multiple_urls():
    """并发获取多个 URL"""
    urls = [
        "https://api.github.com/users/octocat",
        "https://api.github.com/users/torvalds",
        "https://api.github.com/users/gvanrossum",
    ]

    async with httpx.AsyncClient() as client:
        # 并发执行
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)

        # 解析响应
        results = [resp.json() for resp in responses]
        return results

# 运行
asyncio.run(fetch_multiple_urls())
```

### POST 请求

```python
async def create_user_api(username: str, email: str):
    """异步 POST 请求"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/users",
            json={
                "username": username,
                "email": email
            }
        )
        return response.json()
```

### 带超时的请求

```python
async def fetch_with_timeout(url: str, timeout: int = 5):
    """带超时的异步请求"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            return response.json()
    except httpx.TimeoutException:
        print(f"请求超时: {url}")
        return None
```

---

## 并发执行

### 1. asyncio.gather() - 并发执行多个任务

```python
async def task1():
    await asyncio.sleep(1)
    return "Task 1 done"

async def task2():
    await asyncio.sleep(2)
    return "Task 2 done"

async def task3():
    await asyncio.sleep(1.5)
    return "Task 3 done"

async def main():
    # 并发执行，等待所有任务完成
    results = await asyncio.gather(
        task1(),
        task2(),
        task3()
    )
    print(results)  # ['Task 1 done', 'Task 2 done', 'Task 3 done']

asyncio.run(main())
```

**特点**：
- 等待所有任务完成
- 按顺序返回结果
- 如果一个任务失败，默认会抛出异常

### 2. asyncio.create_task() - 创建后台任务

```python
async def background_task():
    while True:
        print("后台任务运行中...")
        await asyncio.sleep(2)

async def main():
    # 创建后台任务（不等待）
    task = asyncio.create_task(background_task())

    # 做其他事情
    await asyncio.sleep(5)

    # 取消后台任务
    task.cancel()

asyncio.run(main())
```

### 3. asyncio.wait() - 更灵活的等待

```python
async def main():
    tasks = [
        asyncio.create_task(task1()),
        asyncio.create_task(task2()),
        asyncio.create_task(task3())
    ]

    # 等待第一个完成
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    # 取消剩余任务
    for task in pending:
        task.cancel()
```

### 4. asyncio.as_completed() - 按完成顺序处理

```python
async def main():
    tasks = [task1(), task2(), task3()]

    # 按完成顺序处理
    for coro in asyncio.as_completed(tasks):
        result = await coro
        print(f"完成: {result}")

asyncio.run(main())
```

---

## 异步上下文管理器

### 使用 async with

```python
# 同步上下文管理器
with open('file.txt') as f:
    content = f.read()

# 异步上下文管理器
async with httpx.AsyncClient() as client:
    response = await client.get('https://example.com')

# 数据库会话
async with AsyncSessionLocal() as session:
    user = await session.get(User, 1)
```

### 自定义异步上下文管理器

```python
class AsyncDatabaseConnection:
    async def __aenter__(self):
        """进入上下文时调用"""
        print("连接数据库...")
        await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时调用"""
        print("关闭数据库连接...")
        await asyncio.sleep(0.1)

    async def query(self, sql):
        print(f"执行查询: {sql}")
        await asyncio.sleep(0.5)
        return "结果"

# 使用
async def main():
    async with AsyncDatabaseConnection() as db:
        result = await db.query("SELECT * FROM users")
        print(result)

asyncio.run(main())
```

---

## 异步生成器

### 定义异步生成器

```python
async def async_range(start, stop):
    """异步生成器"""
    for i in range(start, stop):
        await asyncio.sleep(0.1)  # 模拟异步操作
        yield i

# 使用 async for
async def main():
    async for number in async_range(0, 5):
        print(number)

asyncio.run(main())
```

### 实际应用：分页查询

```python
async def fetch_users_paginated(db: AsyncSession, page_size: int = 100):
    """异步生成器：分页查询用户"""
    offset = 0

    while True:
        # 查询一页数据
        result = await db.execute(
            select(User).offset(offset).limit(page_size)
        )
        users = result.scalars().all()

        # 如果没有数据了，停止
        if not users:
            break

        # 逐个返回用户
        for user in users:
            yield user

        offset += page_size

# 使用
async def process_all_users(db: AsyncSession):
    async for user in fetch_users_paginated(db):
        print(f"处理用户: {user.username}")
        # 处理用户...
```

---

## 常见陷阱

### ❌ 陷阱 1: 在异步函数中使用同步阻塞代码

```python
import time

# ❌ 错误
async def bad_function():
    time.sleep(1)  # 阻塞整个事件循环！
    return "done"

# ✅ 正确
async def good_function():
    await asyncio.sleep(1)  # 非阻塞
    return "done"
```

### ❌ 陷阱 2: 忘记使用 await

```python
# ❌ 错误
async def bad():
    result = async_function()  # 得到的是 coroutine 对象，不是结果
    print(result)  # <coroutine object ...>

# ✅ 正确
async def good():
    result = await async_function()  # 得到实际结果
    print(result)
```

### ❌ 陷阱 3: 在同步函数中调用异步函数

```python
# ❌ 错误
def sync_function():
    result = await async_function()  # SyntaxError: await outside async function

# ✅ 正确方式 1: 改为异步函数
async def async_function_wrapper():
    result = await async_function()
    return result

# ✅ 正确方式 2: 使用 asyncio.run
def sync_function():
    result = asyncio.run(async_function())
    return result
```

### ❌ 陷阱 4: 并发访问共享资源

```python
# ❌ 错误：可能导致竞态条件
counter = 0

async def increment():
    global counter
    temp = counter
    await asyncio.sleep(0.01)  # 模拟延迟
    counter = temp + 1

# ✅ 正确：使用锁
import asyncio

counter = 0
lock = asyncio.Lock()

async def increment():
    global counter
    async with lock:
        temp = counter
        await asyncio.sleep(0.01)
        counter = temp + 1
```

### ❌ 陷阱 5: 在循环中串行执行异步操作

```python
# ❌ 慢：串行执行
async def slow():
    results = []
    for i in range(10):
        result = await fetch_data(i)  # 一个接一个
        results.append(result)
    return results

# ✅ 快：并发执行
async def fast():
    tasks = [fetch_data(i) for i in range(10)]
    results = await asyncio.gather(*tasks)  # 同时执行
    return results
```

---

## 最佳实践

### ✅ 1. 使用异步库

```python
# ❌ 不要用同步库
import requests  # 同步 HTTP 库
import pymysql   # 同步数据库驱动

# ✅ 使用异步库
import httpx     # 异步 HTTP 库
import asyncpg   # 异步 PostgreSQL 驱动
import aiosqlite # 异步 SQLite 驱动
```

### ✅ 2. 合理使用 asyncio.gather()

```python
# 并发执行独立任务
async def fetch_dashboard_data(user_id: int, db: AsyncSession):
    # 这些查询相互独立，可以并发执行
    user, posts, comments = await asyncio.gather(
        get_user(db, user_id),
        get_user_posts(db, user_id),
        get_user_comments(db, user_id)
    )
    return {
        "user": user,
        "posts": posts,
        "comments": comments
    }
```

### ✅ 3. 设置超时

```python
async def fetch_with_timeout():
    try:
        # 设置 5 秒超时
        result = await asyncio.wait_for(
            slow_operation(),
            timeout=5.0
        )
        return result
    except asyncio.TimeoutError:
        print("操作超时")
        return None
```

### ✅ 4. 优雅处理异常

```python
async def safe_fetch(url: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()
    except httpx.HTTPError as e:
        print(f"HTTP 错误: {e}")
        return None
    except Exception as e:
        print(f"未知错误: {e}")
        return None
```

### ✅ 5. 使用类型提示

```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

async def get_users(
    db: AsyncSession,
    limit: int = 10
) -> List[User]:
    """获取用户列表"""
    result = await db.execute(
        select(User).limit(limit)
    )
    return result.scalars().all()

async def get_user_by_id(
    db: AsyncSession,
    user_id: int
) -> Optional[User]:
    """根据 ID 获取用户"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```

---

## 实战示例

### 示例 1: 批量发送邮件

```python
import asyncio
import httpx

async def send_email(email: str, subject: str, body: str):
    """异步发送邮件"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json={
                "to": email,
                "subject": subject,
                "body": body
            }
        )
        return response.status_code == 200

async def send_bulk_emails(users: List[User]):
    """批量发送邮件"""
    tasks = []
    for user in users:
        task = send_email(
            user.email,
            "Welcome!",
            f"Hello {user.username}"
        )
        tasks.append(task)

    # 并发发送
    results = await asyncio.gather(*tasks)

    success_count = sum(results)
    print(f"成功发送 {success_count}/{len(users)} 封邮件")
```

### 示例 2: 并发查询多个 API

```python
async def fetch_user_data(user_id: int):
    """从多个 API 获取用户数据"""
    async with httpx.AsyncClient() as client:
        # 并发调用多个 API
        profile, posts, followers = await asyncio.gather(
            client.get(f"https://api1.com/users/{user_id}"),
            client.get(f"https://api2.com/users/{user_id}/posts"),
            client.get(f"https://api3.com/users/{user_id}/followers")
        )

        return {
            "profile": profile.json(),
            "posts": posts.json(),
            "followers": followers.json()
        }
```

### 示例 3: 数据库批量操作

```python
async def bulk_create_users(
    db: AsyncSession,
    users_data: List[dict]
):
    """批量创建用户"""
    users = [
        User(**data)
        for data in users_data
    ]

    # 批量添加
    db.add_all(users)

    # 提交
    await db.commit()

    # 刷新以获取生成的 ID
    for user in users:
        await db.refresh(user)

    return users
```

### 示例 4: 限流并发

```python
import asyncio
from asyncio import Semaphore

async def rate_limited_fetch(
    urls: List[str],
    max_concurrent: int = 5
):
    """限制并发数量的批量请求"""
    semaphore = Semaphore(max_concurrent)

    async def fetch_with_limit(url: str):
        async with semaphore:  # 限制并发数
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()

    tasks = [fetch_with_limit(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results

# 使用
urls = [f"https://api.example.com/item/{i}" for i in range(100)]
results = asyncio.run(rate_limited_fetch(urls, max_concurrent=10))
```

### 示例 5: 异步缓存

```python
import asyncio
from typing import Dict, Any
from datetime import datetime, timedelta

class AsyncCache:
    def __init__(self):
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any:
        """获取缓存"""
        async with self._lock:
            if key in self._cache:
                value, expire_time = self._cache[key]
                if datetime.now() < expire_time:
                    return value
                else:
                    del self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: int = 60):
        """设置缓存（ttl 单位：秒）"""
        async with self._lock:
            expire_time = datetime.now() + timedelta(seconds=ttl)
            self._cache[key] = (value, expire_time)

    async def delete(self, key: str):
        """删除缓存"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

# 使用
cache = AsyncCache()

async def get_user(user_id: int, db: AsyncSession):
    # 先查缓存
    cache_key = f"user:{user_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # 查数据库
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    # 存入缓存
    if user:
        await cache.set(cache_key, user, ttl=300)

    return user
```

---

## 性能对比

### 测试：并发获取 10 个 URL

```python
import time
import asyncio
import httpx
import requests

# 同步版本
def sync_fetch_all(urls):
    results = []
    for url in urls:
        response = requests.get(url)
        results.append(response.json())
    return results

# 异步版本
async def async_fetch_all(urls):
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]

# 测试
urls = [f"https://jsonplaceholder.typicode.com/posts/{i}" for i in range(1, 11)]

# 同步：约 5 秒（串行）
start = time.time()
sync_results = sync_fetch_all(urls)
print(f"同步耗时: {time.time() - start:.2f}秒")

# 异步：约 0.5 秒（并发）
start = time.time()
async_results = asyncio.run(async_fetch_all(urls))
print(f"异步耗时: {time.time() - start:.2f}秒")
```

**结果**：
- 同步：~5 秒
- 异步：~0.5 秒
- **性能提升：10倍！** 🚀

---

## 何时使用异步？

### ✅ 适合使用异步的场景

1. **I/O 密集型操作**
   - 网络请求（HTTP API 调用）
   - 数据库查询
   - 文件读写
   - 消息队列

2. **高并发场景**
   - Web 服务器（FastAPI, Sanic）
   - WebSocket 连接
   - 实时通信

3. **批量操作**
   - 批量发送邮件/短信
   - 爬虫（并发抓取）
   - 批量数据处理

### ❌ 不适合使用异步的场景

1. **CPU 密集型操作**
   - 图像处理
   - 视频编码
   - 数据分析
   - 机器学习训练

   **建议**：使用多进程（`multiprocessing`）

2. **简单脚本**
   - 一次性任务
   - 简单的 CRUD 操作
   - 不涉及 I/O 的计算

---

## 总结

### 核心要点

1. **async/await** 语法和 JavaScript 几乎一样
2. **asyncio.gather()** 用于并发执行多个任务
3. **await** 只能在 async 函数中使用
4. **避免在异步代码中使用阻塞操作**（如 `time.sleep`）
5. **使用异步库**（httpx, aiosqlite, asyncpg）

### 常用模式

```python
# 1. 并发执行
results = await asyncio.gather(task1(), task2(), task3())

# 2. 异步上下文管理器
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# 3. 异步迭代
async for item in async_generator():
    process(item)

# 4. 超时控制
result = await asyncio.wait_for(slow_task(), timeout=5)

# 5. 后台任务
task = asyncio.create_task(background_job())
```

### 学习建议

1. **从简单开始**：先理解 async/await
2. **对比 JavaScript**：利用你的前端经验
3. **实践为主**：多写异步代码
4. **注意陷阱**：避免阻塞操作
5. **阅读文档**：https://docs.python.org/3/library/asyncio.html

异步编程是现代 Python Web 开发的核心技能，掌握它能显著提升应用性能！🚀
