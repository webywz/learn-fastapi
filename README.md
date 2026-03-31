# 🎓 FastAPI 后端开发完整教程

> 专为前端开发者打造的后端学习项目

这是一个从零开始的 FastAPI 后端教学项目，涵盖了后端开发的所有核心知识点。所有代码都有详细的中文注释，帮助你快速掌握 Python Web 开发。

---

## 📚 项目特色

✅ **详细注释**：每个文件都有大量注释，解释"为什么"而不只是"怎么做"
✅ **完整架构**：统一响应格式、错误码、异常处理、日志系统
✅ **最佳实践**：遵循工业标准的项目结构和代码规范
✅ **前端友好**：从前端视角解释后端概念，易于理解
✅ **实战导向**：可直接用于真实项目

---

## 🎯 你将学到

### 1️⃣ 核心概念
- 统一响应格式（Response Schema）
- 错误码体系（Error Codes）
- 自定义异常处理（Custom Exceptions）
- 全局异常处理器（Global Exception Handler）

### 2️⃣ 数据库
- SQLAlchemy ORM（对象关系映射）
- 异步数据库操作
- 数据库迁移（Alembic）
- 连接池管理

### 3️⃣ 安全
- 密码加密（bcrypt）
- JWT 认证
- 依赖注入（Dependency Injection）
- 权限控制

### 4️⃣ 中间件
- 请求日志记录
- CORS 跨域处理
- 异常统一处理

### 5️⃣ API 开发
- RESTful API 设计
- Pydantic 数据验证
- 自动生成 API 文档
- 分页、搜索、过滤

---

## 📁 项目结构

```
backend-tutorial/
├── common/                  # 公共模块
│   ├── response.py         # 统一响应格式 ⭐
│   ├── error_codes.py      # 错误码定义 ⭐
│   └── exceptions.py       # 自定义异常 ⭐
├── core/                    # 核心配置
│   ├── config.py           # 配置文件 ⭐
│   ├── database.py         # 数据库配置 ⭐
│   └── security.py         # 安全模块（密码、JWT）⭐
├── middleware/              # 中间件
│   ├── logger.py           # 请求日志中间件 ⭐
│   └── error_handler.py    # 全局异常处理器 ⭐
├── models/                  # 数据库模型（ORM）
│   └── user.py             # 用户模型 ⭐
├── schemas/                 # Pydantic 模型（API 数据格式）
│   └── user.py             # 用户 Schema ⭐
├── api/                     # API 路由
│   ├── deps.py             # 依赖注入 ⭐
│   └── v1/
│       ├── auth.py         # 认证接口（注册、登录）⭐
│       └── users.py        # 用户接口 ⭐
├── services/                # 业务逻辑层
│   └── user_service.py     # 用户服务 ⭐
├── utils/                   # 工具函数
│   └── logger.py           # 日志配置 ⭐
├── logs/                    # 日志文件目录
├── main.py                  # 应用入口 ⭐
├── requirements.txt         # Python 依赖
├── .env.example            # 环境变量模板
└── README.md               # 项目文档（本文件）

⭐ = 包含详细注释和学习笔记的核心文件
```

---

## 🚀 快速开始

### 1. 克隆或进入项目

```bash
cd backend-tutorial
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，修改配置
# 特别注意：生产环境必须修改 SECRET_KEY！
```

### 5. 运行项目

```bash
python main.py
```

或者使用 uvicorn：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### 6. 访问 API 文档

打开浏览器访问：
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

---

## 📖 API 使用示例

### 1. 用户注册

```bash
POST http://localhost:8080/api/v1/auth/register
Content-Type: application/json

{
  "username": "alice",
  "email": "alice@example.com",
  "password": "123456"
}
```

**响应：**
```json
{
  "code": 0,
  "message": "注册成功",
  "data": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "is_active": true,
    "is_superuser": false,
    "created_at": "2024-01-01T12:00:00",
    "updated_at": "2024-01-01T12:00:00"
  }
}
```

### 2. 用户登录

```bash
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json

{
  "username": "alice",
  "password": "123456"
}
```

**响应：**
```json
{
  "code": 0,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

### 3. 获取当前用户信息（需要登录）

```bash
GET http://localhost:8080/api/v1/users/me
Authorization: Bearer <token>
```

**响应：**
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    ...
  }
}
```

---

## 🎯 学习路径

### 第一步：理解统一响应格式

阅读文件：`common/response.py`

**关键概念：**
- 为什么需要统一响应格式？
- 成功和失败的响应结构
- 分页数据的处理

### 第二步：掌握错误码体系

阅读文件：`common/error_codes.py`, `common/exceptions.py`

**关键概念：**
- HTTP 状态码 vs 业务错误码
- 如何设计错误码
- 自定义异常类

### 第三步：配置和数据库

阅读文件：`core/config.py`, `core/database.py`

**关键概念：**
- 环境变量管理
- 数据库连接池
- ORM 基础

### 第四步：安全认证

阅读文件：`core/security.py`, `api/deps.py`

**关键概念：**
- 密码加密（不可逆）
- JWT 工作原理
- 依赖注入

### 第五步：中间件和日志

阅读文件：`middleware/`, `utils/logger.py`

**关键概念：**
- 中间件执行顺序
- 请求追踪
- 日志分级

### 第六步：数据模型

阅读文件：`models/user.py`, `schemas/user.py`

**关键概念：**
- ORM 模型 vs Pydantic 模型
- 数据库字段类型
- 数据验证

### 第七步：业务逻辑和 API

阅读文件：`services/`, `api/v1/`

**关键概念：**
- 分层架构
- RESTful API 设计
- CRUD 操作

---

## 💡 核心知识点详解

### 1. 统一响应格式

**为什么需要？**
- 前端可以写统一的拦截器处理响应
- 减少前端的判断逻辑
- 提高团队协作效率

**响应结构：**
```json
{
  "code": 0,           // 0=成功，非0=失败
  "message": "success", // 提示信息
  "data": {}           // 实际数据
}
```

**前端使用（Axios 示例）：**
```javascript
axios.interceptors.response.use(
  response => {
    if (response.data.code === 0) {
      return response.data.data;  // 返回实际数据
    } else {
      // 统一错误提示
      message.error(response.data.message);
      return Promise.reject(response.data);
    }
  }
);
```

### 2. 错误码体系

**设计规范：**
- `0`：成功
- `4xxxx`：客户端错误（用户输入、权限等）
- `5xxxx`：服务器错误（系统异常）

**错误码示例：**
```python
40001: 用户名已存在
40002: 邮箱已存在
41000: 未登录
41001: Token 过期
50000: 服务器内部错误
```

**前端处理：**
```javascript
switch(response.data.code) {
  case 41000: // 未登录
  case 41001: // Token 过期
    router.push('/login');
    break;
  case 40001: // 用户名已存在
    formErrors.username = '用户名已存在';
    break;
  default:
    message.error(response.data.message);
}
```

### 3. JWT 认证流程

**登录流程：**
```
1. 用户输入用户名和密码
2. 后端验证用户名和密码
3. 验证通过，生成 JWT Token
4. 返回 Token 给前端
5. 前端存储 Token（localStorage）
```

**访问接口流程：**
```
1. 前端在请求头携带 Token
   Authorization: Bearer <token>
2. 后端验证 Token
3. Token 有效，返回数据
4. Token 无效/过期，返回 401 错误
```

**安全性：**
- Token 有签名，无法篡改
- 设置过期时间，降低风险
- 不要在 Token 里存敏感信息（密码等）

### 4. 数据库 ORM

**ORM 的好处：**
- 用面向对象的方式操作数据库
- 防止 SQL 注入
- 跨数据库（SQLite、PostgreSQL、MySQL）

**示例对比：**

❌ 原生 SQL（不推荐）：
```python
cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
```

✅ ORM（推荐）：
```python
user = await db.execute(select(User).where(User.username == username))
```

### 5. 依赖注入

**不使用依赖注入：**
```python
@router.get("/users/me")
async def get_me(request: Request):
    token = request.headers.get("Authorization")
    user_id = parse_token(token)
    db = get_database()
    user = db.query(User).filter(User.id == user_id).first()
    return user
```

**使用依赖注入：**
```python
@router.get("/users/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user  # FastAPI 自动处理所有逻辑
```

---

## 🔧 常见问题

### Q1: 如何添加新的 API 接口？

1. 在 `api/v1/` 创建新的路由文件
2. 定义路由函数
3. 在 `main.py` 中注册路由

### Q2: 如何添加新的数据表？

1. 在 `models/` 创建模型类
2. 在 `schemas/` 创建对应的 Pydantic 模型
3. 运行应用，表会自动创建（或使用 Alembic 迁移）

### Q3: 如何修改 Token 过期时间？

修改 `.env` 文件中的 `ACCESS_TOKEN_EXPIRE_MINUTES`

### Q4: 如何部署到生产环境？

1. 修改 `.env` 文件（DEBUG=False, 修改 SECRET_KEY）
2. 使用 PostgreSQL 替代 SQLite
3. 使用 Gunicorn + Uvicorn Workers
4. 配置 Nginx 反向代理

---

## 📝 待完善功能（练习项目）

以下功能你可以自己尝试实现：

- [ ] 邮箱验证
- [ ] 忘记密码
- [ ] 角色和权限管理（RBAC）
- [ ] 文件上传
- [ ] Refresh Token
- [ ] 接口限流
- [ ] 数据缓存（Redis）
- [ ] 单元测试
- [ ] Docker 部署

---

## 🎓 学习建议

### 对于前端开发者

1. **类比学习**：文件中有大量前端类比，帮助你理解后端概念
2. **动手实践**：不要只看代码，一定要自己运行和修改
3. **阅读注释**：每个文件的注释都很详细，慢慢读
4. **调试技巧**：多用 `print()` 和日志查看数据流转

### 学习顺序

1. 先运行项目，看效果
2. 阅读核心文件（标记 ⭐ 的文件）
3. 尝试添加新功能
4. 阅读 FastAPI 官方文档

---

## 📚 推荐资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Pydantic 文档](https://docs.pydantic.dev/)

---

## 💬 反馈和建议

如果你有任何问题或建议，欢迎提 Issue！

---

祝学习愉快！🎉
