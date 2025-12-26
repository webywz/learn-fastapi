"""
===========================================
配置文件模块 (Configuration Module)
===========================================

作用：
  集中管理项目的所有配置参数

为什么需要配置文件？
  1. 集中管理：所有配置都在一个地方，方便修改
  2. 环境区分：开发环境、测试环境、生产环境使用不同配置
  3. 安全性：敏感信息（密码、密钥）通过环境变量管理，不提交到代码库
  4. 类型安全：使用 Pydantic 验证配置，避免配置错误

类比前端：
  - 类似 .env 文件 + config.ts
  - Vite: import.meta.env.VITE_API_URL
  - React: process.env.REACT_APP_API_URL
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


# ============================================================
# 配置类
# ============================================================

class Settings(BaseSettings):
    """
    项目配置类

    使用 Pydantic BaseSettings 的好处：
      1. 自动从环境变量读取配置
      2. 自动进行类型验证
      3. 提供默认值
      4. IDE 有类型提示

    配置优先级（从高到低）：
      1. 环境变量（如 export DATABASE_URL=...）
      2. .env 文件
      3. 代码中的默认值

    如何使用：
      from core.config import settings
      print(settings.APP_NAME)  # 获取配置
    """

    # =========================================
    # 应用基础配置
    # =========================================

    APP_NAME: str = "FastAPI Backend Tutorial"
    """应用名称"""

    APP_VERSION: str = "1.0.0"
    """应用版本号"""

    APP_DESCRIPTION: str = "一个完整的 FastAPI 后端教学项目"
    """应用描述"""

    DEBUG: bool = True
    """
    调试模式
    - True: 开发环境，显示详细错误信息
    - False: 生产环境，隐藏敏感信息

    环境变量设置: export DEBUG=False
    """

    API_V1_PREFIX: str = "/api/v1"
    """API 路由前缀，所有接口都以这个开头"""

    # =========================================
    # 数据库配置
    # =========================================

    DATABASE_URL: str = "sqlite+aiosqlite:///./tutorial.db"
    """
    数据库连接字符串

    SQLite（开发环境，默认）:
      sqlite+aiosqlite:///./tutorial.db

    PostgreSQL（生产环境推荐）:
      postgresql+asyncpg://user:password@localhost:5432/dbname

    MySQL（也可以用）:
      mysql+aiomysql://user:password@localhost:3306/dbname

    为什么用 aiosqlite / asyncpg？
      - FastAPI 是异步框架，数据库也要用异步驱动
      - 性能更好，支持高并发

    环境变量设置:
      export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db"
    """

    DATABASE_ECHO: bool = False
    """
    是否打印 SQL 语句
    - True: 在控制台打印所有 SQL（调试用）
    - False: 不打印（生产环境）
    """

    # =========================================
    # JWT (JSON Web Token) 配置
    # =========================================

    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    """
    JWT 签名密钥（非常重要！）

    作用：
      - 用于生成和验证 JWT token
      - 类似你家大门的钥匙，别人不知道就无法伪造 token

    安全要求：
      1. 必须是随机字符串
      2. 长度至少 32 位
      3. 不能泄露（不要提交到 Git）
      4. 生产环境必须通过环境变量设置

    生成随机密钥的方法：
      Python: openssl rand -hex 32
      或者: python -c "import secrets; print(secrets.token_hex(32))"

    环境变量设置:
      export SECRET_KEY="随机生成的密钥"
    """

    ALGORITHM: str = "HS256"
    """
    JWT 加密算法

    常用算法：
      - HS256: HMAC + SHA256（对称加密，用同一个密钥）
      - RS256: RSA + SHA256（非对称加密，公钥私钥）

    我们用 HS256，简单够用
    """

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时
    """
    Access Token 过期时间（分钟）

    Access Token 是用户登录后获得的凭证
    类似前端的 localStorage.getItem('token')

    过期时间设置建议：
      - 开发环境: 24 小时（方便调试）
      - 生产环境: 15-30 分钟（更安全）

    为什么要过期？
      - 安全性：即使 token 泄露，也只能用一段时间
      - 通常配合 Refresh Token 使用

    环境变量设置:
      export ACCESS_TOKEN_EXPIRE_MINUTES=30
    """

    # =========================================
    # CORS (跨域资源共享) 配置
    # =========================================

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # React 开发服务器
        "http://localhost:5173",  # Vite 开发服务器
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    """
    允许跨域的前端地址列表

    什么是跨域？
      前端(localhost:3000) 访问后端(localhost:8000) 就是跨域
      浏览器会阻止跨域请求（安全机制）

    为什么需要配置 CORS？
      让浏览器允许你的前端访问后端接口

    生产环境示例:
      CORS_ORIGINS=["https://your-frontend.com"]

    环境变量设置（JSON 格式）:
      export CORS_ORIGINS='["http://localhost:3000"]'
    """

    CORS_ALLOW_CREDENTIALS: bool = True
    """
    是否允许携带认证信息（cookies, authorization headers）

    - True: 前端可以发送 cookies 和 Authorization 请求头
    - False: 不允许

    如果你需要 JWT 认证，必须设置为 True
    """

    CORS_ALLOW_METHODS: list[str] = ["*"]
    """
    允许的 HTTP 方法

    - ["*"]: 允许所有方法（GET, POST, PUT, DELETE 等）
    - ["GET", "POST"]: 只允许指定的方法
    """

    CORS_ALLOW_HEADERS: list[str] = ["*"]
    """
    允许的 HTTP 请求头

    - ["*"]: 允许所有请求头
    - ["Content-Type", "Authorization"]: 只允许指定的请求头
    """

    # =========================================
    # 日志配置
    # =========================================

    LOG_LEVEL: str = "INFO"
    """
    日志级别

    级别从低到高:
      - DEBUG: 详细的调试信息（开发环境用）
      - INFO: 一般信息（默认）
      - WARNING: 警告信息
      - ERROR: 错误信息
      - CRITICAL: 严重错误

    环境变量设置:
      export LOG_LEVEL="DEBUG"
    """

    LOG_FILE: str = "logs/app.log"
    """日志文件路径"""

    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    """单个日志文件最大大小（超过会创建新文件）"""

    LOG_BACKUP_COUNT: int = 5
    """保留的日志文件备份数量"""

    # =========================================
    # Redis 配置
    # =========================================

    REDIS_HOST: str = "localhost"
    """Redis 服务器地址"""

    REDIS_PORT: int = 6379
    """Redis 服务器端口"""

    REDIS_PASSWORD: Optional[str] = None
    """
    Redis 密码（可选）

    如果你的 Redis 设置了密码，在这里配置
    环境变量设置: export REDIS_PASSWORD="your-password"
    """

    REDIS_DB: int = 0
    """
    Redis 数据库编号

    Redis 默认有 16 个数据库（0-15）
    可以用不同的数据库隔离不同用途的数据
    """

    REDIS_CACHE_TTL: int = 300
    """
    缓存默认过期时间（秒）

    - 300 秒 = 5 分钟
    - 适合频繁变化的数据

    不同场景建议：
      - 用户信息: 300-600 秒（5-10分钟）
      - 热门数据: 3600 秒（1小时）
      - 静态数据: 86400 秒（24小时）
    """

    @property
    def REDIS_URL(self) -> str:
        """
        构建 Redis 连接 URL

        格式: redis://[:password@]host:port/db
        """
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # =========================================
    # Celery 配置
    # =========================================

    CELERY_BROKER_URL: Optional[str] = None
    """
    Celery 消息代理 URL（Broker）

    Broker 用于存储任务队列
    推荐使用 Redis（也可以用 RabbitMQ）

    如果不设置，默认使用 REDIS_URL
    """

    CELERY_RESULT_BACKEND: Optional[str] = None
    """
    Celery 结果存储 URL（Backend）

    Backend 用于存储任务执行结果
    推荐使用 Redis

    如果不设置，默认使用 REDIS_URL
    """

    @property
    def CELERY_BROKER(self) -> str:
        """
        获取 Celery Broker URL

        如果未配置，默认使用 Redis
        """
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        return self.REDIS_URL

    @property
    def CELERY_BACKEND(self) -> str:
        """
        获取 Celery Backend URL

        如果未配置，默认使用 Redis
        """
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        return self.REDIS_URL

    # =========================================
    # 密码加密配置
    # =========================================

    PWD_CONTEXT_SCHEMES: list[str] = ["bcrypt"]
    """
    密码加密方案

    bcrypt 是目前最安全的密码加密算法之一
    - 加密慢（防止暴力破解）
    - 每次加密结果不同（彩虹表攻击无效）
    - 自动加盐（salt）
    """

    # =========================================
    # 分页配置
    # =========================================

    PAGE_SIZE_DEFAULT: int = 10
    """默认每页数量"""

    PAGE_SIZE_MAX: int = 100
    """每页最大数量（防止用户请求太多数据）"""

    # =========================================
    # 阿里云 OSS 配置
    # =========================================

    OSS_ENABLED: bool = False
    """
    是否启用 OSS 存储

    - True: 文件上传到阿里云 OSS
    - False: 文件上传到本地磁盘

    环境变量设置: export OSS_ENABLED=True
    """

    OSS_ACCESS_KEY_ID: Optional[str] = None
    """
    阿里云 AccessKey ID

    获取位置: 阿里云控制台 → 头像 → AccessKey 管理
    ⚠️ 敏感信息，不要提交到代码库

    环境变量设置: export OSS_ACCESS_KEY_ID="LTAI5t..."
    """

    OSS_ACCESS_KEY_SECRET: Optional[str] = None
    """
    阿里云 AccessKey Secret

    ⚠️ 非常敏感，必须保密！

    环境变量设置: export OSS_ACCESS_KEY_SECRET="xxx"
    """

    OSS_ENDPOINT: str = "oss-cn-beijing.aliyuncs.com"
    """
    OSS 地域节点（Endpoint）

    常用节点:
      - 华北2（北京）: oss-cn-beijing.aliyuncs.com
      - 华东1（杭州）: oss-cn-hangzhou.aliyuncs.com
      - 华东2（上海）: oss-cn-shanghai.aliyuncs.com
      - 华南1（深圳）: oss-cn-shenzhen.aliyuncs.com

    注意: 不要包含 https:// 前缀
    """

    OSS_BUCKET: str = "ywzstore"
    """
    OSS Bucket 名称

    Bucket 是 OSS 中的存储空间
    需要在阿里云控制台创建
    """

    OSS_REGION: str = "oss-cn-beijing"
    """OSS 地域标识"""

    OSS_PATH_PREFIX: str = "uploads/"
    """
    OSS 存储路径前缀

    文件会上传到: {OSS_PATH_PREFIX}{filename}
    例如: uploads/2023/12/26/image.jpg
    """

    OSS_USE_SSL: bool = True
    """
    是否使用 HTTPS

    - True: 使用 HTTPS（推荐）
    - False: 使用 HTTP
    """

    OSS_DOMAIN: Optional[str] = None
    """
    自定义域名（可选）

    如果你绑定了自定义域名，在这里设置
    例如: cdn.example.com

    如果不设置，将使用 OSS 默认域名
    """

    @property
    def OSS_FULL_ENDPOINT(self) -> str:
        """
        完整的 OSS Endpoint URL

        返回: https://ywzstore.oss-cn-beijing.aliyuncs.com
        或: http://ywzstore.oss-cn-beijing.aliyuncs.com
        """
        protocol = "https" if self.OSS_USE_SSL else "http"
        return f"{protocol}://{self.OSS_BUCKET}.{self.OSS_ENDPOINT}"

    @property
    def OSS_BASE_URL(self) -> str:
        """
        获取文件访问的基础 URL

        如果设置了自定义域名，使用自定义域名
        否则使用 OSS 默认域名
        """
        if self.OSS_DOMAIN:
            protocol = "https" if self.OSS_USE_SSL else "http"
            return f"{protocol}://{self.OSS_DOMAIN}"
        return self.OSS_FULL_ENDPOINT

    # =========================================
    # 文件上传配置
    # =========================================

    UPLOAD_DIR: str = "data/uploads"
    """
    本地文件上传目录

    当 OSS_ENABLED=False 时使用
    """

    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    """文件上传大小限制（字节）- 默认 10 MB"""

    # =========================================
    # Pydantic 配置
    # =========================================

    class Config:
        """
        Pydantic 配置类

        env_file: 从哪个文件读取环境变量
        env_file_encoding: 文件编码
        case_sensitive: 环境变量是否区分大小写
        """
        env_file = ".env"  # 读取项目根目录的 .env 文件
        env_file_encoding = "utf-8"
        case_sensitive = True  # 环境变量名区分大小写


# ============================================================
# 单例模式获取配置
# ============================================================

@lru_cache()
def get_settings() -> Settings:
    """
    获取配置实例（单例模式）

    为什么用 @lru_cache？
      - 确保只创建一次 Settings 实例
      - 提高性能（不用每次都读取环境变量）
      - 类似前端的单例模式

    使用方式:
      from core.config import get_settings

      settings = get_settings()
      print(settings.APP_NAME)

    FastAPI 依赖注入方式:
      from fastapi import Depends
      from core.config import get_settings, Settings

      @app.get("/info")
      def get_info(settings: Settings = Depends(get_settings)):
          return {"app_name": settings.APP_NAME}
    """
    return Settings()


# 导出一个全局实例，方便使用
settings = get_settings()


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结（给前端开发的你）：

1. 【环境变量】
   后端和前端都需要环境变量来管理配置

   前端 (.env):
     VITE_API_URL=http://localhost:8000
     VITE_APP_NAME=My App

   后端 (.env):
     DATABASE_URL=postgresql://...
     SECRET_KEY=xxx

2. 【配置优先级】
   环境变量 > .env 文件 > 默认值

   这样可以：
   - 开发时用 .env
   - 生产时用环境变量（更安全）

3. 【类型安全】
   Pydantic 会自动验证类型：

   # 正确
   DEBUG=true  → settings.DEBUG = True (bool)

   # 错误
   PORT=abc  → 报错（不是数字）

4. 【单例模式】
   @lru_cache() 确保只创建一次配置实例
   类似前端的:

   let config: Config | null = null;
   export function getConfig() {
     if (!config) {
       config = new Config();
     }
     return config;
   }

5. 【实际使用示例】

   # 创建 .env 文件（项目根目录）
   APP_NAME="我的博客系统"
   DEBUG=True
   DATABASE_URL="sqlite+aiosqlite:///./blog.db"
   SECRET_KEY="your-secret-key-here"

   # 在代码中使用
   from core.config import settings

   print(settings.APP_NAME)  # "我的博客系统"
   print(settings.DEBUG)  # True

6. 【生产环境部署】
   生产环境不要用 .env 文件（不安全）
   而是在服务器设置环境变量：

   # Linux / macOS
   export SECRET_KEY="xxx"
   export DATABASE_URL="postgresql://..."
   export DEBUG=False

   # Docker
   docker run -e SECRET_KEY="xxx" -e DATABASE_URL="..." my-app

   # Kubernetes
   env:
     - name: SECRET_KEY
       valueFrom:
         secretKeyRef:
           name: my-secret
           key: secret-key

7. 【安全最佳实践】
   ✅ DO:
     - SECRET_KEY 通过环境变量设置
     - .env 添加到 .gitignore
     - 提供 .env.example 作为模板

   ❌ DON'T:
     - 不要把密钥提交到 Git
     - 不要在代码里写死密码
     - 不要在生产环境开启 DEBUG
"""
