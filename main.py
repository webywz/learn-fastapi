"""
===========================================
主应用文件 (Main Application)
===========================================

作用：
  FastAPI 应用的入口文件

整合所有模块：
  - 配置
  - 中间件
  - 路由
  - 异常处理
  - 数据库初始化
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import settings
from core.database import init_db
from core.redis import get_redis, close_redis
from utils.logger import setup_logging, get_logger
from middleware.logger import log_requests_middleware
from middleware.error_handler import register_exception_handlers
from api.v1 import auth, users, tasks

# 初始化日志
setup_logging()
logger = get_logger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    docs_url="/docs",  # Swagger 文档地址
    redoc_url="/redoc",  # ReDoc 文档地址
)


# ============================================================
# 注册中间件
# ============================================================

# CORS 跨域中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # 允许的前端地址
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,  # 允许携带 Cookie
    allow_methods=settings.CORS_ALLOW_METHODS,  # 允许的 HTTP 方法
    allow_headers=settings.CORS_ALLOW_HEADERS,  # 允许的请求头
)

# 请求日志中间件
app.middleware("http")(log_requests_middleware)


# ============================================================
# 注册异常处理器
# ============================================================

register_exception_handlers(app)


# ============================================================
# 注册路由
# ============================================================

# 认证路由（注册、登录）
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["认证"]
)

# 用户路由
app.include_router(
    users.router,
    prefix=f"{settings.API_V1_PREFIX}/users",
    tags=["用户"]
)

# 任务路由
app.include_router(
    tasks.router,
    prefix=f"{settings.API_V1_PREFIX}/tasks",
    tags=["任务"]
)


# ============================================================
# 启动和关闭事件
# ============================================================

@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行

    - 初始化数据库
    - 连接 Redis
    - 记录启动日志
    """
    logger.info("=" * 50)
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"📝 调试模式: {settings.DEBUG}")
    logger.info(f"🗄️  数据库: {settings.DATABASE_URL}")
    logger.info(f"💾 Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info("=" * 50)

    # 初始化数据库（创建表）
    await init_db()
    logger.info("✅ 数据库初始化完成")

    # 连接 Redis
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        logger.info("✅ Redis 连接成功")
    except Exception as e:
        logger.warning(f"⚠️  Redis 连接失败: {e}")
        logger.warning("⚠️  缓存功能将不可用")

    logger.info("=" * 50)
    logger.info(f"📖 API 文档: http://127.0.0.1:8080/docs")
    logger.info(f"📖 ReDoc 文档: http://127.0.0.1:8080/redoc")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时执行

    - 关闭 Redis 连接
    - 清理资源
    """
    logger.info("👋 应用正在关闭...")

    # 关闭 Redis 连接
    await close_redis()
    logger.info("✅ Redis 连接已关闭")


# ============================================================
# 根路由
# ============================================================

@app.get("/", tags=["根路由"])
async def root():
    """
    根路径 - 健康检查

    用于检查服务是否正常运行

    响应示例:
        {
            "code": 0,
            "message": "success",
            "data": {
                "app_name": "FastAPI Backend Tutorial",
                "version": "1.0.0",
                "status": "running"
            }
        }
    """
    from common.response import success

    return success(data={
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    })


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    """
    直接运行这个文件启动应用

    命令: python main.py

    或者使用 uvicorn 命令:
    uvicorn main:app --reload --host 0.0.0.0 --port 8080
    """
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # 监听所有网卡
        port=8080,  # 端口
        reload=True,  # 开发模式：代码修改自动重载
        log_level="info"
    )


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【FastAPI 应用配置】
   app = FastAPI(
       title="API 名称",  # 显示在文档中
       version="1.0.0",  # 版本号
       description="描述",  # 描述
       docs_url="/docs",  # Swagger UI 地址
       redoc_url="/redoc"  # ReDoc 地址
   )

2. 【中间件（Middleware）】
   按注册顺序的反向执行

   注册顺序: A → B → C
   执行顺序: C → B → A → 路由 → A → B → C

   常用中间件:
   - CORSMiddleware: 跨域
   - 自定义中间件: 日志、认证等

3. 【路由注册】
   app.include_router(
       router,
       prefix="/api/v1",  # 路由前缀
       tags=["标签"]  # 文档中的分组
   )

4. 【生命周期事件】
   @app.on_event("startup")  # 启动时执行
   @app.on_event("shutdown")  # 关闭时执行

   用途:
   - 启动: 初始化数据库、建立连接
   - 关闭: 清理资源、关闭连接

5. 【运行方式】
   方式1: python main.py
   方式2: uvicorn main:app --reload

   推荐方式2（更灵活）:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000

6. 【API 文档】
   FastAPI 自动生成交互式文档

   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

   好处:
   - 自动生成（无需手写）
   - 可以直接测试 API
   - 自动显示请求/响应格式

7. 【项目启动流程】
   1. 加载配置（core/config.py）
   2. 初始化日志（utils/logger.py）
   3. 创建 FastAPI 应用
   4. 注册中间件
   5. 注册异常处理器
   6. 注册路由
   7. 启动事件（初始化数据库）
   8. 运行服务器

8. 【开发 vs 生产】
   开发环境:
   - reload=True（代码修改自动重载）
   - DEBUG=True
   - 详细的错误信息

   生产环境:
   - reload=False
   - DEBUG=False
   - 不显示敏感信息
   - 使用 Gunicorn + Uvicorn Workers
"""
