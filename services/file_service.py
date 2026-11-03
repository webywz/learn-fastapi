from datetime import datetime, timezone
from typing import Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.pagination import ListParams, PaginatedPage, apply_offset, compute_offset, paginate
from models.file import File, FileAuditLog, FileShare


class FileService:
    @staticmethod
    def _active_file_filters() -> list:
        return [File.deleted_at.is_(None)]

    @staticmethod
    async def create_file(
        db: AsyncSession,
        *,
        owner_id: int,
        filename: str,
        saved_filename: str,
        content_type: str,
        size: int,
        storage: str,
        file_path: str,
    ) -> File:
        file_record = File(
            owner_id=owner_id,
            filename=filename,
            saved_filename=saved_filename,
            content_type=content_type,
            size=size,
            storage=storage,
            file_path=file_path,
        )
        db.add(file_record)
        await db.commit()
        await db.refresh(file_record)
        return file_record

    @staticmethod
    async def list_user_files(
        db: AsyncSession,
        *,
        owner_id: int,
        params: ListParams,
        include_total: bool = True,
    ) -> PaginatedPage[File]:
        """
        分页列出当前用户的文件。

        排序用主键 id 降序（新上传的 id 更大，排在前面）。

        为什么不按 created_at + id 做复合游标？
          SQLite 把 DateTime 存成字符串，isoformat 和驱动绑定的格式
          对不齐时，`<` / `=` 会把整页数据又查回来。
          自增 id 是整数比较，SQLite / PostgreSQL 都稳。
          生产环境如果必须按业务时间排，请用真正的时间类型（PostgreSQL
          timestamptz）再做成 (created_at, id) 复合游标。

        include_total 默认 True：旧客户端已经依赖 data.total。
        """
        conditions = [File.owner_id == owner_id, *FileService._active_file_filters()]
        stmt = (
            select(File)
            .where(*conditions)
            .order_by(File.id.desc())
        )
        return await paginate(
            db,
            stmt,
            params=params,
            id_column=File.id,
            sort_column=File.id,
            sort_field="id",
            descending=True,
            include_total=include_total,
        )

    @staticmethod
    async def get_user_file_by_saved_filename(
        db: AsyncSession,
        *,
        owner_id: int,
        saved_filename: str,
    ) -> File | None:
        stmt = select(File).where(
            File.owner_id == owner_id,
            File.saved_filename == saved_filename,
            *FileService._active_file_filters(),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_file_by_id(
        db: AsyncSession,
        *,
        owner_id: int,
        file_id: int,
    ) -> File | None:
        stmt = select(File).where(
            File.owner_id == owner_id,
            File.id == file_id,
            *FileService._active_file_filters(),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_public_file_by_saved_filename(
        db: AsyncSession,
        *,
        saved_filename: str,
    ) -> File | None:
        stmt = select(File).where(
            File.saved_filename == saved_filename,
            File.visibility == "public",
            *FileService._active_file_filters(),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_file_by_id(
        db: AsyncSession,
        *,
        file_id: int,
    ) -> File | None:
        stmt = select(File).where(
            File.id == file_id,
            *FileService._active_file_filters(),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_visibility(
        db: AsyncSession,
        *,
        file_record: File,
        visibility: str,
    ) -> File:
        file_record.visibility = visibility
        await db.commit()
        await db.refresh(file_record)
        return file_record

    @staticmethod
    async def delete_file(db: AsyncSession, file_record: File) -> None:
        file_record.deleted_at = datetime.now(timezone.utc)
        file_record.visibility = "private"
        stmt = select(FileShare).where(
            FileShare.file_id == file_record.id,
            FileShare.revoked_at.is_(None),
        )
        result = await db.execute(stmt)
        for share_record in result.scalars().all():
            share_record.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def create_file_share(
        db: AsyncSession,
        *,
        file_id: int,
        owner_id: int,
        token_id: str,
        expires_at: datetime,
    ) -> FileShare:
        share_record = FileShare(
            file_id=file_id,
            owner_id=owner_id,
            token_id=token_id,
            expires_at=expires_at,
        )
        db.add(share_record)
        await db.commit()
        await db.refresh(share_record)
        return share_record

    @staticmethod
    async def list_user_file_shares(
        db: AsyncSession,
        *,
        owner_id: int,
        page: int,
        page_size: int,
        file_id: Optional[int] = None,
    ) -> Tuple[Sequence[FileShare], int]:
        conditions = [FileShare.owner_id == owner_id]
        if file_id is not None:
            conditions.append(FileShare.file_id == file_id)

        total_stmt = select(func.count()).select_from(FileShare).where(*conditions)
        total = await db.scalar(total_stmt) or 0

        # selectinload：先查分享，再一次性把关联文件取回来，避免循环里 N+1
        stmt = apply_offset(
            select(FileShare)
            .options(selectinload(FileShare.file))
            .where(*conditions)
            .order_by(FileShare.created_at.desc(), FileShare.id.desc()),
            compute_offset(page, page_size),
            page_size,
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total

    @staticmethod
    async def get_user_share_by_id(
        db: AsyncSession,
        *,
        owner_id: int,
        share_id: int,
    ) -> FileShare | None:
        stmt = (
            select(FileShare)
            .options(selectinload(FileShare.file))
            .where(
                FileShare.owner_id == owner_id,
                FileShare.id == share_id,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_share_by_id(
        db: AsyncSession,
        *,
        share_id: int,
    ) -> FileShare | None:
        stmt = (
            select(FileShare)
            .options(selectinload(FileShare.file))
            .where(
                FileShare.id == share_id,
                FileShare.file.has(File.deleted_at.is_(None)),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_share(
        db: AsyncSession,
        *,
        share_record: FileShare,
    ) -> FileShare:
        if share_record.revoked_at is None:
            share_record.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(share_record)
        return share_record

    @staticmethod
    async def record_share_access(
        db: AsyncSession,
        *,
        share_record: FileShare,
    ) -> FileShare:
        share_record.access_count += 1
        share_record.last_accessed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(share_record)
        return share_record

    @staticmethod
    async def create_audit_log(
        db: AsyncSession,
        *,
        file_id: int,
        owner_id: int,
        actor_user_id: int,
        event_type: str,
        detail: Optional[str] = None,
    ) -> FileAuditLog:
        audit_log = FileAuditLog(
            file_id=file_id,
            owner_id=owner_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            detail=detail,
        )
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        return audit_log

    @staticmethod
    async def list_user_audit_logs(
        db: AsyncSession,
        *,
        owner_id: int,
        page: int,
        page_size: int,
        file_id: Optional[int] = None,
    ) -> Tuple[Sequence[FileAuditLog], int]:
        conditions = [FileAuditLog.owner_id == owner_id]
        if file_id is not None:
            conditions.append(FileAuditLog.file_id == file_id)

        total_stmt = select(func.count()).select_from(FileAuditLog).where(*conditions)
        total = await db.scalar(total_stmt) or 0

        stmt = apply_offset(
            select(FileAuditLog)
            .where(*conditions)
            .order_by(FileAuditLog.created_at.desc(), FileAuditLog.id.desc()),
            compute_offset(page, page_size),
            page_size,
        )
        result = await db.execute(stmt)
        return result.scalars().all(), total
