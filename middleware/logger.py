"""
===========================================
请求日志中间件 (Request Logger Middleware)
===========================================

作用：
  记录每个 HTTP 请求的详细信息

记录内容：
  - 请求方法和路径
  - 查询参数
  - 客户端 IP
  - 处理时间
  - 响应状态码
"""

import time
import uuid
from fastapi import Request
from utils.logger import get_logger

logger = get_logger(__name__)


async def log_requests_middleware(request: Request, call_next):
    """
    请求日志中间件

    记录所有 HTTP 请求的详细信息和处理时间

    参数:
        request: 请求对象
        call_next: 下一个中间件或路由处理函数

    使用示例（在 main.py）:
        from middleware.logger import log_requests_middleware

        app = FastAPI()
        app.middleware("http")(log_requests_middleware)
    """
    # 生成请求 ID（用于追踪同一个请求）
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # 获取客户端 IP
    client_ip = request.client.host if request.client else "unknown"

    # 记录请求开始
    logger.info(
        f"[{request_id}] --> {request.method} {request.url.path} | "
        f"Client: {client_ip}"
    )

    # 记录查询参数（如果有）
    if request.query_params:
        logger.debug(
            f"[{request_id}] Query params: {dict(request.query_params)}"
        )

    # 记录开始时间
    start_time = time.time()

    # 调用下一个中间件或路由
    response = await call_next(request)

    # 计算处理时间
    process_time = (time.time() - start_time) * 1000  # 转换为毫秒

    # 添加自定义响应头
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    response.headers["X-Request-ID"] = request_id

    # 记录响应
    logger.info(
        f"[{request_id}] <-- {response.status_code} | "
        f"{process_time:.2f}ms | "
        f"{request.method} {request.url.path}"
    )

    return response
