"""
===========================================
用户 Pydantic 模型 (User Schemas)
===========================================

作用：
  定义 API 输入输出的数据格式

Pydantic 模型 vs 数据库模型：
  - 数据库模型（models/user.py）: 数据库表结构
  - Pydantic 模型（schemas/user.py）: API 接口的数据格式

为什么要分开？
  1. 数据库字段 ≠ API 字段
     例如：hashed_password 不应该返回给前端
  2. 不同场景需要不同字段
     创建用户：username, password, email
     返回用户：id, username, email（没有密码）
  3. 数据验证
     Pydantic 自动验证数据类型和格式

类比前端：
  - 类似 TypeScript 的 interface
  - 或者 Zod schema
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ============================================================
# 基础模型
# ============================================================

class UserBase(BaseModel):
    """
    用户基础模型

    包含所有模型共有的字段
    其他模型继承这个基类
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名",
        examples=["alice"]
    )
    email: EmailStr = Field(
        ...,
        description="邮箱",
        examples=["alice@example.com"]
    )


# ============================================================
# 请求模型（用于接收前端数据）
# ============================================================

class UserCreate(UserBase):
    """
    创建用户的请求模型

    用于注册接口

    使用示例（前端）:
        POST /api/v1/auth/register
        {
            "username": "alice",
            "email": "alice@example.com",
            "password": "123456"
        }

    使用示例（后端）:
        @router.post("/register")
        async def register(user_data: UserCreate):
            # user_data 会自动验证
            # 如果验证失败，自动返回 422 错误
            ...
    """
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="密码（明文，后端会加密）",
        examples=["123456"]
    )


class UserUpdate(BaseModel):
    """
    更新用户的请求模型

    所有字段都是可选的（部分更新）

    使用示例（前端）:
        PUT /api/v1/users/me
        {
            "email": "newemail@example.com"
        }
    """
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50
    )
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(
        None,
        min_length=6,
        max_length=100
    )


class UserLogin(BaseModel):
    """
    用户登录的请求模型

    使用示例（前端）:
        POST /api/v1/auth/login
        {
            "username": "alice",
            "password": "123456"
        }
    """
    username: str
    password: str


# ============================================================
# 响应模型（用于返回给前端）
# ============================================================

class User(UserBase):
    """
    用户响应模型

    返回给前端的用户信息

    注意：
    - 不包含 password 或 hashed_password（安全）
    - 包含 id 和时间字段

    使用示例（后端）:
        @router.get("/users/me", response_model=User)
        async def get_current_user(current_user: UserModel):
            # FastAPI 会自动把 UserModel 转换为 User schema
            # 只返回 User schema 中定义的字段
            return current_user

    使用示例（前端响应）:
        {
            "code": 0,
            "message": "success",
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
    """
    id: int
    is_active: bool
    is_superuser: bool = False
    created_at: datetime
    updated_at: datetime

    # Pydantic V2 配置
    model_config = ConfigDict(
        from_attributes=True,  # 允许从 ORM 模型创建
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2024-01-01T12:00:00",
                "updated_at": "2024-01-01T12:00:00"
            }
        }
    )


class UserInDB(User):
    """
    数据库中的用户模型

    包含加密后的密码（仅在内部使用）

    注意：
    - 这个模型不应该返回给前端！
    - 只在后端内部使用
    """
    hashed_password: str


# ============================================================
# Token 模型
# ============================================================

class Token(BaseModel):
    """
    Token 响应模型

    登录成功后返回

    使用示例:
        {
            "code": 0,
            "message": "登录成功",
            "data": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer"
            }
        }
    """
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    Token 载荷模型

    解码 JWT 后的数据结构

    使用示例:
        payload = decode_access_token(token)
        token_data = TokenPayload(**payload)
        user_id = token_data.sub
    """
    sub: Optional[str] = None  # subject（主题）= 用户 ID
    exp: Optional[int] = None  # expiration（过期时间）


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结（给前端开发的你）：

1. 【Pydantic 模型的作用】
   - 数据验证：自动检查类型、长度、格式等
   - 数据序列化：Python 对象 ↔ JSON
   - 文档生成：自动生成 OpenAPI 文档

   类比前端：
   Pydantic   ≈   Zod / Joi
   FastAPI    ≈   tRPC（自动类型推导）

2. 【常用字段类型】
   - str: 字符串
   - int: 整数
   - float: 浮点数
   - bool: 布尔值
   - EmailStr: 邮箱（自动验证格式）
   - HttpUrl: URL（自动验证格式）
   - datetime: 日期时间
   - Optional[T]: 可选字段
   - List[T]: 列表

3. 【Field 参数】
   Field(
       ...,                    # 必填（等同于 required=True）
       default=None,           # 默认值
       min_length=3,           # 最小长度
       max_length=50,          # 最大长度
       gt=0,                   # 大于（greater than）
       ge=0,                   # 大于等于（greater equal）
       lt=100,                 # 小于（less than）
       le=100,                 # 小于等于（less equal）
       regex="^[a-z]+$",       # 正则表达式
       description="描述",     # 字段描述（用于文档）
       examples=["示例"]       # 示例值（用于文档）
   )

4. 【模型继承】
   UserBase（基类）
     ├── UserCreate（继承 + 添加 password）
     └── User（继承 + 添加 id, created_at 等）

   好处：
   - 避免重复定义字段
   - 统一修改基础字段

5. 【请求模型 vs 响应模型】
   请求模型（Request）:
     - 用于接收前端数据
     - 例如：UserCreate, UserUpdate, UserLogin

   响应模型（Response）:
     - 用于返回给前端
     - 例如：User, Token

   为什么要分开？
     请求：username, password (有密码)
     响应：id, username, email (没密码，有 id)

6. 【from_attributes = True】
   允许从 ORM 模型创建 Pydantic 模型

   # 数据库查询
   user_orm = await db.get(User, 1)  # ORM 对象

   # 转换为 Pydantic 模型
   user_schema = UserSchema.from_orm(user_orm)  # ✅ 需要 from_attributes=True

   # FastAPI 自动转换
   @router.get("/users/{id}", response_model=UserSchema)
   async def get_user(id: int):
       user_orm = await db.get(User, id)
       return user_orm  # FastAPI 自动转换为 UserSchema

7. 【数据验证示例】
   class UserCreate(BaseModel):
       username: str = Field(min_length=3, max_length=50)
       email: EmailStr
       password: str = Field(min_length=6)

   # 有效数据
   data = {
       "username": "alice",
       "email": "alice@example.com",
       "password": "123456"
   }
   user = UserCreate(**data)  # ✅ 通过验证

   # 无效数据
   data = {
       "username": "ab",  # 太短
       "email": "invalid-email",  # 格式错误
       "password": "123"  # 太短
   }
   user = UserCreate(**data)  # ❌ 抛出 ValidationError

8. 【实际使用示例】

   # 定义 API（后端）
   @router.post("/users", response_model=User)
   async def create_user(user_data: UserCreate):
       # user_data 已经过验证
       # 如果验证失败，FastAPI 自动返回 422 错误
       user = await create_user_service(user_data)
       return user  # 自动转换为 User schema

   # 调用 API（前端）
   const response = await axios.post('/api/v1/users', {
       username: 'alice',
       email: 'alice@example.com',
       password: '123456'
   });

   // 返回的数据结构
   interface User {
       id: number;
       username: string;
       email: string;
       is_active: boolean;
       is_superuser: boolean;
       created_at: string;
       updated_at: string;
   }

9. 【安全注意事项】
   ✅ DO:
     - 返回模型不包含密码
     - 使用 EmailStr 验证邮箱
     - 设置合理的字段长度限制

   ❌ DON'T:
     - 不要在响应中返回 hashed_password
     - 不要接受未验证的数据
     - 不要在 token 中存储敏感信息
"""
