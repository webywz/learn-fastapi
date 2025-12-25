"""
===========================================
用户路由 (User Routes)
===========================================

作用：
  处理用户相关的 API（获取用户信息、更新用户等）
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.deps import get_current_user
from schemas.user import User as UserSchema, UserUpdate
from services.user_service import UserService
from models.user import User
from common.response import success

router = APIRouter()


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户的信息

    请求示例:
        GET /api/v1/users/me
        Headers: Authorization: Bearer <token>

    响应示例:
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
    """
    return success(data=UserSchema.from_orm(current_user))


@router.put("/me", summary="更新当前用户信息")
async def update_current_user_info(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新当前登录用户的信息

    请求示例:
        PUT /api/v1/users/me
        Headers: Authorization: Bearer <token>
        {
            "email": "newemail@example.com"
        }

    响应示例:
        {
            "code": 0,
            "message": "更新成功",
            "data": {
                "id": 1,
                "username": "alice",
                "email": "newemail@example.com",
                ...
            }
        }
    """
    # 更新用户信息
    updated_user = await UserService.update_user(db, current_user, user_data)

    return success(data=UserSchema.from_orm(updated_user), message="更新成功")


@router.get("/{user_id}", summary="根据ID获取用户信息")
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    根据用户 ID 获取用户信息（公开接口）

    请求示例:
        GET /api/v1/users/1

    响应示例:
        {
            "code": 0,
            "message": "success",
            "data": {
                "id": 1,
                "username": "alice",
                ...
            }
        }
    """
    from common.exceptions import ResourceNotFoundException

    user = await UserService.get_user_by_id(db, user_id)

    if not user:
        raise ResourceNotFoundException(
            message=f"用户 ID {user_id} 不存在"
        )

    return success(data=UserSchema.from_orm(user))
