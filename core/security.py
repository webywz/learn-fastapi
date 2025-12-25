"""
===========================================
安全模块 (Security Module)
===========================================

作用：
  1. 密码加密和验证
  2. JWT Token 生成和验证

为什么需要这个模块？
  1. 密码不能明文存储（数据泄露也安全）
  2. JWT 用于用户认证（替代传统的 Session）
  3. 集中管理安全相关的逻辑

类比前端：
  - 密码加密：前端也要对敏感信息加密再传输
  - JWT：类似 localStorage.getItem('token')
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings


# ============================================================
# 密码加密配置
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)
"""
密码加密上下文

使用 bcrypt 算法加密密码

为什么用 bcrypt？
  1. 加密慢（防止暴力破解）
  2. 自动加盐（每次加密结果不同，彩虹表攻击无效）
  3. 安全性高（业界标准）

什么是盐（Salt）？
  - 加密时加入随机字符串
  - 即使密码相同，加密后的结果也不同

  例如：
  password: "123456"
  salt1: "abc" → 加密后: "$2b$12$xyz..."
  salt2: "def" → 加密后: "$2b$12$uvw..."
  两次结果完全不同！
"""


# ============================================================
# 密码加密和验证
# ============================================================

def hash_password(password: str) -> str:
    """
    加密密码

    参数:
        password: 明文密码（用户输入的密码）

    返回:
        str: 加密后的密码（存储到数据库）

    使用示例:
        # 用户注册时
        plain_password = "123456"
        hashed = hash_password(plain_password)
        # hashed = "$2b$12$xyz..." (60个字符)

        # 存储到数据库
        user.hashed_password = hashed

    注意：
        - 加密是单向的，不能反向解密
        - 验证时用 verify_password 对比
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    参数:
        plain_password: 明文密码（用户输入的密码）
        hashed_password: 加密后的密码（数据库中存储的）

    返回:
        bool: True 表示密码正确，False 表示密码错误

    使用示例:
        # 用户登录时
        input_password = "123456"  # 用户输入
        user_hashed = user.hashed_password  # 数据库中的加密密码

        if verify_password(input_password, user_hashed):
            print("密码正确，登录成功")
        else:
            print("密码错误")

    原理：
        不是解密后对比，而是：
        1. 从 hashed_password 中提取盐
        2. 用相同的盐加密 plain_password
        3. 对比两个加密结果是否相同
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# JWT Token 生成和验证
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT Access Token

    参数:
        data: 要编码到 token 中的数据（通常是用户 ID）
        expires_delta: 过期时间（可选，不传则使用配置的默认值）

    返回:
        str: JWT token 字符串

    使用示例:
        # 用户登录成功后
        token_data = {"sub": str(user.id)}  # sub 是 JWT 标准字段，表示主题（用户ID）
        token = create_access_token(token_data)

        # 返回给前端
        return {"access_token": token, "token_type": "bearer"}

        # 前端存储
        localStorage.setItem('token', token)

        # 前端发送请求时携带
        axios.get('/api/users/me', {
          headers: { Authorization: `Bearer ${token}` }
        })

    JWT 包含什么？
        JWT 由三部分组成：Header.Payload.Signature

        Header (头部):
          {"alg": "HS256", "typ": "JWT"}

        Payload (载荷，我们的数据):
          {
            "sub": "1",  # 用户 ID
            "exp": 1699999999  # 过期时间
          }

        Signature (签名，防止篡改):
          HMACSHA256(
            base64UrlEncode(header) + "." + base64UrlEncode(payload),
            SECRET_KEY
          )

    为什么安全？
        - 有签名，无法篡改（改了签名就对不上了）
        - 即使别人看到 token 内容，也无法伪造
        - SECRET_KEY 只有服务器知道
    """
    # 复制数据，避免修改原始数据
    to_encode = data.copy()

    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 使用默认过期时间
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # 添加过期时间到数据中
    to_encode.update({"exp": expire})

    # 生成 token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码并验证 JWT Token

    参数:
        token: JWT token 字符串

    返回:
        dict: Token 中的数据（验证成功）
        None: Token 无效或过期

    使用示例:
        # 从请求头获取 token
        token = request.headers.get("Authorization").replace("Bearer ", "")

        # 解码 token
        payload = decode_access_token(token)

        if payload:
            user_id = payload.get("sub")
            # 根据 user_id 获取用户信息
            user = await get_user(user_id)
        else:
            # Token 无效
            raise AuthenticationException(ErrorCode.TOKEN_INVALID)

    验证什么？
        1. 签名是否正确（是否被篡改）
        2. 是否过期
        3. 格式是否正确
    """
    try:
        # 解码 token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        # Token 无效或过期
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """
    从 Token 中获取用户 ID

    这是对 decode_access_token 的封装，更方便使用

    参数:
        token: JWT token 字符串

    返回:
        int: 用户 ID（验证成功）
        None: Token 无效

    使用示例:
        token = "eyJhbGciOiJIUzI1NiIs..."
        user_id = get_user_id_from_token(token)

        if user_id:
            user = await get_user(user_id)
        else:
            raise AuthenticationException(ErrorCode.TOKEN_INVALID)
    """
    payload = decode_access_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            return int(user_id)
    return None


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结（给前端开发的你）：

1. 【密码加密流程】
   注册:
     用户输入 "123456"
     → hash_password("123456")
     → "$2b$12$xyz..." (存储到数据库)

   登录:
     用户输入 "123456"
     → verify_password("123456", "$2b$12$xyz...")
     → True/False

2. 【为什么不能明文存储密码？】
   假设数据库泄露：
   ❌ 明文存储:
     用户A: "123456"
     用户B: "password"
     黑客可以直接看到所有密码！

   ✅ 加密存储:
     用户A: "$2b$12$xyz..."
     用户B: "$2b$12$abc..."
     黑客看到的是加密后的，无法反向解密

3. 【JWT vs Session】
   传统 Session（有状态）:
     - 服务器存储登录状态
     - 客户端只存 session_id
     - 需要额外的存储（Redis 等）

   JWT（无状态）:
     - 服务器不存储任何状态
     - 所有信息都在 token 里
     - 只需验证签名即可

   类比：
   Session: 餐厅给你一个号码牌，餐厅记录你点了什么菜
   JWT: 餐厅给你一张收据（包含你点的菜），收据有防伪标志

4. 【JWT 结构】
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjk5OTk5OTk5fQ.xxx
   ↑                               ↑                               ↑
   Header (Base64)                 Payload (Base64)                Signature

   可以在 https://jwt.io 解码查看内容

5. 【JWT 安全性】
   ✅ 优点:
     - 无法篡改（有签名）
     - 无需服务器存储（无状态）
     - 跨域友好

   ❌ 注意:
     - Payload 是 Base64 编码，不是加密（可以解码看到内容）
     - 不要在 token 里放敏感信息（密码、信用卡等）
     - 一旦签发，无法主动撤销（除非配合黑名单）

6. 【Token 使用流程】
   登录:
     POST /api/v1/auth/login
     { "username": "alice", "password": "123456" }
     ↓
     返回: { "access_token": "eyJ...", "token_type": "bearer" }

   前端存储:
     localStorage.setItem('token', access_token)

   访问需要认证的接口:
     GET /api/v1/users/me
     Headers: { Authorization: "Bearer eyJ..." }
     ↓
     后端验证 token → 返回用户信息

   登出:
     前端: localStorage.removeItem('token')
     后端: 不需要做任何事（JWT 是无状态的）

7. 【Refresh Token（可选，进阶）】
   为了安全，Access Token 过期时间短（15-30分钟）
   但频繁登录用户体验不好

   解决方案：
     - Access Token: 短期（30分钟）
     - Refresh Token: 长期（7天）

   流程：
     1. 登录返回两个 token
     2. 用 Access Token 访问 API
     3. Access Token 过期后，用 Refresh Token 换新的 Access Token
     4. Refresh Token 过期后才需要重新登录

8. 【实际使用示例】

   # 用户注册
   password = "123456"
   hashed_password = hash_password(password)
   user = User(username="alice", hashed_password=hashed_password)
   await db.add(user)
   await db.commit()

   # 用户登录
   if verify_password(input_password, user.hashed_password):
       token = create_access_token({"sub": str(user.id)})
       return {"access_token": token, "token_type": "bearer"}

   # 验证用户身份
   user_id = get_user_id_from_token(token)
   if user_id:
       user = await get_user(user_id)
   else:
       raise AuthenticationException(ErrorCode.TOKEN_INVALID)
"""
