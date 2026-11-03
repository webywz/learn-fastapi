"""
===========================================
大文件分片上传服务 (Chunked Upload Service)
===========================================

作用：
  把「大文件切成小片 → 逐片落盘 → 校验 → 拼起来原子移动」收成一层。
  API 只负责鉴权和参数，真正的会话 / 磁盘 / 校验都在这里。

为什么要分片？一次性 POST 整文件有三件事会砸：
  1. 超时：Nginx / 负载均衡 / FastAPI worker 都有读超时，
     200MB 在慢网上传可能跑十几分钟，连接中途被掐。
  2. 内存：UploadFile 虽有 SpooledTemporaryFile，但反向代理仍可能
     先把 body 读完再转发给应用。切片后每片只有几 MB。
  3. 失败重来：传了 90% 断网，整文件方案只能从头来。
     分片方案只重传缺的那几片（断点续传）。

和单次上传 POST /api/v1/files/upload 的关系：
  - 小文件（默认 ≤ 10MB）继续走单次上传，简单、一次审计日志
  - 大文件走本模块；完成后同样写入 files 表，下载 / 分享 / 审计接口不用改
  - 本课只做本地磁盘。OSS Multipart（阿里云 / S3）是另一套 SDK，
    流程很像（init / upload-part / complete / abort），但对象键和 ETag 不同

四个动词（对标 S3 Multipart Upload，方便以后迁云）：

  init      只登记元数据，返回 upload_id 和切分方案
  upload    写入第 N 片；同一片再传是幂等的
  complete  校验齐片 + checksum，临时目录拼好后 os.replace 到正式目录
  abort     删临时目录，会话作废

类比前端：
  - init ≈ 先拿一个 uploadId，再按 slice() 切 Blob
  - 单片失败 ≈ 只重试那一个 XMLHttpRequest，进度条不用归零
  - checksum ≈ 前端 crypto.subtle.digest('SHA-256')，对上才算传完
  - TTL 清理 ≈ 浏览器关了，服务器不能无限囤 blob
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.error_codes import ErrorCode
from common.exceptions import BusinessException
from core.config import settings
from models.file import FileUploadPart, FileUploadSession
from services.file_service import FileService
from utils.logger import get_logger

logger = get_logger(__name__)

# 状态机里会出现的值。写死字符串而不是 Python Enum 入库，
# 是为了 SQLite / 文档 / 前端都能直接读，少一层映射。
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_ABORTED = "aborted"
STATUS_EXPIRED = "expired"

SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
PART_FILENAME = "part_{part:05d}.bin"


# ============================================================
# 路径 / 哈希小工具
# ============================================================
#
# 所有路径都从 settings.UPLOAD_DIR 现算，方便测试 monkeypatch。
# 临时目录在 uploads/.chunks/{upload_id}/，正式文件在 uploads/ 根下。
# 点开头的 .chunks 提醒「这不是用户可下载的成品」。
#

def upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def chunk_root() -> Path:
    root = upload_root() / ".chunks"
    root.mkdir(parents=True, exist_ok=True)
    return root


def session_dir(upload_id: str) -> Path:
    # upload_id 是我们自己发的 UUID，不是用户文件名，不存在路径穿越
    return chunk_root() / upload_id


def part_path(upload_id: str, part_number: int) -> Path:
    return session_dir(upload_id) / PART_FILENAME.format(part=part_number)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """
    流式算文件 SHA-256，不要 path.read_bytes()。

    complete 时文件可能到 100MB。一次性读进内存会把 worker 撑爆，
    分片上传前面节省的内存就白费了。
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_checksum(value: Optional[str]) -> Optional[str]:
    """
    允许 'ABC..' / 'sha256:abc..'，统一存小写 hex。
    给错长度或夹杂杂字符时立刻拒绝，避免 complete 时才发现白传。
    """
    if value is None:
        return None
    text = value.strip().lower()
    if not text:
        return None
    if text.startswith("sha256:"):
        text = text[7:]
    if not SHA256_HEX_RE.match(text):
        raise BusinessException(
            ErrorCode.CHUNK_UPLOAD_INVALID,
            message="checksum 必须是 64 位 SHA-256 hex",
        )
    return text


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def expected_part_size(total_size: int, chunk_size: int, total_chunks: int, part_number: int) -> int:
    """最后一片吃剩余字节，前面的片必须刚好等于 chunk_size。"""
    if part_number == total_chunks:
        return total_size - chunk_size * (total_chunks - 1)
    return chunk_size


def remove_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


# ============================================================
# MIME / 大小：和单次上传同一套规矩
# ============================================================
#
# 分片 init 时还没有文件流，只能看 filename + content_type。
# 这和单次上传一样防不住「把 .exe 改后缀」，只是第一道门。
# 真正的类型嗅探（python-magic）本课不做，避免多装系统库。
#

def validate_filename_and_mime(filename: str, content_type: str) -> str:
    from api.v1.files import ALLOWED_MIME_TYPES

    safe_name = Path(filename).name
    if not safe_name or safe_name in {".", ".."}:
        raise BusinessException(
            ErrorCode.CHUNK_UPLOAD_INVALID,
            message="文件名无效",
        )

    if content_type not in ALLOWED_MIME_TYPES:
        raise BusinessException(
            ErrorCode.CHUNK_UPLOAD_INVALID,
            message=f"不支持的文件类型: {content_type}",
        )

    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_MIME_TYPES[content_type]:
        raise BusinessException(
            ErrorCode.CHUNK_UPLOAD_INVALID,
            message=f"扩展名 {suffix or '(无)'} 与 MIME {content_type} 不匹配",
        )
    return safe_name


def resolve_chunk_plan(total_size: int, chunk_size: Optional[int]) -> tuple[int, int]:
    max_file = settings.CHUNKED_MAX_FILE_SIZE
    max_chunk = settings.CHUNKED_MAX_CHUNK_SIZE
    default_chunk = settings.CHUNKED_DEFAULT_CHUNK_SIZE

    if total_size > max_file:
        raise BusinessException(
            ErrorCode.CHUNK_UPLOAD_INVALID,
            message=(
                f"文件大小超过分片上传上限（最大 {max_file / 1024 / 1024:.0f} MB）"
            ),
        )

    size = chunk_size or default_chunk
    if size > max_chunk:
        raise BusinessException(
            ErrorCode.CHUNK_UPLOAD_INVALID,
            message=f"分片过大（最大 {max_chunk / 1024 / 1024:.0f} MB）",
        )
    # 文件比默认片还小：缩成 1 片，别逼客户端切出空片
    size = min(size, total_size)
    total_chunks = (total_size + size - 1) // size
    return size, total_chunks


# ============================================================
# 会话读写
# ============================================================

class ChunkedUploadService:
    @staticmethod
    def serialize(session: FileUploadSession) -> dict:
        uploaded = [
            {
                "part_number": part.part_number,
                "size": part.size,
                "checksum": part.checksum,
                "reused": False,
            }
            for part in sorted(session.parts, key=lambda item: item.part_number)
        ]
        uploaded_numbers = {item["part_number"] for item in uploaded}
        missing = [
            number
            for number in range(1, session.total_chunks + 1)
            if number not in uploaded_numbers
        ]
        return {
            "upload_id": session.upload_id,
            "filename": session.filename,
            "content_type": session.content_type,
            "total_size": session.total_size,
            "chunk_size": session.chunk_size,
            "total_chunks": session.total_chunks,
            "status": session.status,
            "checksum": session.checksum,
            "expires_at": session.expires_at,
            "uploaded_parts": uploaded,
            "missing_parts": missing,
            "file_id": session.file_id,
            "saved_filename": session.saved_filename,
        }

    @staticmethod
    async def _get_by_upload_id(
        db: AsyncSession,
        upload_id: str,
    ) -> FileUploadSession | None:
        stmt = (
            select(FileUploadSession)
            .options(selectinload(FileUploadSession.parts))
            .where(FileUploadSession.upload_id == upload_id)
            # 同一 Session 里第二次查时，identity map 会复用旧对象，
            # 已经 load 过的 parts 集合不会自动刷新（init 时空的）。
            # populate_existing 强制用这次 SELECT 覆盖，否则 complete 会以为还缺片。
            .execution_options(populate_existing=True)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def _mark_expired(db: AsyncSession, session: FileUploadSession) -> FileUploadSession:
        if session.status == STATUS_PENDING:
            session.status = STATUS_EXPIRED
            for part in list(session.parts):
                await db.delete(part)
            await db.commit()
            reloaded = await ChunkedUploadService._get_by_upload_id(db, session.upload_id)
            if reloaded is not None:
                session = reloaded
        remove_dir(session_dir(session.upload_id))
        return session

    @staticmethod
    async def get_owned_session(
        db: AsyncSession,
        *,
        owner_id: int,
        upload_id: str,
        allow_statuses: Optional[set[str]] = None,
    ) -> FileUploadSession:
        """
        取当前用户的会话，并顺便处理过期。

        别人的 upload_id 一律当「不存在」，避免用枚举探测别人有没有上传。
        """
        session = await ChunkedUploadService._get_by_upload_id(db, upload_id)
        if session is None or session.owner_id != owner_id:
            raise BusinessException(ErrorCode.CHUNK_UPLOAD_NOT_FOUND)

        if session.status == STATUS_PENDING and as_utc(session.expires_at) <= now_utc():
            session = await ChunkedUploadService._mark_expired(db, session)

        if session.status == STATUS_EXPIRED:
            if allow_statuses and STATUS_EXPIRED in allow_statuses:
                return session
            raise BusinessException(ErrorCode.CHUNK_UPLOAD_EXPIRED)

        if session.status == STATUS_ABORTED:
            if allow_statuses and STATUS_ABORTED in allow_statuses:
                return session
            raise BusinessException(ErrorCode.CHUNK_UPLOAD_ABORTED)

        if allow_statuses is not None and session.status not in allow_statuses:
            raise BusinessException(
                ErrorCode.CHUNK_UPLOAD_CONFLICT,
                message=f"当前状态为 {session.status}，不能执行此操作",
            )
        return session

    @staticmethod
    async def cleanup_expired_sessions(
        db: AsyncSession,
        *,
        owner_id: Optional[int] = None,
    ) -> dict:
        """
        清掉过期的 pending 会话（临时目录 + 状态改 expired）。

        可以只清某个用户，也可以全局扫。init 时会调用一次，
        所以即使没人记得跑定时任务，磁盘也不会无限涨。
        没有 Celery Beat 时：手动 POST /chunked/cleanup，或直接删
        data/uploads/.chunks/ 下的目录（会话会在下次访问时对不上）。
        """
        cutoff = now_utc()
        conditions = [FileUploadSession.status == STATUS_PENDING]
        if owner_id is not None:
            conditions.append(FileUploadSession.owner_id == owner_id)

        result = await db.execute(select(FileUploadSession).where(*conditions))
        # SQLite 常把带 timezone 的 DateTime 读成 naive，比较放到 Python 里做
        sessions = [
            session
            for session in result.scalars().all()
            if as_utc(session.expires_at) <= cutoff
        ]
        for session in sessions:
            session.status = STATUS_EXPIRED
            remove_dir(session_dir(session.upload_id))

        if sessions:
            await db.commit()

        logger.info("清理过期分片会话: %s 个", len(sessions))
        return {"expired": len(sessions), "cutoff": cutoff.isoformat()}

    @staticmethod
    async def init_session(
        db: AsyncSession,
        *,
        owner_id: int,
        filename: str,
        content_type: str,
        total_size: int,
        chunk_size: Optional[int] = None,
        checksum: Optional[str] = None,
    ) -> FileUploadSession:
        await ChunkedUploadService.cleanup_expired_sessions(db)

        safe_name = validate_filename_and_mime(filename, content_type)
        size, total_chunks = resolve_chunk_plan(total_size, chunk_size)
        file_checksum = normalize_checksum(checksum)
        upload_id = str(uuid.uuid4())
        expires_at = now_utc() + timedelta(seconds=settings.CHUNKED_SESSION_TTL_SECONDS)

        session_dir(upload_id).mkdir(parents=True, exist_ok=True)

        session = FileUploadSession(
            upload_id=upload_id,
            owner_id=owner_id,
            filename=safe_name,
            content_type=content_type,
            total_size=total_size,
            chunk_size=size,
            total_chunks=total_chunks,
            checksum=file_checksum,
            status=STATUS_PENDING,
            expires_at=expires_at,
        )
        db.add(session)
        await db.commit()
        loaded = await ChunkedUploadService._get_by_upload_id(db, upload_id)
        assert loaded is not None

        logger.info(
            "创建分片会话 %s: %s (%s bytes, %s 片, ttl=%ss)",
            upload_id,
            safe_name,
            total_size,
            total_chunks,
            settings.CHUNKED_SESSION_TTL_SECONDS,
        )
        return loaded

    @staticmethod
    async def save_part(
        db: AsyncSession,
        *,
        owner_id: int,
        upload_id: str,
        part_number: int,
        chunk: UploadFile,
        checksum: Optional[str] = None,
    ) -> dict:
        """
        写入一片。

        幂等规则（这是续传能用的关键）：
          - 同一 part_number 再来一次：如果内容 SHA-256 一样，直接 reused=true
          - 如果不一样：视为客户端重传（上次写坏了 / 换了文件），覆盖
          - 客户端带了 checksum 但和我们算的不一致：拒绝，不留坏片

        落盘顺序：先写 part_XXXXX.bin.tmp，再 os.replace。
        进程在半路被杀，不会留下「半片被当成整片」的文件。
        """
        session = await ChunkedUploadService.get_owned_session(
            db,
            owner_id=owner_id,
            upload_id=upload_id,
            allow_statuses={STATUS_PENDING},
        )

        if part_number < 1 or part_number > session.total_chunks:
            raise BusinessException(
                ErrorCode.CHUNK_UPLOAD_INVALID,
                message=f"part_number 必须在 1 和 {session.total_chunks} 之间",
            )

        expected_size = expected_part_size(
            session.total_size,
            session.chunk_size,
            session.total_chunks,
            part_number,
        )
        client_checksum = normalize_checksum(checksum)

        dest = part_path(upload_id, part_number)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")

        hasher = hashlib.sha256()
        written = 0
        try:
            with tmp.open("wb") as buffer:
                while True:
                    block = await chunk.read(64 * 1024)
                    if not block:
                        break
                    written += len(block)
                    # 多读 1 字节就停，避免恶意客户端拿「一片」灌爆磁盘
                    if written > expected_size:
                        raise BusinessException(
                            ErrorCode.CHUNK_UPLOAD_INVALID,
                            message=(
                                f"第 {part_number} 片大小应为 {expected_size} 字节"
                            ),
                        )
                    hasher.update(block)
                    buffer.write(block)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        finally:
            await chunk.close()

        if written != expected_size:
            tmp.unlink(missing_ok=True)
            raise BusinessException(
                ErrorCode.CHUNK_UPLOAD_INVALID,
                message=(
                    f"第 {part_number} 片大小应为 {expected_size} 字节，实际 {written}"
                ),
            )

        actual_checksum = hasher.hexdigest()
        if client_checksum and client_checksum != actual_checksum:
            tmp.unlink(missing_ok=True)
            raise BusinessException(
                ErrorCode.CHUNK_CHECKSUM_MISMATCH,
                message=f"第 {part_number} 片校验和不匹配",
            )

        existing = next(
            (part for part in session.parts if part.part_number == part_number),
            None,
        )
        reused = (
            existing is not None
            and existing.checksum == actual_checksum
            and existing.size == written
            and dest.exists()
        )
        if reused:
            tmp.unlink(missing_ok=True)
            logger.info("分片 %s#%s 幂等命中，跳过写入", upload_id, part_number)
        else:
            os.replace(tmp, dest)
            if existing is None:
                existing = FileUploadPart(
                    session_id=session.id,
                    part_number=part_number,
                    size=written,
                    checksum=actual_checksum,
                )
                db.add(existing)
            else:
                existing.size = written
                existing.checksum = actual_checksum
            await db.commit()
            logger.info(
                "写入分片 %s#%s (%s bytes, sha256=%s)",
                upload_id,
                part_number,
                written,
                actual_checksum[:8],
            )

        loaded = await ChunkedUploadService._get_by_upload_id(db, upload_id)
        assert loaded is not None
        uploaded_numbers = {part.part_number for part in loaded.parts}
        return {
            "upload_id": upload_id,
            "part_number": part_number,
            "size": written,
            "checksum": actual_checksum,
            "reused": reused,
            "uploaded_count": len(loaded.parts),
            "total_chunks": loaded.total_chunks,
            "missing_parts": [
                number
                for number in range(1, loaded.total_chunks + 1)
                if number not in uploaded_numbers
            ],
        }

    @staticmethod
    async def complete(
        db: AsyncSession,
        *,
        owner_id: int,
        upload_id: str,
        checksum: Optional[str] = None,
    ):
        """
        拼片 → 校验 → 原子移动 → 写入 files 表。

        为什么必须「先写临时 assembled，再 os.replace」？
          如果直接往正式文件名上逐片 append，中途崩溃会留下
          半成品，而下次 complete 可能误把它当成功。
          os.replace 在同一文件系统上是原子的：要么还是旧文件，
          要么已经是完整新文件。

        complete 本身也幂等：已经 completed 再调一次，返回原来的文件记录。
        前端「点了两次完成」或网络重试不该复制出两份文件。
        """
        from api.v1.files import generate_unique_filename

        session = await ChunkedUploadService.get_owned_session(
            db,
            owner_id=owner_id,
            upload_id=upload_id,
            allow_statuses={STATUS_PENDING, STATUS_COMPLETED},
        )

        if session.status == STATUS_COMPLETED:
            file_record = None
            if session.file_id is not None:
                file_record = await FileService.get_user_file_by_id(
                    db,
                    owner_id=owner_id,
                    file_id=session.file_id,
                )
            if file_record is None:
                raise BusinessException(ErrorCode.CHUNK_UPLOAD_NOT_FOUND)
            logger.info("分片会话 %s 已完成，幂等返回文件 #%s", upload_id, file_record.id)
            return file_record

        if len(session.parts) != session.total_chunks:
            missing = [
                number
                for number in range(1, session.total_chunks + 1)
                if number not in {part.part_number for part in session.parts}
            ]
            raise BusinessException(
                ErrorCode.CHUNK_UPLOAD_INCOMPLETE,
                message=f"还缺分片: {missing}",
                data={"missing_parts": missing},
            )

        requested = normalize_checksum(checksum)
        expected_checksum = requested or session.checksum
        if requested and session.checksum and requested != session.checksum:
            raise BusinessException(
                ErrorCode.CHUNK_CHECKSUM_MISMATCH,
                message="complete 与 init 的 checksum 不一致",
            )

        work_dir = session_dir(upload_id)
        assembled = work_dir / "assembled.bin"
        try:
            with assembled.open("wb") as out:
                for part_number in range(1, session.total_chunks + 1):
                    source = part_path(upload_id, part_number)
                    if not source.exists():
                        raise BusinessException(
                            ErrorCode.CHUNK_UPLOAD_INCOMPLETE,
                            message=f"分片文件缺失: {part_number}",
                        )
                    with source.open("rb") as inp:
                        shutil.copyfileobj(inp, out, length=1024 * 1024)
        except Exception:
            assembled.unlink(missing_ok=True)
            raise

        assembled_size = assembled.stat().st_size
        if assembled_size != session.total_size:
            assembled.unlink(missing_ok=True)
            raise BusinessException(
                ErrorCode.CHUNK_CHECKSUM_MISMATCH,
                message=(
                    f"拼出的文件大小为 {assembled_size}，期望 {session.total_size}"
                ),
            )

        actual_checksum = sha256_file(assembled)
        if expected_checksum and expected_checksum != actual_checksum:
            assembled.unlink(missing_ok=True)
            raise BusinessException(
                ErrorCode.CHUNK_CHECKSUM_MISMATCH,
                message="完整文件 SHA-256 不匹配",
            )

        unique_filename = generate_unique_filename(session.filename)
        final_path = upload_root() / unique_filename
        try:
            os.replace(assembled, final_path)
        except Exception:
            assembled.unlink(missing_ok=True)
            raise

        try:
            file_record = await FileService.create_file(
                db,
                owner_id=owner_id,
                filename=session.filename,
                saved_filename=unique_filename,
                content_type=session.content_type,
                size=session.total_size,
                storage="local",
                file_path=str(final_path),
            )
        except Exception:
            final_path.unlink(missing_ok=True)
            raise

        session.status = STATUS_COMPLETED
        session.file_id = file_record.id
        session.saved_filename = unique_filename
        session.checksum = expected_checksum or actual_checksum
        await db.commit()
        await FileService.create_audit_log(
            db,
            file_id=file_record.id,
            owner_id=owner_id,
            actor_user_id=owner_id,
            event_type="upload",
            detail=(
                f"分片上传 {file_record.filename} "
                f"({session.total_chunks} 片, sha256={actual_checksum[:12]}…)"
            ),
        )

        remove_dir(work_dir)
        logger.info(
            "分片会话 %s 完成 → %s (%s bytes)",
            upload_id,
            unique_filename,
            session.total_size,
        )
        return file_record

    @staticmethod
    async def abort(
        db: AsyncSession,
        *,
        owner_id: int,
        upload_id: str,
    ) -> FileUploadSession:
        """
        用户点取消 / 换文件重传：立刻释放磁盘。

        已 completed 的不能 abort，否则正式文件还在、会话却说取消了。
        要删成品走原来的 DELETE /files/delete/{filename}。
        """
        session = await ChunkedUploadService.get_owned_session(
            db,
            owner_id=owner_id,
            upload_id=upload_id,
            allow_statuses={STATUS_PENDING, STATUS_ABORTED, STATUS_EXPIRED},
        )
        if session.status == STATUS_ABORTED:
            return session

        session.status = STATUS_ABORTED
        # 分片行跟着会话清掉，避免 GET 还显示「已上传 3 片」
        for part in list(session.parts):
            await db.delete(part)
        await db.commit()
        remove_dir(session_dir(upload_id))
        logger.info("已取消分片会话 %s", upload_id)
        loaded = await ChunkedUploadService._get_by_upload_id(db, upload_id)
        assert loaded is not None
        return loaded
