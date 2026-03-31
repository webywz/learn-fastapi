"""Create files table

Revision ID: 6f3c5d4c8b21
Revises: 3d5094cfc2ce
Create Date: 2026-03-31 14:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f3c5d4c8b21"
down_revision: Union[str, Sequence[str], None] = "3d5094cfc2ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="文件ID"),
        sa.Column("owner_id", sa.Integer(), nullable=False, comment="上传者用户ID"),
        sa.Column("filename", sa.String(length=255), nullable=False, comment="原始文件名"),
        sa.Column("saved_filename", sa.String(length=255), nullable=False, comment="存储文件名"),
        sa.Column("content_type", sa.String(length=100), nullable=False, comment="文件MIME类型"),
        sa.Column("size", sa.Integer(), nullable=False, comment="文件大小（字节）"),
        sa.Column(
            "storage",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'local'"),
            comment="存储方式（local/oss）",
        ),
        sa.Column("file_path", sa.String(length=500), nullable=False, comment="文件访问路径或URL"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="更新时间",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_files_id"), "files", ["id"], unique=False)
    op.create_index(op.f("ix_files_owner_id"), "files", ["owner_id"], unique=False)
    op.create_index(op.f("ix_files_saved_filename"), "files", ["saved_filename"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_files_saved_filename"), table_name="files")
    op.drop_index(op.f("ix_files_owner_id"), table_name="files")
    op.drop_index(op.f("ix_files_id"), table_name="files")
    op.drop_table("files")
