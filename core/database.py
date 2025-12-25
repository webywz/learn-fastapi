"""
===========================================
数据库配置模块 (Database Module)
===========================================

作用：
  配置数据库连接和会话管理

为什么需要这个模块？
  1. 统一管理数据库连接
  2. 提供数据库会话（Session）的创建和关闭
  3. 支持异步操作（FastAPI 是异步框架）

类比前端：
  - 类似 Axios 实例配置
  - 或者 Prisma Client 的初始化
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from .config import settings


# ============================================================
# 创建数据库引擎
# ============================================================

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,  # 是否打印 SQL 语句
    future=True,  # 使用 SQLAlchemy 2.0 风格
    pool_pre_ping=True,  # 每次从连接池取连接前先 ping 一下，确保连接有效
)
"""
数据库引擎（Engine）

什么是引擎？
  - 引擎是 SQLAlchemy 和数据库之间的桥梁
  - 负责管理数据库连接池
  - 类似前端的 HTTP Client 实例

参数说明:
  - url: 数据库连接字符串（从配置读取）
  - echo: True 会打印所有 SQL（调试用）
  - future: 使用 SQLAlchemy 2.0 的新 API
  - pool_pre_ping: 确保从连接池拿到的连接是活的
    （防止数据库长时间不用，连接被关闭）
"""


# ============================================================
# 创建会话工厂
# ============================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后对象不过期（可以继续访问属性）
    autoflush=False,  # 不自动 flush（手动控制更灵活）
    autocommit=False,  # 不自动提交（需要手动 commit）
)
"""
异步会话工厂

什么是 Session？
  - Session 是你和数据库交互的接口
  - 类似前端的一个 API 请求实例
  - 每次请求都应该有独立的 Session

为什么是 async？
  - FastAPI 是异步框架
  - 异步可以提高并发性能
  - 不会阻塞其他请求

参数说明:
  - bind: 绑定到哪个引擎
  - class_: 使用异步 Session
  - expire_on_commit: False 表示提交后还能访问对象属性
  - autoflush: False 手动控制何时 flush
  - autocommit: False 手动控制何时 commit
"""


# ============================================================
# 声明基类
# ============================================================

Base = declarative_base()
"""
ORM 模型基类

所有数据库模型都要继承这个类

使用示例:
    from core.database import Base
    from sqlalchemy import Column, Integer, String

    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)
        username = Column(String(50), unique=True)
"""


# ============================================================
# 依赖注入：获取数据库会话
# ============================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖注入函数

    这是 FastAPI 依赖注入的标准用法
    会在每个请求开始时创建 Session，结束时关闭

    为什么用 yield？
      - yield 之前的代码在请求开始时执行（创建 Session）
      - yield 之后的代码在请求结束时执行（关闭 Session）
      - 类似 React 的 useEffect cleanup 函数

    使用示例:
        from fastapi import Depends
        from core.database import get_db

        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            # 这里的 db 就是数据库会话
            result = await db.execute(select(User))
            users = result.scalars().all()
            return users

    执行流程:
        1. 请求开始 → 创建 Session
        2. 执行路由函数 → 使用 Session 查询数据库
        3. 请求结束 → 关闭 Session（即使出错也会关闭）
    """
    async with AsyncSessionLocal() as session:
        try:
            # yield 把 session 交给路由函数使用
            yield session
        finally:
            # 无论成功失败，最后都会关闭 session
            await session.close()


# ============================================================
# 数据库初始化函数
# ============================================================

async def init_db() -> None:
    """
    初始化数据库（创建所有表）

    何时调用？
      在应用启动时调用一次

    实际项目中通常用 Alembic 做数据库迁移
    这个函数适合开发环境快速测试

    使用示例（在 main.py）:
        from core.database import init_db

        @app.on_event("startup")
        async def startup():
            await init_db()
    """
    async with engine.begin() as conn:
        # 创建所有继承 Base 的模型对应的表
        await conn.run_sync(Base.metadata.create_all)


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结（给前端开发的你）：

1. 【Engine（引擎） vs Session（会话）】
   - Engine: 管理连接池，全局只需要一个
     类似：const axios = axios.create({ baseURL: '...' })

   - Session: 每次请求使用独立的 Session
     类似：每次 API 调用都是独立的

2. 【连接池（Connection Pool）】
   数据库连接很宝贵（建立连接慢）
   连接池预先创建一些连接，重复使用

   就像餐厅的座位：
   - 不用每次都搭建新座位
   - 客人来了分配一个座位
   - 客人走了座位释放给下一个客人

3. 【异步 (Async) 的好处】
   同步（Sync）: 等待数据库返回，期间不能处理其他请求
   异步（Async）: 等待数据库时可以处理其他请求

   类比前端：
   // 同步（会卡住）
   const data = fetchDataSync();  // 等 1 秒
   console.log('done');

   // 异步（不卡住）
   fetchDataAsync().then(data => {
     console.log(data);
   });
   console.log('done');  // 立即执行

4. 【依赖注入（Dependency Injection）】
   FastAPI 的核心特性

   不需要手动创建和关闭 Session：
   ❌ 手动方式:
   async def get_users():
       db = AsyncSessionLocal()
       try:
           users = await db.execute(select(User))
           return users
       finally:
           await db.close()  # 容易忘记！

   ✅ 依赖注入:
   async def get_users(db: AsyncSession = Depends(get_db)):
       users = await db.execute(select(User))
       return users  # FastAPI 自动关闭 Session

5. 【ORM（Object-Relational Mapping）】
   用面向对象的方式操作数据库

   不用写 SQL:
   ❌ 原生 SQL:
   SELECT * FROM users WHERE username = 'alice'

   ✅ ORM:
   db.query(User).filter(User.username == 'alice').first()

   好处：
   - 类型安全（IDE 有提示）
   - 防止 SQL 注入
   - 跨数据库（SQLite、PostgreSQL 等）

6. 【Session 生命周期】
   Request → 创建 Session → 执行查询 → 关闭 Session

   一个请求一个 Session，不要共享！

7. 【实际使用流程】

   # 1. 定义模型（models/user.py）
   class User(Base):
       __tablename__ = "users"
       id = Column(Integer, primary_key=True)
       username = Column(String(50))

   # 2. 在路由中使用（api/v1/users.py）
   @router.get("/users")
   async def get_users(db: AsyncSession = Depends(get_db)):
       result = await db.execute(select(User))
       users = result.scalars().all()
       return users

   # 3. 应用启动时初始化数据库（main.py）
   @app.on_event("startup")
   async def startup():
       await init_db()

8. 【常见数据库操作】

   # 查询所有
   result = await db.execute(select(User))
   users = result.scalars().all()

   # 查询单个
   result = await db.execute(select(User).where(User.id == 1))
   user = result.scalar_one_or_none()

   # 创建
   new_user = User(username="alice")
   db.add(new_user)
   await db.commit()
   await db.refresh(new_user)  # 刷新获取 ID

   # 更新
   user.username = "bob"
   await db.commit()

   # 删除
   await db.delete(user)
   await db.commit()
"""
