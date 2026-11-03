"""
===========================================
SSE 教学路由 (Server-Sent Events)
===========================================

作用：
  演示 FastAPI 如何用 StreamingResponse 推送服务端事件。
  浏览器只需要一个单向、长连接的「服务器 -> 客户端」通道时，
  SSE 通常比轮询更省请求，也比 WebSocket 更简单。

和本项目其它 JSON 接口的关系：
  - 普通接口继续走统一响应 {code, message, data}
  - SSE 流本身必须是 text/event-stream，不能包一层 JSON 信封
  - 因此本模块用 GET /api/v1/sse 返回教学说明（统一响应），
    真正的推送接口返回事件流

对比三种实时方案（面试常问）：

  1. 轮询 Polling
     客户端每隔 N 秒 GET 一次。实现最简单，但空转浪费，延迟取决于间隔。

  2. SSE (本模块)
     一次 HTTP GET，服务器持续 write 文本事件。
     只支持服务器 -> 浏览器；浏览器用 EventSource 自动重连。
     适合：进度条、通知、日志、股价、AI 打字输出。

  3. WebSocket
     全双工二进制/文本帧，需要协议升级。
     适合：聊天室、协同编辑、客户端也要频繁上行。

类比前端：
  - 轮询 ≈ setInterval(() => fetch('/status'), 1000)
  - SSE  ≈ new EventSource('/stream')  // 服务端一直推
  - WS   ≈ new WebSocket('/ws')        // 两边都能发
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from common.error_codes import ErrorCode
from common.exceptions import BusinessException
from common.response import success
from core.redis import get_redis
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================
# SSE 协议小抄（浏览器 EventSource 认这些字段）
# ============================================================
#
# 一条事件用空行（\n\n）分隔，字段名不区分大小写，常见写法：
#
#   id: 3                 # 事件 ID。断线重连时浏览器会带 Last-Event-ID
#   event: heartbeat      # 自定义事件名。前端 addEventListener('heartbeat', ...)
#   retry: 3000           # 断线后多久重连（毫秒）
#   data: {"tick": 3}     # 载荷。多行 data 会用 \n 拼起来
#
#   : 这是注释 / 心跳    # 冒号开头的行会被客户端忽略，常用来保活
#
# 注意：
#   - 每个 data 行不要自己再包一层 "data:" 以外的协议
#   - JSON 建议单行，避免前端还要处理多行拼接
#   - 必须用 UTF-8 文本，Content-Type 必须是 text/event-stream
#

SSE_MEDIA_TYPE = "text/event-stream"
REDIS_CHANNEL_PREFIX = "sse:channel:"
REDIS_PROBE_TIMEOUT = 0.4

# 告诉浏览器 / 中间层：不要缓存、不要把事件攒在缓冲区里
SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # 关闭 Nginx 反向代理缓冲，否则事件会「卡住」
}


# ============================================================
# 内存广播（Redis 挂了也能把 Demo 跑起来）
# ============================================================

class MemoryEventHub:
    """
    进程内发布订阅。

    为什么还要内存实现？
      Redis Pub/Sub 适合多 Worker / 多机器同步。
      教学环境和 CI 经常没有 Redis，所以默认走这里，
      Redis 活着时再「额外」转发一层。

    数据结构：
      channel 名 -> 若干个 asyncio.Queue（每个订阅者一个）
    """

    def __init__(self) -> None:
        self._channels: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, channel: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._channels.setdefault(channel, []).append(queue)
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        subscribers = self._channels.get(channel)
        if not subscribers:
            return
        if queue in subscribers:
            subscribers.remove(queue)
        if not subscribers:
            self._channels.pop(channel, None)

    async def publish(self, channel: str, payload: dict[str, Any]) -> int:
        delivered = 0
        for queue in list(self._channels.get(channel, [])):
            try:
                queue.put_nowait(payload)
                delivered += 1
            except asyncio.QueueFull:
                # 订阅者处理太慢就丢最老的一条，避免把内存撑爆
                try:
                    queue.get_nowait()
                    queue.put_nowait(payload)
                    delivered += 1
                except asyncio.QueueEmpty:
                    continue
        return delivered


event_hub = MemoryEventHub()


# ============================================================
# 请求模型
# ============================================================

class PublishMessageRequest(BaseModel):
    """往某个频道发一条消息（普通 JSON 接口，走统一响应）。"""

    message: str = Field(..., min_length=1, max_length=500, description="要广播的文本")
    extra: Optional[dict[str, Any]] = Field(default=None, description="可选的附加字段")


# ============================================================
# 协议辅助函数
# ============================================================

def format_sse(
    data: Any = None,
    *,
    event: Optional[str] = None,
    event_id: Optional[str] = None,
    retry: Optional[int] = None,
    comment: Optional[str] = None,
) -> str:
    """
    把 Python 对象编码成一条标准 SSE 文本。

    返回值必须以后面的两个换行结束，浏览器才认为「这条事件完整了」。
    """
    lines: list[str] = []

    if comment is not None:
        lines.append(f": {comment}")
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if event is not None:
        lines.append(f"event: {event}")
    if retry is not None:
        lines.append(f"retry: {retry}")

    if data is not None:
        if isinstance(data, (dict, list)):
            payload = json.dumps(data, ensure_ascii=False)
        else:
            payload = str(data)
        # 规范要求每一行都加 data: 前缀；空字符串也要写一行 data:
        for line in payload.splitlines() or [""]:
            lines.append(f"data: {line}")

    return "\n".join(lines) + "\n\n"


def sse_response(iterator: AsyncIterator[str]) -> StreamingResponse:
    """统一包一层 StreamingResponse，避免每个接口重复写 media_type / headers。"""
    return StreamingResponse(
        iterator,
        media_type=SSE_MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


def parse_last_event_id(request: Request) -> int:
    """
    读取浏览器自动带上的 Last-Event-ID。

    EventSource 断线重连时会加这个请求头，服务器据此跳过已经推过的事件。
    非法值当作 0（从头开始），不要抛 500。
    """
    raw = request.headers.get("last-event-id")
    if not raw:
        return 0
    try:
        return max(int(raw), 0)
    except ValueError:
        logger.warning("忽略非法 Last-Event-ID: %s", raw)
        return 0


async def client_disconnected(request: Request) -> bool:
    """
    客户端关掉标签页 / curl 被 Ctrl+C 后，生成器还可能继续跑。

    Starlette 提供 request.is_disconnected()。
    另外生成器被取消时会抛 asyncio.CancelledError，外层也要接住。
    """
    return await request.is_disconnected()


async def redis_is_available() -> bool:
    """探测 Redis。失败或超时都算不可用，Demo 继续用内存广播。"""
    try:
        client = await get_redis()
        await asyncio.wait_for(client.ping(), timeout=REDIS_PROBE_TIMEOUT)
        return True
    except Exception as exc:
        logger.debug("SSE 探测 Redis 失败，将使用内存回退: %s", exc)
        return False


async def publish_to_redis(channel: str, payload: dict[str, Any]) -> bool:
    """能连上 Redis 就多广播一次，方便以后扩成多进程。"""
    try:
        client = await get_redis()
        await asyncio.wait_for(client.ping(), timeout=REDIS_PROBE_TIMEOUT)
        await client.publish(
            f"{REDIS_CHANNEL_PREFIX}{channel}",
            json.dumps(payload, ensure_ascii=False),
        )
        return True
    except Exception as exc:
        logger.debug("SSE Redis 发布失败（可忽略）: %s", exc)
        return False


async def forward_redis_messages(
    channel: str,
    queue: asyncio.Queue,
    stop_event: asyncio.Event,
) -> None:
    """
    后台任务：把 Redis 频道里的消息转进当前订阅者的 Queue。

    Redis 不在就立刻退出，不影响内存 Demo。
    """
    pubsub = None
    try:
        client = await get_redis()
        await asyncio.wait_for(client.ping(), timeout=REDIS_PROBE_TIMEOUT)
        pubsub = client.pubsub()
        await pubsub.subscribe(f"{REDIS_CHANNEL_PREFIX}{channel}")
        logger.info("SSE 已订阅 Redis 频道 sse:channel:%s", channel)

        while not stop_event.is_set():
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=0.2,
            )
            if not message or message.get("type") != "message":
                await asyncio.sleep(0.05)
                continue

            raw = message.get("data")
            try:
                payload = json.loads(raw) if isinstance(raw, str) else {"message": raw}
            except json.JSONDecodeError:
                payload = {"message": raw}
            if not isinstance(payload, dict):
                payload = {"message": payload}
            payload.setdefault("source", "redis")

            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("SSE 频道 %s 的内存队列已满，丢弃一条 Redis 消息", channel)
    except Exception as exc:
        logger.debug("SSE Redis 订阅结束/不可用: %s", exc)
    finally:
        if pubsub is not None:
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
            except Exception:
                pass


# ============================================================
# 教学说明（统一 JSON 响应）
# ============================================================

@router.get("/", summary="SSE 模块说明")
async def sse_overview():
    """
    返回本模块有哪些演示接口。

    这是普通 JSON，方便在 Swagger 里先看一眼；
    下面几个 GET 才是真正的 text/event-stream。
    """
    redis_enabled = await redis_is_available()
    return success(
        message="SSE 教学接口已就绪",
        data={
            "protocol": "Server-Sent Events",
            "content_type": SSE_MEDIA_TYPE,
            "redis_enabled": redis_enabled,
            "compare": {
                "polling": "客户端反复请求，实现简单，空转多",
                "sse": "单向长连接，浏览器 EventSource 自动重连",
                "websocket": "双向连接，适合聊天/协同，实现更重",
            },
            "fields": ["event", "data", "id", "retry", ":comment"],
            "endpoints": {
                "heartbeat": "GET /api/v1/sse/heartbeat",
                "progress": "GET /api/v1/sse/progress",
                "subscribe": "GET /api/v1/sse/channel/{name}",
                "publish": "POST /api/v1/sse/channel/{name}",
            },
        },
    )


# ============================================================
# Demo 1：定时心跳 / 计数器
# ============================================================

@router.get("/heartbeat", summary="SSE 心跳计数流")
async def sse_heartbeat(
    request: Request,
    ticks: int = Query(5, ge=1, le=30, description="推送多少次心跳"),
    interval_ms: int = Query(200, ge=10, le=5000, description="两次事件间隔（毫秒）"),
):
    """
    最简单的 SSE：每隔一段时间推一条计数。

    教学要点：
      1. 返回 StreamingResponse，media_type=text/event-stream
      2. 第一条事件带 retry，告诉浏览器断线后多久重连
      3. 每条事件带 id，配合 Last-Event-ID 可以续传
      4. 循环里检查 request.is_disconnected()，避免客户端走了还空转

    curl 示例:
        curl -N http://127.0.0.1:8080/api/v1/sse/heartbeat?ticks=3&interval_ms=200
    """

    last_id = parse_last_event_id(request)
    logger.info(
        "SSE heartbeat 开始 | ticks=%s interval_ms=%s last_id=%s",
        ticks,
        interval_ms,
        last_id,
    )

    async def generate() -> AsyncIterator[str]:
        try:
            # 注释行：代理/防火墙有时靠它判断连接还活着
            yield format_sse(comment="heartbeat stream opened")

            if last_id <= 0:
                yield format_sse(
                    {"message": "心跳流已连接", "total": ticks},
                    event="ready",
                    event_id="0",
                    retry=3000,
                )

            start = min(last_id, ticks)
            for tick in range(start + 1, ticks + 1):
                if await client_disconnected(request):
                    logger.info("SSE heartbeat 客户端断开，停在 tick=%s", tick)
                    return

                yield format_sse(
                    {
                        "tick": tick,
                        "total": ticks,
                        "ts": int(time.time()),
                    },
                    event="heartbeat",
                    event_id=str(tick),
                )
                await asyncio.sleep(interval_ms / 1000)

            if not await client_disconnected(request):
                yield format_sse(
                    {"tick": ticks, "status": "completed"},
                    event="done",
                    event_id=str(ticks),
                )
        except asyncio.CancelledError:
            logger.info("SSE heartbeat 被取消（客户端断开或服务关闭）")
            raise
        finally:
            logger.info("SSE heartbeat 结束")

    return sse_response(generate())


# ============================================================
# Demo 2：假进度任务（不依赖 Redis / Celery）
# ============================================================

PROGRESS_STAGES = (
    "queued",
    "preparing",
    "running",
    "finalizing",
    "completed",
)


@router.get("/progress", summary="SSE 假进度任务流")
async def sse_progress(
    request: Request,
    steps: int = Query(5, ge=2, le=20, description="进度分成几步"),
    interval_ms: int = Query(80, ge=10, le=3000, description="每步间隔（毫秒）"),
):
    """
    稍微丰富一点的流：模拟「后台任务进度」。

    真实项目里进度通常来自 Celery / 数据库；
    这里用纯内存循环，保证没有 Redis / Worker 也能看懂 SSE。

    事件序列：
      ready -> progress * N -> done
    """
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    logger.info("SSE progress 开始 | job_id=%s steps=%s", job_id, steps)

    async def generate() -> AsyncIterator[str]:
        try:
            yield format_sse(
                {"job_id": job_id, "steps": steps},
                event="ready",
                event_id="0",
                retry=2000,
            )

            for step in range(1, steps + 1):
                if await client_disconnected(request):
                    logger.info("SSE progress 客户端断开 | job_id=%s step=%s", job_id, step)
                    return

                percent = int(step / steps * 100)
                stage_index = min(
                    int((step - 1) / steps * (len(PROGRESS_STAGES) - 1)),
                    len(PROGRESS_STAGES) - 1,
                )
                if step == steps:
                    stage = "completed"
                else:
                    stage = PROGRESS_STAGES[stage_index]

                yield format_sse(
                    {
                        "job_id": job_id,
                        "step": step,
                        "total": steps,
                        "percent": percent,
                        "stage": stage,
                        "message": f"任务 {job_id} 进度 {percent}%",
                    },
                    event="progress",
                    event_id=str(step),
                )
                await asyncio.sleep(interval_ms / 1000)

            if not await client_disconnected(request):
                yield format_sse(
                    {
                        "job_id": job_id,
                        "percent": 100,
                        "stage": "completed",
                        "status": "success",
                    },
                    event="done",
                    event_id=str(steps),
                )
        except asyncio.CancelledError:
            logger.info("SSE progress 被取消 | job_id=%s", job_id)
            raise
        finally:
            logger.info("SSE progress 结束 | job_id=%s", job_id)

    return sse_response(generate())


# ============================================================
# Demo 3：频道订阅（内存优先，Redis 可选）
# ============================================================

@router.get("/channel/{name}", summary="订阅 SSE 频道")
async def sse_subscribe_channel(
    name: str,
    request: Request,
    timeout_ms: int = Query(
        8000,
        ge=50,
        le=60000,
        description="最多挂起多久，超时后发 done 并结束（方便测试）",
    ),
    demo: bool = Query(False, description="true 时自动推 2 条演示消息"),
):
    """
    订阅一个命名频道。

    默认行为：
      1. 立刻推 ready
      2. 等待 POST /channel/{name} 发来的消息
      3. 超时或客户端断开后结束

    Redis：
      连得上就同时听 Redis Pub/Sub，多进程也能收到；
      连不上只走进程内 MemoryEventHub，Demo 照样能跑。
    """
    channel = name.strip()
    if not channel or len(channel) > 32 or not channel.replace("-", "").replace("_", "").isalnum():
        raise BusinessException(
            ErrorCode.PARAMS_INVALID,
            message="频道名仅允许字母、数字、下划线和短横线，最长 32 位",
        )

    redis_enabled = await redis_is_available()
    logger.info(
        "SSE 订阅频道 %s | timeout_ms=%s demo=%s redis=%s",
        channel,
        timeout_ms,
        demo,
        redis_enabled,
    )

    async def generate() -> AsyncIterator[str]:
        queue = event_hub.subscribe(channel)
        stop_event = asyncio.Event()
        redis_task: Optional[asyncio.Task] = None
        event_seq = 0

        try:
            yield format_sse(comment=f"subscribed {channel}")
            yield format_sse(
                {
                    "channel": channel,
                    "redis_enabled": redis_enabled,
                    "message": "已订阅，等待消息",
                },
                event="ready",
                event_id="0",
                retry=3000,
            )

            if redis_enabled:
                redis_task = asyncio.create_task(
                    forward_redis_messages(channel, queue, stop_event)
                )

            if demo:
                for index, text in enumerate(("demo-1", "demo-2"), start=1):
                    if await client_disconnected(request):
                        return
                    event_seq = index
                    yield format_sse(
                        {
                            "channel": channel,
                            "message": text,
                            "source": "demo",
                        },
                        event="message",
                        event_id=str(event_seq),
                    )
                    await asyncio.sleep(0.01)

            deadline = time.monotonic() + timeout_ms / 1000
            while time.monotonic() < deadline:
                if await client_disconnected(request):
                    logger.info("SSE 频道 %s 客户端断开", channel)
                    return

                remaining = deadline - time.monotonic()
                try:
                    payload = await asyncio.wait_for(
                        queue.get(),
                        timeout=min(0.15, max(remaining, 0.01)),
                    )
                except asyncio.TimeoutError:
                    # 短间隔空转：既能响应断开，也能给代理一个「还活着」的机会
                    continue

                event_seq += 1
                if not isinstance(payload, dict):
                    payload = {"message": payload}
                payload.setdefault("channel", channel)
                payload.setdefault("source", payload.get("source") or "memory")
                yield format_sse(payload, event="message", event_id=str(event_seq))

            if not await client_disconnected(request):
                yield format_sse(
                    {"channel": channel, "reason": "timeout"},
                    event="done",
                    event_id=str(event_seq),
                )
        except asyncio.CancelledError:
            logger.info("SSE 频道 %s 订阅被取消", channel)
            raise
        finally:
            stop_event.set()
            if redis_task is not None:
                redis_task.cancel()
                try:
                    await redis_task
                except asyncio.CancelledError:
                    pass
            event_hub.unsubscribe(channel, queue)
            logger.info("SSE 频道 %s 订阅结束", channel)

    return sse_response(generate())


@router.post("/channel/{name}", summary="往 SSE 频道发布消息")
async def sse_publish_channel(name: str, body: PublishMessageRequest):
    """
    发布一条消息给当前所有订阅者。

    这是普通 JSON 接口（统一响应），不是 SSE。
    浏览器 EventSource 只能 GET，所以上行消息必须另开一个 POST。
    """
    channel = name.strip()
    if not channel or len(channel) > 32 or not channel.replace("-", "").replace("_", "").isalnum():
        raise BusinessException(
            ErrorCode.PARAMS_INVALID,
            message="频道名仅允许字母、数字、下划线和短横线，最长 32 位",
        )

    payload = {
        "channel": channel,
        "message": body.message,
        "source": "api",
        "ts": int(time.time()),
    }
    if body.extra:
        payload["extra"] = body.extra

    delivered = await event_hub.publish(channel, payload)
    redis_published = await publish_to_redis(channel, payload)

    logger.info(
        "SSE 发布频道 %s | memory=%s redis=%s",
        channel,
        delivered,
        redis_published,
    )
    return success(
        message="消息已发布",
        data={
            "channel": channel,
            "delivered": delivered,
            "redis_published": redis_published,
        },
    )


# ============================================================
# 学习笔记
# ============================================================
"""
1. 【为什么不用 success() 包 SSE】
   EventSource 解析的是 text/event-stream，不是 application/json。
   把 {code, message, data} 整包当 HTTP body 返回，浏览器不会触发 message 事件。

2. 【StreamingResponse】
   传入异步生成器，每 yield 一次就往连接上写一块文本。
   不要在生成器里先把所有事件攒成 list 再返回，那就不是流了。

3. 【断开连接】
   - 循环里 await request.is_disconnected()
   - except asyncio.CancelledError: 记日志后 raise
   - finally: 退订 / 关 Redis pubsub，避免泄漏

4. 【Last-Event-ID】
   给每条事件写 id。客户端重连时带上最后收到的 id，
   服务端从 id+1 续推，进度条才不会倒回去。

5. 【Nginx】
   必须 proxy_buffering off; 并拉长 proxy_read_timeout。
   详见 nginx/conf.d/default.conf 和 docs/sse-guide.md。

6. 【鉴权提示】
   浏览器原生 EventSource 不能自定义 Authorization 头，
   生产环境常用 Cookie 或 ?token= 查询参数。本 Demo 故意不鉴权，降低门槛。
"""
