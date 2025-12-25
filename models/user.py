"""
===========================================
用户数据库模型 (User Model)
===========================================

作用：
  定义用户表的结构（ORM 模型）

什么是 ORM？
  Object-Relational Mapping（对象关系映射）
  - 用 Python 类表示数据库表
  - 用类属性表示表字段
  - 用对象实例表示表记录

类比前端：
  - 类似 TypeScript 的 interface
  - 或者 Prisma 的 schema
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from core.database import Base
class User(Base):
    """
    用户模型

    对应数据库中的 users 表

    字段说明:
        id: 主键，自动递增
        username: 用户名，唯一，最长50字符
        email: 邮箱，唯一，最长100字符
        hashed_password: 加密后的密码
        is_active: 是否激活（可用于软删除或禁用用户）
        is_superuser: 是否是超级管理员
        created_at: 创建时间，自动设置
        updated_at: 更新时间，自动更新

    使用示例:
        # 创建用户
        user = User(
            username="alice",
            email="alice@example.com",
            hashed_password="$2b$12$...",
            is_active=True
        )
        db.add(user)
        await db.commit()

        # 查询用户
        result = await db.execute(
            select(User).where(User.username == "alice")
        )
        user = result.scalar_one_or_none()

        # 更新用户
        user.email = "newemail@example.com"
        await db.commit()

        # 删除用户
        await db.delete(user)
        await db.commit()
    """

    __tablename__ = "users"

    # =========================================
    # 主键
    # =========================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="用户ID"
    )
    """
    主键字段

    - primary_key=True: 主键
    - index=True: 创建索引，查询更快
    - autoincrement=True: 自动递增
    """

    # =========================================
    # 认证信息
    # =========================================

    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名"
    )
    """
    用户名

    - String(50): 最长50个字符
    - unique=True: 唯一约束（不能重复）
    - nullable=False: 不能为空（必填）
    - index=True: 创建索引（经常用于查询）
    """

    email = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱"
    )
    """邮箱地址"""

    hashed_password = Column(
        String(255),
        nullable=False,
        comment="加密后的密码"
    )
    """
    加密后的密码

    注意：
    - 存储的是加密后的密码，不是明文
    - bcrypt 加密后大约 60 个字符
    - 设置 255 是为了兼容其他加密算法
    """

    phone = Column(
        String(20),
        nullable=True,
        index=True,
        comment="手机号码"
    )
    """手机号码（可选）"""

    # =========================================
    # 状态字段
    # =========================================

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否激活"
    )
    """
    是否激活

    用途：
    - 软删除：不直接删除用户，而是设置为 False
    - 禁用用户：管理员可以禁用某个用户
    """

    is_superuser = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否是超级管理员"
    )
    """是否是超级管理员（拥有所有权限）"""

    # =========================================
    # 时间字段
    # =========================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    """
    创建时间

    - DateTime(timezone=True): 带时区的时间
    - server_default=func.now(): 数据库自动设置当前时间
    - 创建记录时自动设置，不需要手动赋值
    """

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )
    """
    更新时间

    - onupdate=func.now(): 更新记录时自动更新为当前时间
    """

    def __repr__(self) -> str:
        """
        对象的字符串表示

        方便调试时查看对象信息

        示例:
            user = User(username="alice", email="alice@example.com")
            print(user)  # <User(id=1, username='alice', email='alice@example.com')>
        """
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结（给前端开发的你）：

1. 【ORM 模型 vs 数据库表】
   Python 类          →  数据库表
   类属性（Column）   →  表字段
   对象实例           →  表记录

   class User(Base):
       id = Column(Integer, primary_key=True)
       username = Column(String(50))

   ↓ 对应 SQL

   CREATE TABLE users (
       id INTEGER PRIMARY KEY,
       username VARCHAR(50)
   );

2. 【Column 参数】
   - primary_key: 主键
   - unique: 唯一约束（不能重复）
   - nullable: 是否可以为空（False表示必填）
   - index: 是否创建索引（加快查询速度）
   - default: 默认值
   - server_default: 数据库层面的默认值
   - onupdate: 更新时自动修改

3. 【数据类型】
   - Integer: 整数（对应数据库的 INT）
   - String(n): 字符串，最长 n 个字符（对应 VARCHAR(n)）
   - Boolean: 布尔值（对应 BOOLEAN 或 TINYINT）
   - DateTime: 日期时间（对应 DATETIME 或 TIMESTAMP）
   - Text: 长文本（对应 TEXT）
   - Float: 浮点数（对应 FLOAT）

4. 【索引（Index）】
   什么是索引？
     - 就像书的目录，帮助快速查找
     - 没有索引：从头到尾扫描整个表（慢）
     - 有索引：直接定位到数据（快）

   何时创建索引？
     - 经常用于查询的字段（username, email）
     - 唯一字段（unique=True 会自动创建索引）
     - 主键（primary_key=True 会自动创建索引）

   注意：
     - 索引加快查询，但会降低插入/更新速度
     - 不要给所有字段都创建索引

5. 【软删除 vs 硬删除】
   硬删除：
     DELETE FROM users WHERE id = 1;
     数据永久删除，无法恢复

   软删除：
     UPDATE users SET is_active = false WHERE id = 1;
     数据还在，只是标记为"已删除"

   软删除的好处：
     - 可以恢复
     - 保留历史记录
     - 外键关联不会出问题

6. 【时间字段】
   created_at（创建时间）：
     - 创建记录时自动设置
     - 以后不会改变

   updated_at（更新时间）：
     - 创建时设置为当前时间
     - 每次更新都会自动更新

   使用 func.now()：
     - 在数据库层面设置时间（而不是 Python）
     - 多个服务器时间一致（以数据库时间为准）

7. 【CRUD 操作示例】

   # Create（创建）
   user = User(username="alice", email="alice@example.com", hashed_password="...")
   db.add(user)
   await db.commit()
   await db.refresh(user)  # 刷新以获取数据库生成的 ID

   # Read（查询）
   # 查询所有
   result = await db.execute(select(User))
   users = result.scalars().all()

   # 按 ID 查询
   result = await db.execute(select(User).where(User.id == 1))
   user = result.scalar_one_or_none()

   # 按用户名查询
   result = await db.execute(select(User).where(User.username == "alice"))
   user = result.scalar_one_or_none()

   # 多条件查询
   result = await db.execute(
       select(User).where(User.is_active == True, User.is_superuser == False)
   )
   users = result.scalars().all()

   # Update（更新）
   user.email = "newemail@example.com"
   await db.commit()

   # Delete（删除）
   # 硬删除
   await db.delete(user)
   await db.commit()

   # 软删除
   user.is_active = False
   await db.commit()

8. 【与前端的对应关系】
   后端 ORM 模型   →   前端 TypeScript Interface

   # 后端（Python）
   class User(Base):
       id = Column(Integer)
       username = Column(String)
       email = Column(String)

   // 前端（TypeScript）
   interface User {
       id: number;
       username: string;
       email: string;
   }
"""
