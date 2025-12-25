from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ============================================================
# 导入项目模块以支持自动生成迁移
# ============================================================
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 导入数据库配置和所有模型
from core.database import Base
from core.config import settings

# 重要: 必须导入所有模型，否则 autogenerate 检测不到
from models.user import User

# 设置 target_metadata 为 Base.metadata
# 这样 Alembic 才能自动检测模型变化
target_metadata = Base.metadata

# ============================================================
# 配置数据库 URL（从 settings 读取）
# ============================================================
# 将异步数据库 URL 转换为同步 URL（Alembic 使用同步驱动）
database_url = settings.DATABASE_URL
# 替换异步驱动为同步驱动
database_url = database_url.replace("sqlite+aiosqlite://", "sqlite://")
database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
database_url = database_url.replace("mysql+aiomysql://", "mysql://")

config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
