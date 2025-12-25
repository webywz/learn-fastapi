"""
===========================================
用户业务逻辑层 (User Service)
===========================================

作用：
  处理用户相关的业务逻辑

为什么需要 Service 层？
  1. 分离关注点：API 层只负责接收请求，Service 层处理业务逻辑
  2. 代码复用：多个 API 可以调用同一个 Service 方法
  3. 易于测试：可以单独测试业务逻辑
  4. 易于维护：业务逻辑集中管理

架构分层：
  API 层（路由）→ Service 层（业务逻辑）→ Database 层（数据访问）
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from models.user import User
from schemas.user import UserCreate, UserUpdate
from core.security import hash_password, verify_password
from common.exceptions import BusinessException
from common.error_codes import ErrorCode
from utils.cache import cache, cache_invalidate, CacheManager
from core.redis import redis_cache


class UserService:
    """用户服务类"""

    @staticmethod
    @cache(ttl=600, key_prefix="user")
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """
        根据 ID 获取用户（带缓存）

        参数:
            db: 数据库会话
            user_id: 用户 ID

        返回:
            User: 用户对象
            None: 用户不存在

        缓存策略:
            - 缓存时间: 10 分钟
            - 缓存键: user:get_user_by_id:{user_id}
            - 第一次查询从数据库读取，结果缓存
            - 10 分钟内再次查询直接从 Redis 返回
        """
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """
        创建用户

        参数:
            db: 数据库会话
            user_data: 用户创建数据

        返回:
            User: 创建的用户对象

        异常:
            BusinessException: 用户名或邮箱已存在
        """
        # 检查用户名是否存在
        existing_user = await UserService.get_user_by_username(db, user_data.username)
        if existing_user:
            raise BusinessException(ErrorCode.USER_ALREADY_EXISTS)

        # 检查邮箱是否存在
        existing_email = await UserService.get_user_by_email(db, user_data.email)
        if existing_email:
            raise BusinessException(ErrorCode.EMAIL_ALREADY_EXISTS)

        # 创建用户
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            is_active=True,
            is_superuser=False
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
        """
        验证用户登录

        参数:
            db: 数据库会话
            username: 用户名
            password: 明文密码

        返回:
            User: 验证成功，返回用户对象
            None: 验证失败
        """
        user = await UserService.get_user_by_username(db, username)

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    @cache_invalidate("user:*")
    async def update_user(db: AsyncSession, user: User, user_data: UserUpdate) -> User:
        """
        更新用户信息（更新后自动清除缓存）

        参数:
            db: 数据库会话
            user: 用户对象
            user_data: 更新数据

        返回:
            User: 更新后的用户对象

        缓存处理:
            - 更新成功后，自动删除所有 user:* 的缓存
            - 下次查询会从数据库重新获取最新数据
        """
        # 只更新提供的字段
        if user_data.username is not None:
            # 检查新用户名是否已存在
            existing = await UserService.get_user_by_username(db, user_data.username)
            if existing and existing.id != user.id:
                raise BusinessException(ErrorCode.USER_ALREADY_EXISTS)
            user.username = user_data.username

        if user_data.email is not None:
            # 检查新邮箱是否已存在
            existing = await UserService.get_user_by_email(db, user_data.email)
            if existing and existing.id != user.id:
                raise BusinessException(ErrorCode.EMAIL_ALREADY_EXISTS)
            user.email = user_data.email

        if user_data.password is not None:
            user.hashed_password = hash_password(user_data.password)

        await db.commit()
        await db.refresh(user)

        return user


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【Service 层的职责】
   - 处理业务逻辑
   - 数据验证（业务规则层面）
   - 调用数据库操作
   - 抛出业务异常

2. 【为什么用静态方法 @staticmethod？】
   - 不需要实例化类
   - 方法不依赖类的状态
   - 类似工具函数的集合

   使用：
   user = await UserService.create_user(db, user_data)

3. 【错误处理】
   Service 层抛出 BusinessException
   全局异常处理器统一捕获并返回错误响应

4. 【实际使用示例】
   @router.post("/users")
   async def create_user_api(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
       user = await UserService.create_user(db, user_data)
       return success(data=user)
"""
