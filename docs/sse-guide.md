# Server-Sent Events (SSE) 学习指南

> 中文讲解为主，关键术语保留中英对照，方便对照官方文档和面试表达。

配套代码：`api/v1/sse.py`  
配套测试：`tests/test_api_sse.py`

---

## 1. 什么是 SSE？

**Server-Sent Events（服务端推送事件）** 是浏览器原生支持的一种 **HTTP 长连接**：客户端发起一次 GET，服务器持续写入文本事件。

| 中文 | English | 一句话 |
|------|---------|--------|
| 服务端推送事件 | Server-Sent Events | 服务器单向推文本事件 |
| 事件流 | `text/event-stream` | SSE 的 Content-Type |
| 事件源 | `EventSource` | 浏览器客户端 API |
| 流式响应 | `StreamingResponse` | FastAPI / Starlette 的写法 |

适合：任务进度、站内通知、日志尾随、AI 逐 token 输出。  
不适合：客户端也要高频上行（请用 WebSocket）。

---

## 2. SSE vs WebSocket vs 轮询

| | 轮询 Polling | SSE | WebSocket |
|--|-------------|-----|-----------|
| 方向 | 请求-响应 | 服务器 → 客户端 | 双向 |
| 协议 | 普通 HTTP | 普通 HTTP GET | `ws://` 升级 |
| 浏览器 API | `fetch` / `axios` | `EventSource` | `WebSocket` |
| 自动重连 | 自己写 | 浏览器自带 | 自己写 |
| 代理友好 | 很好 | 较好（需关缓冲） | 要单独配 Upgrade |
| 复杂度 | 最低 | 低 | 较高 |

记忆口诀：

- **只要服务器说话**：先看 SSE
- **两边都要说话**：WebSocket
- **偶尔查一下就行**：轮询

---

## 3. 事件字段

一条事件以空行 `\n\n` 结束：

```text
id: 3
event: heartbeat
retry: 3000
data: {"tick": 3, "total": 5}

```

| 字段 | 含义 |
|------|------|
| `event` | 自定义事件名。前端 `addEventListener('heartbeat', ...)` |
| `data` | 载荷。多行 `data:` 会用 `\n` 拼起来；本项目用单行 JSON |
| `id` | 事件 ID。重连时浏览器自动带 `Last-Event-ID` |
| `retry` | 断线后多久重连（毫秒） |
| `: comment` | 注释，客户端忽略，常用来保活 |

本项目的 JSON 业务接口仍是 `{code, message, data}`。  
**SSE 流本身不能再包一层统一信封**，否则 `EventSource` 解析不到事件。

---

## 4. FastAPI 怎么写

核心就三步：

1. 异步生成器里 `yield` 文本块
2. 用 `StreamingResponse(..., media_type="text/event-stream")`
3. 加上 `Cache-Control: no-cache` 和 `X-Accel-Buffering: no`

```python
from fastapi.responses import StreamingResponse

async def generate():
    yield "event: ready\ndata: {\"ok\": true}\n\n"
    yield "event: done\ndata: {\"status\": \"completed\"}\n\n"

return StreamingResponse(generate(), media_type="text/event-stream")
```

完整封装见 `format_sse()` / `sse_response()`。

### 客户端断开

标签页关了，生成器可能还在 `sleep`。必须处理：

- 循环里 `await request.is_disconnected()`
- `except asyncio.CancelledError` 后重新抛出
- `finally` 里退订、关掉 Redis Pub/Sub

---

## 5. 本仓库演示接口

前缀：`/api/v1/sse`

| 方法 | 路径 | 类型 | 说明 |
|------|------|------|------|
| GET | `/api/v1/sse/` | JSON 统一响应 | 模块说明、对比表、Redis 是否可用 |
| GET | `/api/v1/sse/heartbeat` | SSE | 定时计数 / 心跳，支持 `Last-Event-ID` |
| GET | `/api/v1/sse/progress` | SSE | 假进度任务（不依赖 Celery / Redis） |
| GET | `/api/v1/sse/channel/{name}` | SSE | 订阅频道；Redis 可选，挂了走内存 |
| POST | `/api/v1/sse/channel/{name}` | JSON 统一响应 | 往频道发一条消息 |

查询参数（测试里都会把间隔压到 10ms，避免慢测试）：

```text
GET /api/v1/sse/heartbeat?ticks=5&interval_ms=200
GET /api/v1/sse/progress?steps=5&interval_ms=80
GET /api/v1/sse/channel/demo?timeout_ms=8000&demo=true
```

Redis 活着时，发布会同时 `PUBLISH sse:channel:{name}`，多进程也能收到。  
Redis 挂了：内存 `MemoryEventHub` 仍能在本进程演示，CI 不依赖 Redis。

---

## 6. 前端怎么接

```javascript
const source = new EventSource('/api/v1/sse/heartbeat?ticks=10&interval_ms=1000');

source.addEventListener('ready', (event) => {
  console.log('ready', JSON.parse(event.data));
});

source.addEventListener('heartbeat', (event) => {
  console.log('tick', JSON.parse(event.data), 'id=', event.lastEventId);
});

source.addEventListener('done', (event) => {
  console.log('done', JSON.parse(event.data));
  source.close();
});

source.onerror = (err) => {
  console.error('sse error', err);
};
```

原生 `EventSource` **不能自定义 `Authorization` 头**。  
生产环境常见做法：Cookie 会话，或 `?token=`（注意日志和 Referer 泄露）。

`curl` 调试请加 `-N`（关闭缓冲）：

```bash
curl -N "http://127.0.0.1:8080/api/v1/sse/heartbeat?ticks=3&interval_ms=200"
```

---

## 7. Nginx 注意点

SSE 经过反向代理时，**一定要关掉响应缓冲**，否则事件会攒在 Nginx 里，进度条看起来「卡住」。

本仓库已在 `nginx/conf.d/default.conf` 增加 `/api/v1/sse/`：

- `proxy_buffering off;`
- `proxy_cache off;`
- `proxy_read_timeout` 拉长（长连接）
- `X-Accel-Buffering: no`（应用层也加了）

---

## 8. 怎么测

```bash
pytest tests/test_api_sse.py
```

测试用 httpx `AsyncClient.stream()`，断言：

- `Content-Type` 包含 `text/event-stream`
- 心跳流至少有 `ready` / 若干 `heartbeat` / `done`
- 进度流最后一条是 100%
- `demo=true` 的频道不依赖 Redis 也能收到事件

---

## 9. 常见问题

**Q: Swagger 里点 SSE 接口，页面转圈？**  
A: Swagger 会等整个响应结束。用 `curl -N` 或前端 `EventSource` 看流。

**Q: 事件要隔很久才出现？**  
A: 多半是 Nginx / CDN 缓冲。关 `proxy_buffering`，并确认没开 gzip 缓冲。

**Q: 为什么频道订阅会自己结束？**  
A: 教学接口带了 `timeout_ms`，避免演示连接永不退出。生产通知流可以一直挂着，靠注释行心跳保活。

**Q: 和 Celery 进度怎么接？**  
A: Worker 把进度写入 Redis / DB，SSE 生成器去读；本模块的 `/progress` 只演示「推送形状」，不绑死任务队列。
