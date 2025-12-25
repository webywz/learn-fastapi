# FastAPI 和中间件方法完全手册

## 📚 目录
1. [路由装饰器](#路由装饰器)
2. [请求对象 (Request)](#请求对象-request)
3. [响应对象 (Response)](#响应对象-response)
4. [依赖注入 (Depends)](#依赖注入-depends)
5. [中间件](#中间件)
6. [异常处理](#异常处理)

---

## 路由装饰器

### `@app.get()` / `@router.get()`
**作用**: 定义 GET 请求路由

**参数**:
- `path`: 路径（必填）
- `response_model`: 响应模型（可选）
- `status_code`: HTTP 状态码（可选）
- `tags`: API 文档分组（可选）
- `summary`: 简短描述（可选）

```python
from fastapi import APIRouter
from schemas.user import User

router = APIRouter()

# ===== 基础用法 =====
@router.get("/users")
async def get_users():
    return {"users": []}

# ===== 路径参数 =====
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    # user_id 自动从 URL 提取并转换为 int
    return {"user_id": user_id}

# ===== 查询参数 =====
@router.get("/users")
async def search_users(keyword: str, page: int = 1):
    # GET /users?keyword=alice&page=2
    # keyword = "alice", page = 2
    return {"keyword": keyword, "page": page}

# ===== 指定响应模型 =====
@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    user = await get_user_from_db(user_id)
    return user  # FastAPI 自动按 User 模型序列化

# ===== 完整示例 =====
@router.get(
    "/users/{user_id}",
    response_model=User,
    status_code=200,
    tags=["用户管理"],
    summary="获取用户信息",
    description="根据用户 ID 获取用户详细信息"
)
async def get_user(user_id: int):
    return await get_user_from_db(user_id)
```

---

### `@app.post()`
**作用**: 定义 POST 请求路由

```python
from schemas.user import UserCreate, User

# ===== 接收 JSON 请求体 =====
@router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    # user_data 自动从请求体解析并验证
    user = await create_user_in_db(user_data)
    return user

# 请求示例：
# POST /users
# Content-Type: application/json
# {"username": "alice", "email": "alice@example.com", "password": "123456"}
```

---

### `@app.put()` / `@app.patch()`
**作用**: 定义 PUT/PATCH 请求路由

```python
# PUT - 完整更新
@router.put("/users/{user_id}")
async def update_user(user_id: int, user_data: UserUpdate):
    user = await update_user_in_db(user_id, user_data)
    return user

# PATCH - 部分更新
@router.patch("/users/{user_id}")
async def partial_update_user(user_id: int, user_data: UserUpdate):
    # UserUpdate 的所有字段都是 Optional
    user = await update_user_in_db(user_id, user_data)
    return user
```

---

### `@app.delete()`
**作用**: 定义 DELETE 请求路由

```python
@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    await delete_user_from_db(user_id)
    return {"message": "删除成功"}
```

---

## 请求对象 (Request)

### `Request` 对象属性和方法

```python
from fastapi import Request

@app.get("/test")
async def test_request(request: Request):
    """获取请求的各种信息"""

    # ===== URL 信息 =====
    request.url                 # 完整 URL: http://localhost:8000/test?page=1
    request.url.path            # 路径: /test
    request.url.scheme          # 协议: http
    request.url.hostname        # 主机名: localhost
    request.url.port            # 端口: 8000

    # ===== HTTP 方法 =====
    request.method              # GET, POST, PUT, DELETE, etc.

    # ===== Headers (请求头) =====
    request.headers             # 所有请求头（字典）
    request.headers.get("authorization")  # 获取特定请求头
    request.headers.get("user-agent")     # 获取 User-Agent

    # ===== 查询参数 =====
    request.query_params        # 查询参数（字典）
    # GET /test?page=1&size=10
    request.query_params.get("page")    # "1" (字符串)
    request.query_params.get("size")    # "10"

    # ===== 客户端信息 =====
    request.client              # 客户端对象
    request.client.host         # 客户端 IP: "127.0.0.1"
    request.client.port         # 客户端端口

    # ===== Cookies =====
    request.cookies             # 所有 cookies（字典）
    request.cookies.get("session_id")

    # ===== 请求体 =====
    body = await request.body()          # 原始字节
    json_data = await request.json()     # 解析为 JSON

    # ===== 表单数据 =====
    form_data = await request.form()     # 表单数据

    # ===== 自定义状态（在中间件中设置）=====
    request.state.user_id = 123          # 设置
    user_id = request.state.user_id      # 获取

    return {
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host
    }
```

---

### 实用示例

```python
# ===== 1. 获取 Authorization Token =====
@app.get("/protected")
async def protected_route(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="未提供认证信息")

    # 提取 token: "Bearer eyJhbGci..."
    token = auth_header.replace("Bearer ", "")
    return {"token": token}


# ===== 2. 记录客户端 IP =====
@app.get("/")
async def log_ip(request: Request):
    client_ip = request.client.host
    logger.info(f"Request from {client_ip}")
    return {"ip": client_ip}


# ===== 3. 获取请求 ID（中间件设置）=====
async def middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    return response

@app.get("/test")
async def test(request: Request):
    request_id = request.state.request_id
    return {"request_id": request_id}
```

---

## 响应对象 (Response)

### 设置响应头

```python
from fastapi import Response

@app.get("/")
async def set_headers(response: Response):
    # 设置自定义响应头
    response.headers["X-Custom-Header"] = "MyValue"
    response.headers["X-Request-ID"] = "abc123"

    return {"message": "success"}
```

---

### 设置 Cookie

```python
@app.get("/login")
async def login(response: Response):
    # 设置 cookie
    response.set_cookie(
        key="session_id",
        value="abc123",
        max_age=3600,        # 有效期（秒）
        httponly=True,       # 禁止 JavaScript 访问
        secure=True,         # 只通过 HTTPS 传输
        samesite="lax"       # CSRF 保护
    )

    return {"message": "登录成功"}
```

---

### 删除 Cookie

```python
@app.get("/logout")
async def logout(response: Response):
    # 删除 cookie
    response.delete_cookie("session_id")
    return {"message": "登出成功"}
```

---

### 返回不同类型的响应

```python
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse, RedirectResponse

# ===== JSON 响应（默认）=====
@app.get("/json")
async def json_response():
    return {"message": "JSON response"}


# ===== 纯文本响应 =====
@app.get("/text")
async def text_response():
    return PlainTextResponse("This is plain text")


# ===== 文件下载 =====
@app.get("/download")
async def download_file():
    return FileResponse(
        path="/path/to/file.pdf",
        filename="download.pdf",
        media_type="application/pdf"
    )


# ===== 重定向 =====
@app.get("/redirect")
async def redirect():
    return RedirectResponse(url="/new-path")


# ===== 自定义状态码 =====
@app.get("/created", status_code=201)
async def created():
    return {"message": "资源已创建"}
```

---

## 依赖注入 (Depends)

### 基础用法

```python
from fastapi import Depends

# ===== 定义依赖函数 =====
async def get_current_user(token: str):
    """从 token 获取当前用户"""
    user_id = decode_token(token)
    user = await get_user(user_id)
    return user


# ===== 使用依赖 =====
@app.get("/users/me")
async def get_me(current_user: User = Depends(get_current_user)):
    # current_user 由 get_current_user() 返回
    return current_user
```

---

### 多层依赖

```python
# 依赖1: 获取数据库连接
async def get_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()


# 依赖2: 获取当前用户（依赖于数据库）
async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db)  # 依赖于 get_db
):
    user_id = decode_token(token)
    user = await UserService.get_user_by_id(db, user_id)
    return user


# 依赖3: 检查是否是管理员（依赖于当前用户）
async def get_admin_user(
    current_user: User = Depends(get_current_user)  # 依赖于 get_current_user
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    return current_user


# 路由使用
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user)  # 依赖链自动执行
):
    # get_db() → get_current_user() → get_admin_user()
    await delete_user_from_db(user_id)
    return {"message": "删除成功"}
```

---

### 类依赖

```python
from fastapi import Query

class PaginationParams:
    """分页参数依赖"""
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100)
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


# 使用
@app.get("/users")
async def get_users(
    pagination: PaginationParams = Depends()
):
    # pagination.page, pagination.page_size, pagination.offset
    users = await get_users_from_db(
        offset=pagination.offset,
        limit=pagination.page_size
    )
    return users
```

---

## 中间件

### 创建中间件

```python
from fastapi import Request
import time

# ===== 方式1: 装饰器方式 =====
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加处理时间响应头"""
    start_time = time.time()

    # 调用下一个中间件/路由
    response = await call_next(request)

    # 计算处理时间
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response


# ===== 方式2: 函数方式 =====
async def log_middleware(request: Request, call_next):
    """日志中间件"""
    print(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"Response: {response.status_code}")
    return response

# 注册
app.middleware("http")(log_middleware)
```

---

### 中间件执行顺序

```python
# 注册顺序
app.middleware("http")(middleware_a)  # 第一个注册
app.middleware("http")(middleware_b)  # 第二个注册
app.middleware("http")(middleware_c)  # 第三个注册

# 执行顺序（洋葱模型）:
"""
请求 →
    middleware_c 开始
        middleware_b 开始
            middleware_a 开始
                路由处理
            middleware_a 结束
        middleware_b 结束
    middleware_c 结束
← 响应
"""
```

---

### 常用中间件示例

```python
import uuid
import time
from fastapi import Request, status
from fastapi.responses import JSONResponse

# ===== 1. 请求 ID 中间件 =====
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """为每个请求添加唯一 ID"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


# ===== 2. CORS 中间件（已内置）=====
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许的域名
    allow_credentials=True,                    # 允许携带 cookie
    allow_methods=["*"],                       # 允许的 HTTP 方法
    allow_headers=["*"],                       # 允许的请求头
)


# ===== 3. 异常捕获中间件 =====
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    """捕获所有异常"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"}
        )


# ===== 4. 限流中间件 =====
from collections import defaultdict
from datetime import datetime, timedelta

# 简单的内存限流（生产环境用 Redis）
request_counts = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """每个 IP 每分钟最多 60 次请求"""
    client_ip = request.client.host
    now = datetime.now()

    # 清理过期记录
    request_counts[client_ip] = [
        req_time for req_time in request_counts[client_ip]
        if now - req_time < timedelta(minutes=1)
    ]

    # 检查限流
    if len(request_counts[client_ip]) >= 60:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "请求过于频繁，请稍后再试"}
        )

    # 记录请求
    request_counts[client_ip].append(now)

    response = await call_next(request)
    return response


# ===== 5. 性能监控中间件 =====
@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """记录慢接口"""
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000

    # 记录慢接口（超过 1 秒）
    if process_time > 1000:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {process_time:.2f}ms"
        )

    return response
```

---

## 异常处理

### 注册异常处理器

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from common.exceptions import BusinessException

# ===== 处理业务异常 =====
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """处理业务异常"""
    return JSONResponse(
        status_code=200,  # 业务错误也返回 200
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None
        }
    )


# ===== 处理 HTTP 异常 =====
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTP 异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# ===== 处理所有异常 =====
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """兜底异常处理"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )
```

---

## FastAPI 应用配置

### 创建应用

```python
from fastapi import FastAPI

app = FastAPI(
    title="My API",                      # API 名称
    version="1.0.0",                     # 版本
    description="API Description",       # 描述
    docs_url="/docs",                    # Swagger UI 路径
    redoc_url="/redoc",                  # ReDoc 路径
    openapi_url="/openapi.json",         # OpenAPI schema 路径
    debug=True                           # 调试模式
)
```

---

### 生命周期事件

```python
# ===== 启动事件 =====
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("Application starting...")
    # 初始化数据库
    await init_database()
    # 加载配置
    await load_config()


# ===== 关闭事件 =====
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print("Application shutting down...")
    # 关闭数据库连接
    await close_database()
```

---

## 方法速查表

### 请求方法
| 装饰器 | HTTP 方法 | 用途 |
|--------|-----------|------|
| `@app.get()` | GET | 查询数据 |
| `@app.post()` | POST | 创建数据 |
| `@app.put()` | PUT | 完整更新 |
| `@app.patch()` | PATCH | 部分更新 |
| `@app.delete()` | DELETE | 删除数据 |

### Request 对象
| 属性/方法 | 作用 |
|-----------|------|
| `request.method` | HTTP 方法 |
| `request.url.path` | URL 路径 |
| `request.headers` | 请求头 |
| `request.query_params` | 查询参数 |
| `request.client.host` | 客户端 IP |
| `request.state` | 自定义状态 |
| `await request.json()` | 解析 JSON |

### Response 对象
| 方法 | 作用 |
|------|------|
| `response.headers["X-Custom"]` | 设置响应头 |
| `response.set_cookie()` | 设置 Cookie |
| `response.delete_cookie()` | 删除 Cookie |

### 依赖注入
| 用法 | 作用 |
|------|------|
| `Depends(func)` | 基础依赖 |
| `Depends(Class)` | 类依赖 |
| 多层 Depends | 依赖链 |

### 中间件
| 用法 | 作用 |
|------|------|
| `@app.middleware("http")` | 注册中间件 |
| `await call_next(request)` | 调用下一个处理器 |
