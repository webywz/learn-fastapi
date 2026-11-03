"""
===========================================
大文件分片上传路由 (Chunked Upload Routes)
===========================================

功能：
  - init / upload-part / complete / abort
  - GET 查询进度（断点续传）
  - 过期会话清理

为什么不把这些塞进 files.py？
  files.py 已经承担单次上传、下载、分享、图片处理。
  分片是另一套状态机，单独文件更利于对照阅读。
  路由仍挂在 /api/v1/files 下，对前端来说还是「文件模块」。

和 POST /upload 的关系：
  - 小文件继续走 /upload，本模块不会替换它
  - 完成后都进同一张 files 表，下载 / 列表 / 分享接口不用改

认证：
  - GET /chunked 公开（教学说明，和 /email/ 一样）
  - 其余全部要登录；会话按 owner_id 隔离
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from api.v1.files import MAX_FILE_SIZE, serialize_file_record
from common.response import success
from core.config import settings
from core.database import get_db
from models.user import User
from schemas.file import ChunkedUploadCompleteRequest, ChunkedUploadInitRequest
from services.chunked_upload_service import (
    STATUS_ABORTED,
    STATUS_COMPLETED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    ChunkedUploadService,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/chunked", summary="分片上传说明")
async def chunked_upload_overview():
    """
    教学说明（统一 JSON 信封）。

    回答：为什么要分片、和单次上传怎么选、会话多久过期、
    本课不做 OSS Multipart。
    """
    return success(
        data={
            "module": "chunked-upload",
            "storage": "local",
            "checksum": "sha256",
            "single_shot_max_bytes": MAX_FILE_SIZE,
            "chunked_max_bytes": settings.CHUNKED_MAX_FILE_SIZE,
            "default_chunk_size": settings.CHUNKED_DEFAULT_CHUNK_SIZE,
            "max_chunk_size": settings.CHUNKED_MAX_CHUNK_SIZE,
            "session_ttl_seconds": settings.CHUNKED_SESSION_TTL_SECONDS,
            "temp_dir": f"{settings.UPLOAD_DIR}/.chunks/{{upload_id}}",
            "endpoints": {
                "init": "POST /api/v1/files/chunked/init",
                "status": "GET /api/v1/files/chunked/{upload_id}",
                "upload_part": "PUT /api/v1/files/chunked/{upload_id}/parts/{part_number}",
                "complete": "POST /api/v1/files/chunked/{upload_id}/complete",
                "abort": "DELETE /api/v1/files/chunked/{upload_id}",
                "cleanup": "POST /api/v1/files/chunked/cleanup",
            },
            "notes": [
                f"小于 {MAX_FILE_SIZE // 1024 // 1024}MB 建议走 POST /api/v1/files/upload",
                "同一 part_number 再传一次是幂等的（checksum 相同则跳过）",
                "complete 会把临时目录拼好后 os.replace 到 uploads/，再写入 files 表",
                "过期会话在 init / cleanup 时删除临时目录；也可手动删 data/uploads/.chunks/",
                "本课不做阿里云 OSS / AWS S3 Multipart，那是另一套 SDK",
            ],
        }
    )


@router.post("/chunked/cleanup", summary="清理过期的分片会话")
async def cleanup_expired_chunked_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    mine_only: bool = Query(False, description="只清理当前用户的过期会话"),
):
    """
    把 pending 且过期的会话标为 expired，并删除临时目录。

    不传 mine_only 时扫全部过期会话（磁盘垃圾不属于某个用户私有）。
    没有定时任务时靠这个接口，或靠下次 init 顺手清理。
    """
    result = await ChunkedUploadService.cleanup_expired_sessions(
        db,
        owner_id=current_user.id if mine_only else None,
    )
    return success(data=result, message=f"已清理 {result['expired']} 个过期会话")


@router.post("/chunked/init", summary="初始化分片上传")
async def init_chunked_upload(
    payload: ChunkedUploadInitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    只登记元数据，不传文件本体。

    客户端用返回的 upload_id、chunk_size、total_chunks 去切文件。
    可选 checksum（整文件 SHA-256）会在 complete 时核对。
    """
    session = await ChunkedUploadService.init_session(
        db,
        owner_id=current_user.id,
        filename=payload.filename,
        content_type=payload.content_type,
        total_size=payload.total_size,
        chunk_size=payload.chunk_size,
        checksum=payload.checksum,
    )
    return success(
        data=ChunkedUploadService.serialize(session),
        message="分片上传会话已创建",
    )


@router.get("/chunked/{upload_id}", summary="查询分片进度（续传）")
async def get_chunked_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    断点续传靠这个接口：看 missing_parts，只补缺的片。

    已完成 / 已取消 / 已过期也会返回，方便前端停掉进度条。
    """
    session = await ChunkedUploadService.get_owned_session(
        db,
        owner_id=current_user.id,
        upload_id=upload_id,
        allow_statuses={
            STATUS_PENDING,
            STATUS_COMPLETED,
            STATUS_ABORTED,
            STATUS_EXPIRED,
        },
    )
    return success(data=ChunkedUploadService.serialize(session))


@router.put("/chunked/{upload_id}/parts/{part_number}", summary="上传一个分片")
async def upload_chunk_part(
    upload_id: str,
    part_number: int,
    chunk: UploadFile = File(..., description="这一片的二进制内容"),
    checksum: Optional[str] = Form(
        None,
        description="可选：本片 SHA-256 hex，不匹配会拒绝",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传第 N 片（从 1 开始，和 S3 Multipart 一样）。

    幂等：同一片、同一 checksum 再 PUT 一次会 reused=true，不会复制数据。
    最后一片可以小于 chunk_size，其它片必须刚好等于 chunk_size。
    """
    result = await ChunkedUploadService.save_part(
        db,
        owner_id=current_user.id,
        upload_id=upload_id,
        part_number=part_number,
        chunk=chunk,
        checksum=checksum,
    )
    message = "分片已存在，跳过写入" if result["reused"] else "分片上传成功"
    return success(data=result, message=message)


@router.post("/chunked/{upload_id}/complete", summary="完成分片上传")
async def complete_chunked_upload(
    upload_id: str,
    payload: Optional[ChunkedUploadCompleteRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    校验齐片和 checksum，拼到临时文件后原子移动到 uploads/。

    成功后的 data 和单次上传同一套 FileRecord，
    所以原来的下载 / 列表 / 分享接口可以直接用。
    再调一次 complete 不会复制文件（幂等）。
    """
    body = payload or ChunkedUploadCompleteRequest()
    file_record = await ChunkedUploadService.complete(
        db,
        owner_id=current_user.id,
        upload_id=upload_id,
        checksum=body.checksum,
    )
    return success(
        data=serialize_file_record(file_record),
        message="分片上传完成（本地）",
    )


@router.delete("/chunked/{upload_id}", summary="取消分片上传")
async def abort_chunked_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    丢掉未完成的临时分片。已经 complete 的文件请走 DELETE /files/delete/{filename}。
    """
    session = await ChunkedUploadService.abort(
        db,
        owner_id=current_user.id,
        upload_id=upload_id,
    )
    return success(
        data=ChunkedUploadService.serialize(session),
        message="分片上传已取消",
    )
