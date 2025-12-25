# SQLAlchemy ORM 方法完全手册

## 📚 目录
1. [查询构建方法](#查询构建方法)
2. [结果获取方法](#结果获取方法)
3. [过滤和条件方法](#过滤和条件方法)
4. [排序和分页方法](#排序和分页方法)
5. [增删改方法](#增删改方法)
6. [关系和连接查询](#关系和连接查询)

---

## 查询构建方法

### `select(Model)`
**作用**: 创建一个 SELECT 查询语句

**返回**: Select 对象（查询语句，还未执行）

**使用场景**: 所有查询的起点

```python
from sqlalchemy import select
from models.user import User

# 创建查询语句
stmt = select(User)
# 等同于 SQL: SELECT * FROM users

# 查询特定字段
stmt = select(User.id, User.username)
# 等同于 SQL: SELECT id, username FROM users
```

---

### `db.execute(statement)`
**作用**: 执行查询语句

**参数**:
- `statement`: 查询语句（select、update、delete 等）

**返回**: Result 对象（查询结果）

**使用场景**: 执行所有数据库操作

```python
# 1. 执行查询
stmt = select(User)
result = await db.execute(stmt)  # 返回 Result 对象

# 2. 执行更新
from sqlalchemy import update
stmt = update(User).where(User.id == 1).values(username="new_name")
await db.execute(stmt)

# 3. 执行删除
from sqlalchemy import delete
stmt = delete(User).where(User.id == 1)
await db.execute(stmt)
```

---

## 结果获取方法

### `result.scalar_one_or_none()`
**作用**: 获取单个对象，如果没有则返回 None

**返回**:
- 找到：返回对象
- 没找到：返回 None
- 找到多个：抛出异常

**使用场景**: 查询单个用户、根据唯一字段查询

```python
# 场景1: 根据 ID 查询用户
result = await db.execute(select(User).where(User.id == 1))
user = result.scalar_one_or_none()
# user = User 对象 或 None

# 场景2: 根据唯一字段查询
result = await db.execute(select(User).where(User.username == "alice"))
user = result.scalar_one_or_none()

# ✅ 推荐使用场景：
# - 根据主键（ID）查询
# - 根据唯一字段（username、email）查询
# - 你期望只有 0 或 1 个结果

# ❌ 不要用在可能返回多个结果的查询
# result = await db.execute(select(User).where(User.is_active == True))
# user = result.scalar_one_or_none()  # 如果有多个活跃用户，会抛异常！
```

---

### `result.scalar_one()`
**作用**: 获取单个对象，如果没有则抛出异常

**返回**:
- 找到：返回对象
- 没找到：抛出 NoResultFound 异常
- 找到多个：抛出 MultipleResultsFound 异常

**使用场景**: 你确定结果一定存在的情况

```python
# 场景: 获取当前登录用户（已通过认证，一定存在）
result = await db.execute(select(User).where(User.id == current_user_id))
user = result.scalar_one()  # 如果不存在会抛异常

# 对比 scalar_one_or_none()：
# scalar_one()          → 找不到会报错（用于必须存在的情况）
# scalar_one_or_none()  → 找不到返回 None（用于可能不存在的情况）
```

---

### `result.scalars()`
**作用**: 返回一个可迭代对象，用于获取多个结果

**返回**: ScalarResult 对象

**使用场景**: 需要进一步处理结果（调用 .all(), .first() 等）

```python
result = await db.execute(select(User))
scalars_result = result.scalars()  # ScalarResult 对象

# 通常配合其他方法使用：
users = scalars_result.all()    # 获取所有
user = scalars_result.first()   # 获取第一个
```

---

### `result.scalars().all()`
**作用**: 获取所有查询结果（列表）

**返回**: 对象列表 `[User, User, User, ...]`

**使用场景**: 查询多个用户、列表数据

```python
# 场景1: 获取所有用户
result = await db.execute(select(User))
users = result.scalars().all()
# users = [User(id=1), User(id=2), User(id=3)]

# 场景2: 获取所有活跃用户
result = await db.execute(select(User).where(User.is_active == True))
active_users = result.scalars().all()

# 场景3: 分页查询
result = await db.execute(
    select(User).offset(0).limit(10)
)
first_page_users = result.scalars().all()

# ⚠️ 注意：
# - 如果结果很多，会一次性加载到内存
# - 如果数据量大，考虑分页或流式处理
```

---

### `result.scalars().first()`
**作用**: 获取第一个结果

**返回**:
- 有结果：返回第一个对象
- 没结果：返回 None

**使用场景**: 只需要第一个结果，或检查是否存在

```python
# 场景1: 获取第一个用户
result = await db.execute(select(User).order_by(User.created_at))
first_user = result.scalars().first()

# 场景2: 检查是否存在
result = await db.execute(select(User).where(User.username == "alice"))
exists = result.scalars().first() is not None

# first() vs scalar_one_or_none():
# first()              → 返回第一个，即使有多个也不报错
# scalar_one_or_none() → 有多个会报错
```

---

### `result.scalar()`
**作用**: 获取查询结果的第一行第一列

**返回**: 单个值（不是对象）

**使用场景**: 查询单个字段值、COUNT 等聚合函数

```python
from sqlalchemy import func

# 场景1: 查询总数
result = await db.execute(select(func.count()).select_from(User))
total = result.scalar()  # 100 (数字，不是对象)

# 场景2: 查询单个字段值
result = await db.execute(select(User.username).where(User.id == 1))
username = result.scalar()  # "alice" (字符串)

# 场景3: 检查是否存在（返回 True/False）
result = await db.execute(
    select(func.count()).select_from(User).where(User.username == "alice")
)
exists = result.scalar() > 0  # True
```

---

## 过滤和条件方法

### `where(条件)`
**作用**: 添加 WHERE 条件

**参数**: 条件表达式

**返回**: 新的查询对象（可以链式调用）

**使用场景**: 筛选数据

```python
# 1. 等于
select(User).where(User.id == 1)
# SQL: WHERE id = 1

# 2. 不等于
select(User).where(User.id != 1)
# SQL: WHERE id != 1

# 3. 大于/小于
select(User).where(User.age > 18)
select(User).where(User.age >= 18)
select(User).where(User.age < 60)
select(User).where(User.age <= 60)

# 4. IN 查询
select(User).where(User.id.in_([1, 2, 3]))
# SQL: WHERE id IN (1, 2, 3)

# 5. NOT IN
select(User).where(User.id.not_in([1, 2, 3]))
# SQL: WHERE id NOT IN (1, 2, 3)

# 6. LIKE 模糊查询
select(User).where(User.username.like("%alice%"))
# SQL: WHERE username LIKE '%alice%'

# 7. IS NULL
select(User).where(User.phone.is_(None))
# SQL: WHERE phone IS NULL

# 8. IS NOT NULL
select(User).where(User.phone.is_not(None))
# SQL: WHERE phone IS NOT NULL

# 9. BETWEEN
from sqlalchemy import between
select(User).where(between(User.age, 18, 60))
# SQL: WHERE age BETWEEN 18 AND 60
```

---

### 多条件查询

```python
from sqlalchemy import and_, or_, not_

# AND 条件（多个条件都要满足）
# 方式1: 逗号分隔（推荐）
select(User).where(
    User.is_active == True,
    User.age >= 18
)
# SQL: WHERE is_active = true AND age >= 18

# 方式2: 使用 and_()
select(User).where(
    and_(
        User.is_active == True,
        User.age >= 18
    )
)

# OR 条件（任一条件满足即可）
select(User).where(
    or_(
        User.username == "alice",
        User.email == "alice@example.com"
    )
)
# SQL: WHERE username = 'alice' OR email = 'alice@example.com'

# NOT 条件
select(User).where(
    not_(User.is_active == False)
)
# SQL: WHERE NOT (is_active = false)

# 复杂组合
select(User).where(
    and_(
        User.is_active == True,
        or_(
            User.age >= 18,
            User.is_superuser == True
        )
    )
)
# SQL: WHERE is_active = true AND (age >= 18 OR is_superuser = true)
```

---

## 排序和分页方法

### `order_by(字段)`
**作用**: 排序

**参数**: 排序字段

**使用场景**: 按时间、名称等排序

```python
# 1. 升序（默认）
select(User).order_by(User.username)
# SQL: ORDER BY username ASC

# 2. 降序
select(User).order_by(User.created_at.desc())
# SQL: ORDER BY created_at DESC

# 3. 多字段排序
select(User).order_by(
    User.is_active.desc(),  # 先按是否激活降序
    User.created_at.desc()  # 再按创建时间降序
)
# SQL: ORDER BY is_active DESC, created_at DESC

# 使用场景：
# - 最新用户: order_by(User.created_at.desc())
# - 按字母排序: order_by(User.username)
# - VIP用户优先: order_by(User.is_vip.desc(), User.created_at.desc())
```

---

### `limit(数量)`
**作用**: 限制返回数量

**参数**: 整数（返回多少条）

**使用场景**: 分页、获取前N条

```python
# 获取前10个用户
select(User).limit(10)
# SQL: LIMIT 10

# 获取最新的5个用户
select(User).order_by(User.created_at.desc()).limit(5)
```

---

### `offset(数量)`
**作用**: 跳过前N条记录

**参数**: 整数（跳过多少条）

**使用场景**: 分页

```python
# 跳过前10条
select(User).offset(10)
# SQL: OFFSET 10

# 分页实现
page = 2
page_size = 10
offset = (page - 1) * page_size  # (2-1) * 10 = 10

select(User).offset(offset).limit(page_size)
# SQL: LIMIT 10 OFFSET 10  (返回第11-20条)

# 完整分页函数
async def get_users_page(db: AsyncSession, page: int = 1, page_size: int = 10):
    offset = (page - 1) * page_size

    # 查询数据
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    users = result.scalars().all()

    # 查询总数
    count_result = await db.execute(
        select(func.count()).select_from(User)
    )
    total = count_result.scalar()

    return users, total
```

---

## 增删改方法

### `db.add(对象)`
**作用**: 添加对象到会话（准备插入数据库）

**参数**: ORM 对象

**使用场景**: 创建新记录

```python
# 创建单个用户
user = User(username="alice", email="alice@example.com")
db.add(user)
await db.commit()  # 真正保存到数据库

# 批量创建
users = [
    User(username="alice", email="alice@example.com"),
    User(username="bob", email="bob@example.com"),
]
db.add_all(users)
await db.commit()
```

---

### `db.commit()`
**作用**: 提交事务（保存所有更改）

**使用场景**: 所有增删改操作后

```python
# 创建
user = User(username="alice")
db.add(user)
await db.commit()  # INSERT 语句在这里执行

# 更新
user.email = "new@example.com"
await db.commit()  # UPDATE 语句在这里执行

# 删除
await db.delete(user)
await db.commit()  # DELETE 语句在这里执行
```

---

### `db.refresh(对象)`
**作用**: 从数据库重新加载对象

**使用场景**: 获取数据库自动生成的值（ID、时间戳等）

```python
# 创建用户
user = User(username="alice")
db.add(user)
print(user.id)  # None（还未保存）

await db.commit()
print(user.id)  # None（已保存，但对象未更新）

await db.refresh(user)
print(user.id)  # 1（从数据库重新加载）
print(user.created_at)  # 2024-01-01 12:00:00（数据库自动生成）
```

---

### `db.delete(对象)`
**作用**: 删除对象

**使用场景**: 删除记录

```python
# 删除单个用户
user = await get_user_by_id(db, 1)
if user:
    await db.delete(user)
    await db.commit()

# 注意：也可以用 delete 语句（不需要先查询）
from sqlalchemy import delete

stmt = delete(User).where(User.id == 1)
await db.execute(stmt)
await db.commit()
```

---

### `db.rollback()`
**作用**: 回滚事务（撤销所有未提交的更改）

**使用场景**: 发生错误时恢复

```python
try:
    user = User(username="alice")
    db.add(user)

    # 假设这里发生错误
    raise Exception("Something wrong")

    await db.commit()
except Exception as e:
    await db.rollback()  # 撤销所有更改
    raise e
```

---

## 聚合函数

### `func.count()`
**作用**: 计数

```python
from sqlalchemy import func

# 查询总用户数
result = await db.execute(
    select(func.count()).select_from(User)
)
total = result.scalar()  # 100

# 查询满足条件的数量
result = await db.execute(
    select(func.count()).select_from(User).where(User.is_active == True)
)
active_count = result.scalar()  # 80
```

---

### `func.max()`, `func.min()`, `func.avg()`, `func.sum()`
**作用**: 最大值、最小值、平均值、求和

```python
# 最大年龄
result = await db.execute(select(func.max(User.age)))
max_age = result.scalar()

# 最小年龄
result = await db.execute(select(func.min(User.age)))
min_age = result.scalar()

# 平均年龄
result = await db.execute(select(func.avg(User.age)))
avg_age = result.scalar()

# 总和（比如积分总和）
result = await db.execute(select(func.sum(User.points)))
total_points = result.scalar()
```

---

## 实用查询示例

### 1. 搜索功能
```python
async def search_users(db: AsyncSession, keyword: str):
    """根据关键词搜索用户"""
    result = await db.execute(
        select(User).where(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%")
            )
        )
    )
    return result.scalars().all()
```

---

### 2. 分页 + 搜索 + 排序
```python
async def get_users_advanced(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    order_by: str = "created_at"
):
    """高级用户查询"""
    # 构建基础查询
    query = select(User)

    # 添加搜索条件
    if keyword:
        query = query.where(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%")
            )
        )

    # 添加排序
    if order_by == "created_at":
        query = query.order_by(User.created_at.desc())
    elif order_by == "username":
        query = query.order_by(User.username)

    # 添加分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # 执行查询
    result = await db.execute(query)
    users = result.scalars().all()

    # 查询总数
    count_query = select(func.count()).select_from(User)
    if keyword:
        count_query = count_query.where(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%")
            )
        )
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return users, total
```

---

### 3. 检查是否存在
```python
async def username_exists(db: AsyncSession, username: str) -> bool:
    """检查用户名是否存在"""
    result = await db.execute(
        select(func.count()).select_from(User).where(User.username == username)
    )
    count = result.scalar()
    return count > 0

# 或者更简单的方式
async def username_exists_v2(db: AsyncSession, username: str) -> bool:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalars().first() is not None
```

---

### 4. 软删除查询
```python
# 只查询未删除的用户
async def get_active_users(db: AsyncSession):
    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    return result.scalars().all()

# 包括已删除的
async def get_all_users_including_deleted(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()
```

---

## 方法速查表

| 方法 | 返回值 | 使用场景 |
|------|--------|----------|
| `select(User)` | 查询语句 | 构建查询 |
| `db.execute(stmt)` | Result | 执行查询 |
| `scalar_one_or_none()` | 对象或None | 查询单个（可能不存在） |
| `scalar_one()` | 对象 | 查询单个（一定存在） |
| `scalars().all()` | 列表 | 查询多个 |
| `scalars().first()` | 对象或None | 获取第一个 |
| `scalar()` | 单个值 | 聚合函数、单字段 |
| `where()` | 查询语句 | 添加条件 |
| `order_by()` | 查询语句 | 排序 |
| `limit()` | 查询语句 | 限制数量 |
| `offset()` | 查询语句 | 跳过记录 |
| `db.add()` | 无 | 添加对象 |
| `db.commit()` | 无 | 提交事务 |
| `db.refresh()` | 无 | 重新加载对象 |
| `db.delete()` | 无 | 删除对象 |
| `db.rollback()` | 无 | 回滚事务 |
