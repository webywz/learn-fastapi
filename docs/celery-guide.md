# Celery 完整学习指南

## 目录
1. [什么是 Celery](#什么是-celery)
2. [为什么需要 Celery](#为什么需要-celery)
3. [Celery 核心概念](#celery-核心概念)
4. [项目配置](#项目配置)
5. [创建任务](#创建任务)
6. [调用任务](#调用任务)
7. [任务状态追踪](#任务状态追踪)
8. [定时任务](#定时任务)
9. [启动 Celery](#启动-celery)
10. [监控工具 Flower](#监控工具-flower)
11. [实战示例](#实战示例)
12. [最佳实践](#最佳实践)
13. [常见问题](#常见问题)

---

## 什么是 Celery？

**Celery** 是一个分布式任务队列，用于处理**异步任务**和**定时任务**。

### 核心功能

1. **异步任务** - 将耗时操作放到后台执行
2. **定时任务** - 定期执行任务（类似 cron）
3. **任务重试** - 失败自动重试
4. **分布式** - 多台服务器并行处理

### 类比前端

```javascript
// JavaScript 异步操作
setTimeout(() => {
    console.log('延迟执行');
}, 1000);

// 或者 Promise
fetch('/api/data')
    .then(response => response.json())
    .then(data => console.log(data));
```

```python
# Celery 异步任务（类似，但更强大）
@shared_task
def process_data():
    # 耗时操作
    return result

# 异步调用
task = process_data.delay()  # 立即返回
```

**区别**：
- JavaScript 异步：单线程，适合浏览器
- Celery：多进程/多机器，适合服务器端大任务

---

## 为什么需要 Celery？

### 场景 1: API 响应太慢 🐌

```python
# ❌ 没有 Celery（同步，慢）
@app.post("/send-email")
async def send_email_api(email: str):
    # 发送邮件需要 2-3 秒
    send_email(email, "Welcome", "Hello!")  # 阻塞 2-3 秒
    return {"message": "Email sent"}  # 用户等了 3 秒才收到响应
```

```python
# ✅ 使用 Celery（异步，快）
@app.post("/send-email")
async def send_email_api(email: str):
    # 提交任务到队列
    task = send_email.delay(email, "Welcome", "Hello!")  # 立即返回
    return {"task_id": task.id}  # 用户立即收到响应（< 100ms）
```

**提升**：从 3 秒变成 0.1 秒！🚀

### 场景 2: 定时任务

```python
# 每天凌晨 2 点清理过期数据
@shared_task
def cleanup_expired_data():
    # 删除 7 天前的临时文件
    pass

# 定时配置
beat_schedule = {
    'cleanup-daily': {
        'task': 'tasks.cleanup_expired_data',
        'schedule': crontab(hour=2, minute=0),
    }
}
```

### 场景 3: 批量处理

```python
# 给 10000 个用户发送通知
@shared_task
def send_newsletter(user_ids):
    for user_id in user_ids:
        send_notification(user_id)

# 异步执行（不阻塞）
send_newsletter.delay(user_ids=[1, 2, 3, ...])
```

---

## Celery 核心概念

### 架构图

```
┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
│ FastAPI │ ───> │ Broker  │ ───> │ Worker  │ ───> │ Backend │
│         │      │ (Redis) │      │ (进程)  │      │ (Redis) │
└─────────┘      └─────────┘      └─────────┘      └─────────┘
   提交任务         任务队列          执行任务          存储结果
```

### 核心组件

#### 1. Celery App（应用实例）
```python
from celery import Celery

celery_app = Celery(
    'my_app',
    broker='redis://localhost:6379/0',  # 消息代理
    backend='redis://localhost:6379/0'  # 结果存储
)
```

#### 2. Broker（消息代理）
- **作用**：存储待执行的任务
- **常用**：Redis、RabbitMQ
- **类比**：待办事项列表

#### 3. Worker（工作进程）
- **作用**：执行任务的进程
- **启动**：`celery -A core.celery_app worker`
- **类比**：员工（从待办列表中取任务执行）

#### 4. Backend（结果存储）
- **作用**：存储任务执行结果
- **常用**：Redis、数据库
- **类比**：完成记录

#### 5. Beat（定时调度器）
- **作用**：触发定时任务
- **启动**：`celery -A core.celery_app beat`
- **类比**：闹钟（到点了就把任务放入队列）

---

## 项目配置

### 1. 安装依赖

```bash
pip install celery==5.4.0 redis==7.1.0 flower==2.0.1
```

### 2. 配置（`core/celery_app.py`）

```python
from celery import Celery
from core.config import settings

celery_app = Celery(
    "fastapi_tasks",
    broker=settings.CELERY_BROKER,
    backend=settings.CELERY_BACKEND,
    include=[
        "tasks.email_tasks",
        "tasks.report_tasks",
        "tasks.cleanup_tasks",
    ]
)

# 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
)
```

### 3. 环境变量（`.env`）

```env
# Redis 配置（Broker 和 Backend 都用 Redis）
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_PASSWORD="root"
REDIS_DB=0
```

---

## 创建任务

### 基本任务

```python
from celery import shared_task

@shared_task
def add(x, y):
    """简单的加法任务"""
    return x + y

# 调用
result = add.delay(2, 3)  # 异步执行
print(result.get())  # 获取结果: 5
```

### 带重试的任务

```python
@shared_task(
    bind=True,
    max_retries=3,  # 最多重试 3 次
    default_retry_delay=60  # 重试间隔 60 秒
)
def send_email(self, to: str, subject: str, body: str):
    try:
        # 发送邮件
        smtp.send(to, subject, body)
    except Exception as exc:
        # 失败后重试
        raise self.retry(exc=exc)
```

### 带进度的任务

```python
@shared_task(bind=True)
def process_data(self, items):
    total = len(items)

    for i, item in enumerate(items):
        # 更新进度
        self.update_state(
            state='PROGRESS',
            meta={'current': i + 1, 'total': total}
        )

        # 处理数据
        process_item(item)

    return {'status': 'complete', 'total': total}
```

---

## 调用任务

### 方式 1: `.delay()` - 最简单

```python
# 异步调用
task = send_email.delay("user@example.com", "Hi", "Hello")

# 返回任务对象
print(task.id)  # 任务 ID
print(task.state)  # 任务状态
```

### 方式 2: `.apply_async()` - 更灵活

```python
# 延迟 60 秒后执行
task = send_email.apply_async(
    args=["user@example.com", "Hi", "Hello"],
    countdown=60  # 延迟 60 秒
)

# 指定时间执行
from datetime import datetime, timedelta

eta = datetime.now() + timedelta(hours=1)
task = send_email.apply_async(
    args=["user@example.com", "Hi", "Hello"],
    eta=eta  # 1 小时后执行
)

# 设置过期时间
task = send_email.apply_async(
    args=["user@example.com", "Hi", "Hello"],
    expires=3600  # 1 小时后过期（不再执行）
)

# 指定队列
task = send_email.apply_async(
    args=["user@example.com", "Hi", "Hello"],
    queue="email"  # 发送到 email 队列
)
```

### 方式 3: 同步调用（不推荐）

```python
# 同步调用（阻塞）
result = send_email("user@example.com", "Hi", "Hello")
```

---

## 任务状态追踪

### 任务状态

- `PENDING` - 等待执行
- `STARTED` - 正在执行
- `PROGRESS` - 执行中（自定义状态）
- `SUCCESS` - 执行成功
- `FAILURE` - 执行失败
- `RETRY` - 重试中
- `REVOKED` - 已取消

### 获取任务状态

```python
from core.celery_app import celery_app

task_id = "abc-123-def"
task_result = celery_app.AsyncResult(task_id)

print(task_result.state)  # 状态
print(task_result.ready())  # 是否完成
print(task_result.successful())  # 是否成功
print(task_result.failed())  # 是否失败

# 获取结果（阻塞）
if task_result.successful():
    result = task_result.result
    print(result)

# 非阻塞检查
if task_result.ready():
    result = task_result.result
```

### API 中查询状态

```python
@app.get("/tasks/status/{task_id}")
async def get_task_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)

    if task_result.state == 'PENDING':
        response = {"status": "pending", "message": "任务等待中"}

    elif task_result.state == 'PROGRESS':
        response = {
            "status": "in_progress",
            "progress": task_result.info  # 进度信息
        }

    elif task_result.state == 'SUCCESS':
        response = {
            "status": "success",
            "result": task_result.result
        }

    elif task_result.state == 'FAILURE':
        response = {
            "status": "failure",
            "error": str(task_result.info)
        }

    return response
```

---

## 定时任务

### Crontab 语法

```python
from celery.schedules import crontab

# 每天 2:00
crontab(hour=2, minute=0)

# 每周一 0:00
crontab(hour=0, minute=0, day_of_week=1)

# 每 15 分钟
crontab(minute="*/15")

# 每小时
crontab(minute=0)

# 每天 9:00-17:00 之间，每小时执行
crontab(hour="9-17", minute=0)
```

### 配置定时任务

```python
celery_app.conf.beat_schedule = {
    # 每天凌晨 2 点清理
    'cleanup-expired-data': {
        'task': 'tasks.cleanup_tasks.cleanup_expired_data',
        'schedule': crontab(hour=2, minute=0),
    },

    # 每小时统计
    'generate-hourly-report': {
        'task': 'tasks.report_tasks.generate_hourly_report',
        'schedule': crontab(minute=0),
    },

    # 每 10 分钟
    'health-check': {
        'task': 'tasks.cleanup_tasks.health_check',
        'schedule': 600.0,  # 秒
    },
}
```

---

## 启动 Celery

### 1. 启动 Worker

```bash
# Windows
celery -A core.celery_app worker --loglevel=info --pool=solo

# Linux/Mac
celery -A core.celery_app worker --loglevel=info
```

**参数说明**：
- `-A core.celery_app` - Celery 应用位置
- `worker` - 启动 Worker
- `--loglevel=info` - 日志级别
- `--pool=solo` - Windows 需要（单进程模式）

### 2. 启动 Beat（定时任务）

```bash
celery -A core.celery_app beat --loglevel=info
```

### 3. 同时启动 Worker 和 Beat

```bash
# Linux/Mac
celery -A core.celery_app worker --beat --loglevel=info

# Windows (需要两个终端)
# 终端 1
celery -A core.celery_app worker --loglevel=info --pool=solo

# 终端 2
celery -A core.celery_app beat --loglevel=info
```

### 4. 指定队列

```bash
# 只处理 email 队列
celery -A core.celery_app worker -Q email --loglevel=info

# 处理多个队列
celery -A core.celery_app worker -Q email,report --loglevel=info
```

### 5. 多 Worker

```bash
# 启动 4 个 Worker 进程
celery -A core.celery_app worker --concurrency=4 --loglevel=info
```

---

## 监控工具 Flower

**Flower** 是 Celery 的 Web 监控工具。

### 1. 启动 Flower

```bash
celery -A core.celery_app flower
```

访问：http://localhost:5555

### 2. 功能

- ✅ 查看所有 Worker
- ✅ 查看任务列表
- ✅ 查看任务详情
- ✅ 实时监控
- ✅ 图表统计

### 3. 截图

```
任务列表：
┌────────────┬─────────┬──────────┬──────────┐
│ Task ID    │ Name    │ State    │ Runtime  │
├────────────┼─────────┼──────────┼──────────┤
│ abc-123    │ send_   │ SUCCESS  │ 2.5s     │
│            │ email   │          │          │
├────────────┼─────────┼──────────┼──────────┤
│ def-456    │ export_ │ PROGRESS │ 15.2s    │
│            │ users   │          │          │
└────────────┴─────────┴──────────┴──────────┘
```

---

## 实战示例

### 示例 1: 用户注册发送欢迎邮件

```python
# 任务定义 (tasks/email_tasks.py)
@shared_task
def send_welcome_email(user_id: int, email: str):
    send_email(email, "Welcome", "Thank you for joining!")
    return {"user_id": user_id, "status": "sent"}

# API 调用
@app.post("/register")
async def register(username: str, email: str):
    # 1. 创建用户
    user = create_user(username, email)

    # 2. 异步发送欢迎邮件
    send_welcome_email.delay(user.id, user.email)

    # 3. 立即返回
    return {"message": "注册成功，欢迎邮件将发送到您的邮箱"}
```

### 示例 2: 导出数据

```python
# 任务定义
@shared_task(bind=True)
def export_users_csv(self, user_id: int):
    # 1. 查询数据
    users = get_all_users()

    # 2. 生成 CSV
    csv_file = generate_csv(users)

    # 3. 上传到 OSS
    url = upload_to_oss(csv_file)

    # 4. 发送下载链接
    send_email(user_id, "导出完成", f"下载链接: {url}")

    return {"url": url}

# API 调用
@app.post("/export-users")
async def export_users(user_id: int):
    task = export_users_csv.delay(user_id)

    return {
        "task_id": task.id,
        "message": "导出任务已提交，完成后将发送邮件通知"
    }
```

### 示例 3: 定时统计

```python
# 任务定义
@shared_task
def generate_daily_stats():
    today = datetime.now().date()

    # 统计各项指标
    stats = {
        "new_users": count_new_users(today),
        "orders": count_orders(today),
        "revenue": calculate_revenue(today),
    }

    # 存入数据库
    save_stats(stats)

    # 发送日报给管理员
    send_email("admin@example.com", "每日统计", format_stats(stats))

# 定时配置
beat_schedule = {
    'daily-stats': {
        'task': 'tasks.report_tasks.generate_daily_stats',
        'schedule': crontab(hour=1, minute=0),  # 每天 1:00
    }
}
```

---

## 最佳实践

### ✅ 1. 任务要幂等

```python
# ✅ 幂等任务（多次执行结果一样）
@shared_task
def update_user_status(user_id: int, status: str):
    user = get_user(user_id)
    user.status = status
    user.save()

# ❌ 非幂等任务（多次执行结果不同）
@shared_task
def increment_counter(user_id: int):
    user = get_user(user_id)
    user.counter += 1  # 重复执行会导致错误
    user.save()
```

### ✅ 2. 设置超时

```python
@shared_task(time_limit=3600)  # 1 小时超时
def long_running_task():
    # 长时间任务
    pass
```

### ✅ 3. 失败重试

```python
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def unreliable_task(self):
    try:
        # 可能失败的操作
        call_external_api()
    except Exception as exc:
        raise self.retry(exc=exc)
```

### ✅ 4. 分批处理

```python
@shared_task
def send_bulk_notifications(user_ids):
    # 每批 100 个
    batch_size = 100

    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        for user_id in batch:
            send_notification(user_id)
```

### ✅ 5. 使用链式任务

```python
from celery import chain

# 任务链：任务 1 → 任务 2 → 任务 3
workflow = chain(
    task1.s(arg1),
    task2.s(),
    task3.s()
)

workflow.apply_async()
```

### ✅ 6. 记录详细日志

```python
@shared_task
def process_payment(order_id: int):
    logger.info(f"开始处理订单: {order_id}")

    try:
        result = charge_payment(order_id)
        logger.info(f"支付成功: {order_id}")
        return result
    except Exception as e:
        logger.error(f"支付失败: {order_id}, 错误: {e}")
        raise
```

---

## 常见问题

### Q1: Windows 下 Worker 启动失败

**问题**：
```
ValueError: not enough values to unpack
```

**解决**：使用 `--pool=solo`
```bash
celery -A core.celery_app worker --pool=solo --loglevel=info
```

### Q2: 任务卡住不执行

**原因**：
- Worker 没启动
- Redis 连接失败
- 任务名称不匹配

**检查**：
```bash
# 检查 Worker 是否运行
ps aux | grep celery

# 检查 Redis 是否运行
redis-cli ping

# 检查任务是否注册
celery -A core.celery_app inspect registered
```

### Q3: 任务结果丢失

**原因**：结果过期或未配置 Backend

**解决**：
```python
# 设置结果过期时间
celery_app.conf.result_expires = 3600  # 1 小时

# 确保配置了 Backend
celery_app = Celery(
    'app',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'  # 必须配置
)
```

### Q4: 任务执行太慢

**优化**：
1. 增加 Worker 数量
2. 使用多队列
3. 优化任务代码
4. 分批处理

```bash
# 启动多个 Worker
celery -A core.celery_app worker --concurrency=8
```

### Q5: 定时任务不执行

**原因**：Beat 没启动

**解决**：
```bash
# 启动 Beat
celery -A core.celery_app beat --loglevel=info
```

---

## 总结

### 核心要点

1. **Celery 是什么？**
   - 分布式任务队列
   - 处理异步和定时任务

2. **核心组件**
   - Broker: 存储任务队列（Redis）
   - Worker: 执行任务
   - Beat: 定时调度
   - Backend: 存储结果

3. **使用场景**
   - 发送邮件
   - 生成报表
   - 数据导入/导出
   - 定时统计
   - 图片处理

4. **启动命令**
   ```bash
   # Worker
   celery -A core.celery_app worker --loglevel=info

   # Beat
   celery -A core.celery_app beat --loglevel=info

   # Flower
   celery -A core.celery_app flower
   ```

5. **任务调用**
   ```python
   # 异步
   task = my_task.delay(arg1, arg2)

   # 延迟执行
   task = my_task.apply_async(args=[arg1, arg2], countdown=60)

   # 查询状态
   result = celery_app.AsyncResult(task_id)
   print(result.state)
   ```

### 快速开始

```python
# 1. 定义任务
@shared_task
def add(x, y):
    return x + y

# 2. 调用任务
task = add.delay(2, 3)

# 3. 获取结果
print(task.get())  # 5

# 4. 启动 Worker
# celery -A core.celery_app worker --loglevel=info
```

Celery 让你的应用更快、更稳定、更可扩展！🚀
