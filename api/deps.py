"""
===========================================
依赖注入模块 (Dependencies)
===========================================

作用：
  提供可复用的依赖项（如获取当前用户）

什么是依赖注入？
  FastAPI 的核心特性之一
  - 自动管理依赖关系
  - 代码更简洁、可复用
  - 易于测试

类比前端：
  - 类似 React 的 Context + Hooks
  - 或者 Vue 的 provide/inject
"""

from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_user_id_from_token
from services.user_service import UserService
from models.user import User
from common.exceptions import AuthenticationException
from common.error_codes import ErrorCode

# HTTP Bearer 认证方案
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    获取当前登录用户

    从请求头的 Authorization 中获取 token，验证并返回用户对象

    参数:
        credentials: HTTP 认证凭证（自动从请求头获取）
        db: 数据库会话

    返回:
        User: 当前用户对象

    异常:
        AuthenticationException: Token 无效或用户不存在

    使用示例:
        @router.get("/users/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            # current_user 就是当前登录的用户
            return success(data=current_user)

    前端调用:
        axios.get('/api/v1/users/me', {
            headers: {
                Authorization: `Bearer ${token}`
            }
        })
    """
    # 获取 token
    token = credentials.credentials

    # 从 token 中解析用户 ID
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise AuthenticationException(
            ErrorCode.TOKEN_INVALID,
            message="Token 无效或已过期"
        )

    # 根据用户 ID 获取用户
    user = await UserService.get_user_by_id(db, user_id)
    if not user:
        raise AuthenticationException(
            ErrorCode.USER_NOT_FOUND,
            message="用户不存在"
        )

    # 检查用户是否被禁用
    if not user.is_active:
        raise AuthenticationException(
            ErrorCode.USER_DISABLED,
            message="用户已被禁用"
        )

    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前超级管理员用户

    用于需要管理员权限的接口

    参数:
        current_user: 当前用户（通过 get_current_user 获取）

    返回:
        User: 超级管理员用户

    异常:
        PermissionException: 不是超级管理员

    使用示例:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: int,
            current_user: User = Depends(get_current_active_superuser)
        ):
            # 只有超级管理员才能删除用户
            ...
    """
    from common.exceptions import PermissionException

    if not current_user.is_superuser:
        raise PermissionException(
            ErrorCode.PERMISSION_DENIED,
            message="需要超级管理员权限"
        )

    return current_user


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【依赖注入（Dependency Injection）】
   不需要：
   @router.get("/users/me")
   async def get_me(request: Request):
       token = request.headers.get("Authorization")
       user_id = parse_token(token)
       db = get_database()
       user = db.query(User).filter(User.id == user_id).first()
       return user

   使用依赖注入：
   @router.get("/users/me")
   async def get_me(current_user: User = Depends(get_current_user)):
       return current_user  # FastAPI 自动处理所有逻辑

2. 【HTTPBearer】
   自动从请求头获取 Authorization: Bearer <token>

   security = HTTPBearer()

   @router.get("/")
   async def api(credentials: HTTPAuthorizationCredentials = Depends(security)):
       token = credentials.credentials  # 获取 token

3. 【依赖链】
   get_current_user
     → Depends(security)  # 获取 token
     → Depends(get_db)    # 获取数据库连接

   get_current_active_superuser
     → Depends(get_current_user)  # 先获取当前用户
     → 检查是否是超级管理员

4. 【实际使用示例】

   # 公开接口（不需要登录）
   @router.get("/public")
   async def public_api():
       return {"message": "这是公开接口"}

   # 需要登录的接口
   @router.get("/users/me")
   async def get_me(current_user: User = Depends(get_current_user)):
       return success(data=current_user)

   # 需要管理员权限的接口
   @router.delete("/users/{user_id}")
   async def delete_user(
       user_id: int,
       admin: User = Depends(get_current_active_superuser)
   ):
       # 只有管理员能执行
       ...
"""
