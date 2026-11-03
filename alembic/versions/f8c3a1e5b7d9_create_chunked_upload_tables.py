"""Create chunked upload session tables

Revision ID: f8c3a1e5b7d9
Revises: e4f7a9b2c6d1
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8c3a1e5b7d9"
down_revision: Union[str, Sequence[str], None] = "e4f7a9b2c6d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_upload_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="会话主键"),
        sa.Column(
            "upload_id",
            sa.String(length=36),
            nullable=False,
            comment="对外暴露的上传会话 ID（UUID）",
        ),
        sa.Column("owner_id", sa.Integer(), nullable=False, comment="发起上传的用户 ID"),
        sa.Column("filename", sa.String(length=255), nullable=False, comment="原始文件名"),
        sa.Column("content_type", sa.String(length=100), nullable=False, comment="文件 MIME 类型"),
        sa.Column("total_size", sa.Integer(), nullable=False, comment="完整文件大小（字节）"),
        sa.Column(
            "chunk_size",
            sa.Integer(),
            nullable=False,
            comment="约定的分片大小（最后一片可以更小）",
        ),
        sa.Column("total_chunks", sa.Integer(), nullable=False, comment="分片总数"),
        sa.Column(
            "checksum",
            sa.String(length=64),
            nullable=True,
            comment="可选：整个文件的 SHA-256 hex，complete 时核对",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="pending / completed / aborted / expired",
        ),
        sa.Column("file_id", sa.Integer(), nullable=True, comment="完成后对应的 files.id"),
        sa.Column("saved_filename", sa.String(length=255), nullable=True, comment="完成后的存储文件名"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, comment="过期时间，超过后临时分片可被清理"),
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
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_file_upload_sessions_expires_at"), "file_upload_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_file_upload_sessions_file_id"), "file_upload_sessions", ["file_id"], unique=False)
    op.create_index(op.f("ix_file_upload_sessions_id"), "file_upload_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_file_upload_sessions_owner_id"), "file_upload_sessions", ["owner_id"], unique=False)
    op.create_index(op.f("ix_file_upload_sessions_status"), "file_upload_sessions", ["status"], unique=False)
    op.create_index(op.f("ix_file_upload_sessions_upload_id"), "file_upload_sessions", ["upload_id"], unique=True)

    op.create_table(
        "file_upload_parts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="分片记录 ID"),
        sa.Column("session_id", sa.Integer(), nullable=False, comment="所属会话 ID"),
        sa.Column("part_number", sa.Integer(), nullable=False, comment="分片序号（从 1 开始，和 S3 Multipart 一样）"),
        sa.Column("size", sa.Integer(), nullable=False, comment="本片实际字节数"),
        sa.Column("checksum", sa.String(length=64), nullable=False, comment="本片 SHA-256 hex"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="首次写入时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="覆盖重传时间",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["file_upload_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "part_number", name="uq_upload_parts_session_part"),
    )
    op.create_index(op.f("ix_file_upload_parts_id"), "file_upload_parts", ["id"], unique=False)
    op.create_index(op.f("ix_file_upload_parts_session_id"), "file_upload_parts", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_file_upload_parts_session_id"), table_name="file_upload_parts")
    op.drop_index(op.f("ix_file_upload_parts_id"), table_name="file_upload_parts")
    op.drop_table("file_upload_parts")

    op.drop_index(op.f("ix_file_upload_sessions_upload_id"), table_name="file_upload_sessions")
    op.drop_index(op.f("ix_file_upload_sessions_status"), table_name="file_upload_sessions")
    op.drop_index(op.f("ix_file_upload_sessions_owner_id"), table_name="file_upload_sessions")
    op.drop_index(op.f("ix_file_upload_sessions_id"), table_name="file_upload_sessions")
    op.drop_index(op.f("ix_file_upload_sessions_file_id"), table_name="file_upload_sessions")
    op.drop_index(op.f("ix_file_upload_sessions_expires_at"), table_name="file_upload_sessions")
    op.drop_table("file_upload_sessions")
