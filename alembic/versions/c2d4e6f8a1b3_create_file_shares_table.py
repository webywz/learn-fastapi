"""Create file shares table

Revision ID: c2d4e6f8a1b3
Revises: 91e4a2b7f6b0
Create Date: 2026-03-31 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d4e6f8a1b3"
down_revision: Union[str, Sequence[str], None] = "91e4a2b7f6b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_shares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="分享链接ID"),
        sa.Column("file_id", sa.Integer(), nullable=False, comment="文件ID"),
        sa.Column("owner_id", sa.Integer(), nullable=False, comment="分享者用户ID"),
        sa.Column("token_id", sa.String(length=64), nullable=False, comment="分享令牌唯一标识"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, comment="过期时间"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True, comment="撤销时间"),
        sa.Column(
            "access_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="访问次数",
        ),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True, comment="最后访问时间"),
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
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_shares_expires_at"), "file_shares", ["expires_at"], unique=False)
    op.create_index(op.f("ix_file_shares_file_id"), "file_shares", ["file_id"], unique=False)
    op.create_index(op.f("ix_file_shares_id"), "file_shares", ["id"], unique=False)
    op.create_index(op.f("ix_file_shares_owner_id"), "file_shares", ["owner_id"], unique=False)
    op.create_index(op.f("ix_file_shares_token_id"), "file_shares", ["token_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_file_shares_token_id"), table_name="file_shares")
    op.drop_index(op.f("ix_file_shares_owner_id"), table_name="file_shares")
    op.drop_index(op.f("ix_file_shares_id"), table_name="file_shares")
    op.drop_index(op.f("ix_file_shares_file_id"), table_name="file_shares")
    op.drop_index(op.f("ix_file_shares_expires_at"), table_name="file_shares")
    op.drop_table("file_shares")
