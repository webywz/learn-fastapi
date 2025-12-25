"""
===========================================
认证路由 (Authentication Routes)
===========================================

作用：
  处理用户注册、登录等认证相关的 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import create_access_token
from schemas.user import UserCreate, UserLogin, Token, User as UserSchema
from services.user_service import UserService
from common.response import success
from common.exceptions import BusinessException
from common.error_codes import ErrorCode

router = APIRouter()


@router.post("/register", summary="用户注册")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册接口

    请求示例:
        POST /api/v1/auth/register
        {
            "username": "alice",
            "email": "alice@example.com",
            "password": "123456"
        }

    响应示例:
        {
            "code": 0,
            "message": "注册成功",
            "data": {
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                ...
            }
        }
    """
    # 创建用户（Service 层会检查用户名和邮箱是否存在）
    user = await UserService.create_user(db, user_data)

    # 返回成功响应
    return success(data=UserSchema.from_orm(user), message="注册成功")


@router.post("/login", summary="用户登录")
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录接口

    请求示例:
        POST /api/v1/auth/login
        {
            "username": "alice",
            "password": "123456"
        }

    响应示例:
        {
            "code": 0,
            "message": "登录成功",
            "data": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer"
            }
        }
    """
    # 验证用户名和密码
    user = await UserService.authenticate_user(
        db,
        login_data.username,
        login_data.password
    )

    if not user:
        raise BusinessException(
            ErrorCode.INVALID_USERNAME_OR_PASSWORD,
            message="用户名或密码错误"
        )

    # 生成 access token
    access_token = create_access_token(data={"sub": str(user.id)})

    # 返回 token
    token_data = Token(access_token=access_token, token_type="bearer")
    return success(data=token_data, message="登录成功")
