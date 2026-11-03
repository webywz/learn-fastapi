"""
===========================================
文件数据库模型 (File Model)
===========================================

作用：
  定义上传文件的元数据表结构

为什么需要文件表？
  1. 记录文件归属关系（谁上传的）
  2. 保存文件访问地址和存储方式
  3. 支持后续文件列表、详情、删除等功能
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class File(Base):
    """上传文件元数据模型"""

    __tablename__ = "files"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="文件ID",
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="上传者用户ID",
    )

    filename = Column(
        String(255),
        nullable=False,
        comment="原始文件名",
    )

    saved_filename = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="存储文件名",
    )

    content_type = Column(
        String(100),
        nullable=False,
        comment="文件MIME类型",
    )

    size = Column(
        Integer,
        nullable=False,
        comment="文件大小（字节）",
    )

    storage = Column(
        String(20),
        nullable=False,
        default="local",
        server_default=text("'local'"),
        comment="存储方式（local/oss）",
    )

    visibility = Column(
        String(20),
        nullable=False,
        default="private",
        server_default=text("'private'"),
        comment="可见性（private/public）",
    )

    file_path = Column(
        String(500),
        nullable=False,
        comment="文件访问路径或URL",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="软删除时间",
    )

    shares = relationship(
        "FileShare",
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    audit_logs = relationship(
        "FileAuditLog",
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<File(id={self.id}, owner_id={self.owner_id}, "
            f"filename='{self.filename}', storage='{self.storage}')>"
        )


class FileShare(Base):
    """文件分享链接模型"""

    __tablename__ = "file_shares"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="分享链接ID",
    )

    file_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文件ID",
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="分享者用户ID",
    )

    token_id = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="分享令牌唯一标识",
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="过期时间",
    )

    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="撤销时间",
    )

    access_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="访问次数",
    )

    last_accessed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后访问时间",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    file = relationship("File", back_populates="shares")

    def __repr__(self) -> str:
        return (
            f"<FileShare(id={self.id}, file_id={self.file_id}, "
            f"owner_id={self.owner_id}, token_id='{self.token_id[:8]}...')>"
        )


class FileAuditLog(Base):
    """文件审计日志模型"""

    __tablename__ = "file_audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="审计日志ID",
    )

    file_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文件ID",
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文件所有者用户ID",
    )

    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="执行操作的用户ID",
    )

    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="事件类型",
    )

    detail = Column(
        String(500),
        nullable=True,
        comment="事件详情",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    file = relationship("File", back_populates="audit_logs")

    def __repr__(self) -> str:
        return (
            f"<FileAuditLog(id={self.id}, file_id={self.file_id}, "
            f"event_type='{self.event_type}')>"
        )


class FileUploadSession(Base):
    """
    大文件分片上传会话

    为什么单独一张表，而不是只在磁盘上丢一堆 part_N.bin？
      1. 要知道是谁的会话（owner_id），别人不能续传你的片
      2. 要记录期望的 total_size / chunk_size / checksum，complete 时才能校验
      3. 要有 TTL（expires_at），否则放弃的上传会把磁盘撑满
      4. 续传时客户端问「我传了哪些片」，查表比扫目录稳

    状态机（status）：
      pending    → 正在传片
      completed  → 已拼好并写入 files 表（可幂等再 complete）
      aborted    → 用户主动取消，临时目录已删
      expired    → 超过 TTL，临时目录已删
    """

    __tablename__ = "file_upload_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="会话主键",
    )

    upload_id = Column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        comment="对外暴露的上传会话 ID（UUID）",
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="发起上传的用户 ID",
    )

    filename = Column(
        String(255),
        nullable=False,
        comment="原始文件名",
    )

    content_type = Column(
        String(100),
        nullable=False,
        comment="文件 MIME 类型",
    )

    total_size = Column(
        Integer,
        nullable=False,
        comment="完整文件大小（字节）",
    )

    chunk_size = Column(
        Integer,
        nullable=False,
        comment="约定的分片大小（最后一片可以更小）",
    )

    total_chunks = Column(
        Integer,
        nullable=False,
        comment="分片总数",
    )

    checksum = Column(
        String(64),
        nullable=True,
        comment="可选：整个文件的 SHA-256 hex，complete 时核对",
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        index=True,
        comment="pending / completed / aborted / expired",
    )

    file_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="完成后对应的 files.id",
    )

    saved_filename = Column(
        String(255),
        nullable=True,
        comment="完成后的存储文件名",
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="过期时间，超过后临时分片可被清理",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )

    parts = relationship(
        "FileUploadPart",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<FileUploadSession(upload_id='{self.upload_id}', "
            f"status='{self.status}', owner_id={self.owner_id})>"
        )


class FileUploadPart(Base):
    """
    已经落到磁盘的一片。

    (session_id, part_number) 唯一：同一片再传一次是幂等覆盖，不是插第二行。
    分片字节在临时目录，这里只存 size / checksum 方便 GET 续传列表。
    """

    __tablename__ = "file_upload_parts"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "part_number",
            name="uq_upload_parts_session_part",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="分片记录 ID",
    )

    session_id = Column(
        Integer,
        ForeignKey("file_upload_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话 ID",
    )

    part_number = Column(
        Integer,
        nullable=False,
        comment="分片序号（从 1 开始，和 S3 Multipart 一样）",
    )

    size = Column(
        Integer,
        nullable=False,
        comment="本片实际字节数",
    )

    checksum = Column(
        String(64),
        nullable=False,
        comment="本片 SHA-256 hex",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="首次写入时间",
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="覆盖重传时间",
    )

    session = relationship("FileUploadSession", back_populates="parts")

    def __repr__(self) -> str:
        return (
            f"<FileUploadPart(session_id={self.session_id}, "
            f"part_number={self.part_number}, size={self.size})>"
        )
