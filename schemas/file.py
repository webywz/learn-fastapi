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
