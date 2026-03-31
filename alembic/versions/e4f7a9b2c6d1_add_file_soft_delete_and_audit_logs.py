"""Add file soft delete and audit logs

Revision ID: e4f7a9b2c6d1
Revises: c2d4e6f8a1b3
Create Date: 2026-03-31 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f7a9b2c6d1"
down_revision: Union[str, Sequence[str], None] = "c2d4e6f8a1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="软删除时间",
        ),
    )
    op.create_index(op.f("ix_files_deleted_at"), "files", ["deleted_at"], unique=False)

    op.create_table(
        "file_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="审计日志ID"),
        sa.Column("file_id", sa.Integer(), nullable=False, comment="文件ID"),
        sa.Column("owner_id", sa.Integer(), nullable=False, comment="文件所有者用户ID"),
        sa.Column("actor_user_id", sa.Integer(), nullable=False, comment="执行操作的用户ID"),
        sa.Column("event_type", sa.String(length=50), nullable=False, comment="事件类型"),
        sa.Column("detail", sa.String(length=500), nullable=True, comment="事件详情"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="创建时间",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_audit_logs_actor_user_id"), "file_audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_file_audit_logs_event_type"), "file_audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_file_audit_logs_file_id"), "file_audit_logs", ["file_id"], unique=False)
    op.create_index(op.f("ix_file_audit_logs_id"), "file_audit_logs", ["id"], unique=False)
    op.create_index(op.f("ix_file_audit_logs_owner_id"), "file_audit_logs", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_file_audit_logs_owner_id"), table_name="file_audit_logs")
    op.drop_index(op.f("ix_file_audit_logs_id"), table_name="file_audit_logs")
    op.drop_index(op.f("ix_file_audit_logs_file_id"), table_name="file_audit_logs")
    op.drop_index(op.f("ix_file_audit_logs_event_type"), table_name="file_audit_logs")
    op.drop_index(op.f("ix_file_audit_logs_actor_user_id"), table_name="file_audit_logs")
    op.drop_table("file_audit_logs")

    op.drop_index(op.f("ix_files_deleted_at"), table_name="files")
    op.drop_column("files", "deleted_at")
