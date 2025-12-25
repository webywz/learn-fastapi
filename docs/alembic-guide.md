# Alembic 数据库迁移完整指南

## 什么是 Alembic？

Alembic 是 SQLAlchemy 的数据库迁移工具，类似于前端的数据库 schema 版本管理工具。

**类比前端**：
- 就像 Git 管理代码版本
- Alembic 管理数据库结构（schema）版本

## 为什么需要数据库迁移？

### ❌ 没有迁移工具的问题
```python
# 开发阶段：手动创建表
Base.metadata.create_all(bind=engine)

# 问题：
# 1. 修改模型后，怎么更新已有数据库？
# 2. 团队成员的数据库结构不一致
# 3. 线上数据库怎么安全升级？
# 4. 出问题了怎么回滚？
```

### ✅ 使用迁移工具的好处
- 记录每次数据库结构变更
- 可以升级（upgrade）和回滚（downgrade）
- 团队协作时保持数据库一致
- 自动生成迁移代码

---

## 项目配置

### 1. 配置说明

已经配置好的文件：

#### `alembic/env.py` (核心配置)
```python
# 自动导入所有模型
from models.user import User

# 设置 metadata
target_metadata = Base.metadata

# 数据库 URL 从配置文件读取
database_url = settings.DATABASE_URL
```

#### `alembic.ini`
数据库 URL 从 `.env` 文件读取，无需修改此文件。

---

## 常用命令

### 1. 初始化 Alembic（已完成）
```bash
alembic init alembic
```

### 2. 🔥 自动生成迁移文件（最常用）
```bash
# 自动检测模型变化并生成迁移
alembic revision --autogenerate -m "描述你的修改"

# 示例：
alembic revision --autogenerate -m "Add phone field to users"
alembic revision --autogenerate -m "Create products table"
alembic revision --autogenerate -m "Add index on user email"
```

**工作流程**：
1. 修改你的模型（如 `models/user.py`）
2. 运行 `alembic revision --autogenerate -m "描述"`
3. Alembic 自动检测变化并生成迁移文件
4. 查看生成的文件，确认无误
5. 执行迁移

### 3. 执行迁移
```bash
# 升级到最新版本
alembic upgrade head

# 升级到指定版本
alembic upgrade <revision_id>

# 升级一个版本
alembic upgrade +1

# 升级两个版本
alembic upgrade +2
```

### 4. 回滚迁移
```bash
# 回滚到上一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision_id>

# 回滚所有迁移（清空数据库）
alembic downgrade base
```

### 5. 查看迁移状态
```bash
# 查看当前数据库版本
alembic current

# 查看迁移历史
alembic history

# 查看详细历史（包括描述）
alembic history --verbose
```

### 6. 手动创建迁移（不推荐）
```bash
# 创建空白迁移文件（需要手动编写迁移代码）
alembic revision -m "描述"
```

---

## 完整工作流程

### 场景 1：第一次使用 Alembic

```bash
# 1. 初始化（已完成）
alembic init alembic

# 2. 配置 env.py（已完成）

# 3. 生成初始迁移
alembic revision --autogenerate -m "Initial migration"

# 4. 执行迁移
alembic upgrade head

# 5. 查看当前版本
alembic current
```

### 场景 2：修改模型并更新数据库

```bash
# 1. 修改模型文件
# 例如：在 models/user.py 中添加 phone 字段

# 2. 自动生成迁移
alembic revision --autogenerate -m "Add phone field to users"

# 3. 查看生成的迁移文件
# alembic/versions/xxx_add_phone_field_to_users.py

# 4. 确认无误后执行迁移
alembic upgrade head

# 5. 验证
alembic current
alembic history
```

### 场景 3：回滚错误的迁移

```bash
# 1. 发现问题，回滚到上一个版本
alembic downgrade -1

# 2. 修改模型或迁移文件

# 3. 重新生成或执行迁移
alembic upgrade head
```

### 场景 4：团队协作

```bash
# 1. 拉取最新代码（包含新的迁移文件）
git pull

# 2. 查看有哪些新迁移
alembic history

# 3. 执行所有新迁移
alembic upgrade head

# 4. 确认数据库已更新
alembic current
```

---

## 迁移文件结构

生成的迁移文件示例：

```python
"""Add phone field to users table

Revision ID: 3d5094cfc2ce
Revises: 8e5c0fc340f2
Create Date: 2025-12-25 16:12:41.242419
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '3d5094cfc2ce'  # 当前版本号
down_revision: Union[str, None] = '8e5c0fc340f2'  # 上一个版本号

def upgrade() -> None:
    """升级数据库（应用迁移）"""
    # 添加列
    op.add_column('users', sa.Column('phone', sa.String(20)))
    # 创建索引
    op.create_index('ix_users_phone', 'users', ['phone'])

def downgrade() -> None:
    """降级数据库（回滚迁移）"""
    # 删除索引
    op.drop_index('ix_users_phone', table_name='users')
    # 删除列
    op.drop_column('users', 'phone')
```

### 迁移文件字段说明

- **revision**: 当前迁移的唯一标识
- **down_revision**: 依赖的上一个迁移（形成迁移链）
- **upgrade()**: 升级操作（应用变更）
- **downgrade()**: 降级操作（撤销变更）

---

## 常用迁移操作

### 1. 添加列
```python
def upgrade():
    op.add_column('users', sa.Column('nickname', sa.String(50)))

def downgrade():
    op.drop_column('users', 'nickname')
```

### 2. 删除列
```python
def upgrade():
    op.drop_column('users', 'old_field')

def downgrade():
    op.add_column('users', sa.Column('old_field', sa.String(50)))
```

### 3. 修改列
```python
def upgrade():
    # 修改列类型
    op.alter_column('users', 'username',
                    type_=sa.String(100),  # 原来是 50
                    existing_type=sa.String(50))

def downgrade():
    op.alter_column('users', 'username',
                    type_=sa.String(50),
                    existing_type=sa.String(100))
```

### 4. 创建表
```python
def upgrade():
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('price', sa.Float(), nullable=False)
    )

def downgrade():
    op.drop_table('products')
```

### 5. 创建/删除索引
```python
def upgrade():
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

def downgrade():
    op.drop_index('ix_users_email', table_name='users')
```

### 6. 添加外键
```python
def upgrade():
    op.add_column('posts', sa.Column('user_id', sa.Integer()))
    op.create_foreign_key(
        'fk_posts_user_id',  # 外键名称
        'posts',             # 源表
        'users',             # 目标表
        ['user_id'],         # 源列
        ['id']               # 目标列
    )

def downgrade():
    op.drop_constraint('fk_posts_user_id', 'posts', type_='foreignkey')
    op.drop_column('posts', 'user_id')
```

---

## 重要注意事项

### ✅ 最佳实践

1. **每次修改模型后都生成迁移**
   ```bash
   # 修改模型后立即生成
   alembic revision --autogenerate -m "描述修改内容"
   ```

2. **提交前检查迁移文件**
   - 查看生成的 `upgrade()` 和 `downgrade()` 是否正确
   - 确保 `downgrade()` 能正确回滚

3. **有意义的迁移描述**
   ```bash
   # ✅ 好的描述
   alembic revision --autogenerate -m "Add phone and address to users"

   # ❌ 不好的描述
   alembic revision --autogenerate -m "update"
   ```

4. **在新增模型后必须导入**
   ```python
   # alembic/env.py
   from models.user import User
   from models.product import Product  # 新增模型要导入！
   ```

5. **迁移文件要提交到 Git**
   ```bash
   git add alembic/versions/
   git commit -m "Add migration for new phone field"
   ```

### ⚠️ 常见陷阱

1. **不要手动修改已执行的迁移文件**
   - 已经 `upgrade` 的迁移不要修改
   - 如果有问题，创建新的迁移来修复

2. **不要删除迁移文件**
   - 迁移文件形成链条，删除会破坏链条
   - 如果要撤销，使用 `downgrade` 而不是删除文件

3. **生产环境谨慎操作**
   ```bash
   # ⚠️ 生产环境操作前先备份数据库
   # ⚠️ 在测试环境先验证迁移
   # ⚠️ 准备好回滚方案

   # 生产环境执行
   alembic upgrade head
   ```

4. **自动生成不是 100% 准确**
   - 检查生成的迁移文件
   - 某些复杂变更可能需要手动调整
   - 特别是重命名操作（Alembic 会认为是删除+新增）

---

## 故障排除

### 问题 1：Alembic 没有检测到模型变化

**原因**：模型没有在 `env.py` 中导入

**解决**：
```python
# alembic/env.py
from models.user import User
from models.product import Product  # 确保导入所有模型
```

### 问题 2：数据库版本冲突

```bash
# 错误：FAILED: Multiple head revisions are present
```

**解决**：
```bash
# 查看冲突的版本
alembic heads

# 合并冲突（需要手动处理）
alembic merge <revision1> <revision2> -m "Merge branches"
```

### 问题 3：迁移执行失败

```bash
# 查看当前版本
alembic current

# 如果卡住了，手动标记版本
alembic stamp head  # 标记为最新版本（不执行迁移）
alembic stamp <revision_id>  # 标记为指定版本
```

### 问题 4：想重新开始

```bash
# 1. 删除数据库文件
rm tutorial.db

# 2. 删除所有迁移文件
rm alembic/versions/*.py

# 3. 重新生成初始迁移
alembic revision --autogenerate -m "Initial migration"

# 4. 执行迁移
alembic upgrade head
```

---

## 快速参考

| 命令 | 说明 |
|------|------|
| `alembic revision --autogenerate -m "描述"` | 自动生成迁移文件 |
| `alembic upgrade head` | 升级到最新版本 |
| `alembic downgrade -1` | 回滚一个版本 |
| `alembic current` | 查看当前版本 |
| `alembic history` | 查看迁移历史 |
| `alembic upgrade +1` | 升级一个版本 |
| `alembic downgrade base` | 回滚所有迁移 |
| `alembic stamp head` | 标记版本（不执行迁移） |

---

## 示例：完整的开发流程

```bash
# 1. 修改模型
# 在 models/user.py 中添加 phone 字段

# 2. 生成迁移
alembic revision --autogenerate -m "Add phone field to users"

# 3. 查看生成的文件
cat alembic/versions/xxx_add_phone_field_to_users.py

# 4. 执行迁移
alembic upgrade head

# 5. 验证
alembic current
alembic history

# 6. 提交到 Git
git add models/user.py
git add alembic/versions/xxx_add_phone_field_to_users.py
git commit -m "Add phone field to users table"
git push
```

---

## 总结

- ✅ 使用 `--autogenerate` 自动生成迁移
- ✅ 每次修改模型都创建迁移
- ✅ 迁移文件提交到版本控制
- ✅ 生产环境先测试再执行
- ✅ 保持迁移文件的完整性（不删除、不修改已执行的）

Alembic 是数据库版本管理的强大工具，用好它可以让数据库变更更加安全和可控！🚀
