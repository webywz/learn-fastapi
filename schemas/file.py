from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FileRecord(BaseModel):
    id: int
    owner_id: int
    filename: str
    saved_filename: str
    content_type: str
    size: int
    storage: str
    visibility: str
    file_path: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    url: str

    model_config = ConfigDict(from_attributes=True)


class FileVisibilityUpdate(BaseModel):
    visibility: str


class FileShareCreate(BaseModel):
    expires_minutes: int = Field(default=60, ge=1, le=10080)


class FileShareLink(BaseModel):
    id: int
    file_id: int
    filename: str
    saved_filename: str
    token: str
    share_url: str
    expires_at: datetime
    status: str


class FileShareRecord(BaseModel):
    id: int
    file_id: int
    filename: str
    saved_filename: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    access_count: int
    last_accessed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    status: str
    is_active: bool
    share_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FileAuditRecord(BaseModel):
    id: int
    file_id: int
    owner_id: int
    actor_user_id: int
    event_type: str
    detail: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChunkedUploadInitRequest(BaseModel):
    """
    创建分片会话。

    只传元数据，不传文件本体。客户端按返回的 chunk_size / total_chunks 去切文件。
    """

    filename: str = Field(..., min_length=1, max_length=255, examples=["lecture.txt"])
    content_type: str = Field(..., min_length=1, max_length=100, examples=["text/plain"])
    total_size: int = Field(..., ge=1, description="完整文件字节数")
    chunk_size: Optional[int] = Field(
        None,
        ge=1,
        description="每片字节数；不传则用服务端默认。最后一片可以更小。",
    )
    checksum: Optional[str] = Field(
        None,
        description="可选：整个文件的 SHA-256 hex，complete 时核对",
        examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    )


class ChunkedUploadCompleteRequest(BaseModel):
    """拼片收尾。checksum 可省略（若 init 时已经给过）。"""

    checksum: Optional[str] = Field(
        None,
        description="可选：整个文件的 SHA-256 hex；与 init 同时给时必须一致",
    )


class ChunkedPartInfo(BaseModel):
    part_number: int
    size: int
    checksum: str
    reused: bool = False


class ChunkedUploadSessionRecord(BaseModel):
    upload_id: str
    filename: str
    content_type: str
    total_size: int
    chunk_size: int
    total_chunks: int
    status: str
    checksum: Optional[str] = None
    expires_at: datetime
    uploaded_parts: list[ChunkedPartInfo]
    missing_parts: list[int]
    file_id: Optional[int] = None
    saved_filename: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
