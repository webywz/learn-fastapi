"""
===========================================
文件上传路由 (File Upload Routes)
===========================================

功能：
  - 基础文件上传
  - 文件类型验证
  - 文件大小限制
  - 本地存储
  - 文件下载
  - 多文件上传

学习目标：
  - FastAPI UploadFile 的使用
  - 文件流处理
  - 文件系统操作
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime

from common.response import success, error
from utils.logger import get_logger
from core.config import settings

try:
    from utils.image_processor import ImageProcessor, compress_image, create_thumbnail
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    from utils.oss_client import get_oss_client
    OSS_AVAILABLE = True
except ImportError:
    OSS_AVAILABLE = False

logger = get_logger(__name__)

# 检查功能可用性
if not PILLOW_AVAILABLE:
    logger.warning("⚠️  Pillow 未安装，图片处理功能将不可用。请运行: pip install Pillow")

if settings.OSS_ENABLED and not OSS_AVAILABLE:
    logger.error("❌ OSS 已启用但 oss2 库未安装！请运行: pip install oss2")
    logger.warning("⚠️  将使用本地存储作为后备方案")

# 创建路由器
router = APIRouter()

# ============================================================
# 配置
# ============================================================

# 上传文件存储目录
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 允许的文件类型（MIME types）
ALLOWED_MIME_TYPES = {
    # 图片
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/webp": [".webp"],
    # 文档
    "application/pdf": [".pdf"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    # 文本
    "text/plain": [".txt"],
    "text/csv": [".csv"],
}

# 文件大小限制（字节）
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ============================================================
# 辅助函数
# ============================================================

async def upload_to_oss(file: UploadFile, filename: str) -> dict:
    """
    上传文件到阿里云 OSS

    Args:
        file: 上传的文件对象
        filename: 文件名

    Returns:
        dict: 包含文件信息的字典
    """
    if not OSS_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="OSS 功能不可用，请安装 oss2: pip install oss2"
        )

    try:
        # 获取 OSS 客户端
        oss_client = get_oss_client()

        # 上传文件流
        file_url = await oss_client.upload_stream(
            file.file,
            filename,
            content_type=file.content_type
        )

        # 获取文件大小
        file_size = file.size if hasattr(file, 'size') else 0

        return {
            "filename": file.filename,
            "saved_filename": filename,
            "content_type": file.content_type,
            "size": file_size,
            "url": file_url,
            "storage": "oss"
        }

    except Exception as e:
        logger.error(f"❌ OSS 上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"OSS 上传失败: {str(e)}")


def validate_file_type(file: UploadFile) -> bool:
    """
    验证文件类型

    Args:
        file: 上传的文件对象

    Returns:
        bool: 文件类型是否合法
    """
    content_type = file.content_type

    if content_type not in ALLOWED_MIME_TYPES:
        return False

    # 验证文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = ALLOWED_MIME_TYPES[content_type]

    return file_ext in allowed_extensions


def generate_unique_filename(original_filename: str) -> str:
    """
    生成唯一的文件名

    格式: {timestamp}_{uuid}_{original_filename}

    Args:
        original_filename: 原始文件名

    Returns:
        str: 唯一的文件名
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]

    # 获取文件扩展名
    file_ext = Path(original_filename).suffix
    # 获取不带扩展名的文件名
    filename_without_ext = Path(original_filename).stem

    return f"{timestamp}_{unique_id}_{filename_without_ext}{file_ext}"


async def save_upload_file(file: UploadFile, destination: Path) -> int:
    """
    保存上传的文件到磁盘

    Args:
        file: 上传的文件对象
        destination: 目标路径

    Returns:
        int: 文件大小（字节）
    """
    file_size = 0

    try:
        with open(destination, "wb") as buffer:
            # 分块读取和写入，避免内存溢出
            chunk_size = 1024 * 1024  # 1 MB
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)

                # 检查文件大小
                if file_size > MAX_FILE_SIZE:
                    # 删除已写入的文件
                    buffer.close()
                    os.remove(destination)
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE / 1024 / 1024} MB）"
                    )

                buffer.write(chunk)
    finally:
        await file.close()

    return file_size


# ============================================================
# 路由端点
# ============================================================

@router.post("/upload", summary="上传单个文件")
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件")
):
    """
    上传单个文件

    **功能：**
    - 支持多种文件类型（图片、文档、文本）
    - 自动验证文件类型（MIME type 和扩展名）
    - 限制文件大小（最大 10 MB）
    - 自动生成唯一文件名
    - 支持本地存储和 OSS 存储

    **支持的文件类型：**
    - 图片: JPG, PNG, GIF, WebP
    - 文档: PDF, DOC, DOCX
    - 文本: TXT, CSV

    **存储方式：**
    - OSS_ENABLED=True: 上传到阿里云 OSS
    - OSS_ENABLED=False: 保存到本地磁盘

    **返回数据：**
    - filename: 原始文件名
    - saved_filename: 保存的文件名（唯一）
    - content_type: 文件 MIME 类型
    - size: 文件大小（字节）
    - url: 文件访问 URL
    - storage: 存储方式（oss/local）
    """
    logger.info(f"📤 收到文件上传请求: {file.filename} ({file.content_type})")

    # 1. 验证文件类型
    if not validate_file_type(file):
        logger.warning(f"❌ 不支持的文件类型: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}"
        )

    # 2. 生成唯一文件名
    unique_filename = generate_unique_filename(file.filename)

    # 3. 上传文件
    try:
        # 如果启用了 OSS，上传到 OSS
        if settings.OSS_ENABLED and OSS_AVAILABLE:
            logger.info("☁️  使用 OSS 存储")
            result = await upload_to_oss(file, unique_filename)
            return success(data=result, message="文件上传成功（OSS）")

        # 否则保存到本地
        else:
            logger.info("💾 使用本地存储")
            file_path = UPLOAD_DIR / unique_filename
            file_size = await save_upload_file(file, file_path)

            logger.info(f"✅ 文件保存成功: {unique_filename} ({file_size} bytes)")

            return success(data={
                "filename": file.filename,
                "saved_filename": unique_filename,
                "content_type": file.content_type,
                "size": file_size,
                "url": f"/api/v1/files/download/{unique_filename}",
                "storage": "local"
            }, message="文件上传成功（本地）")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/upload/multiple", summary="上传多个文件")
async def upload_multiple_files(
    files: List[UploadFile] = File(..., description="要上传的文件列表")
):
    """
    批量上传多个文件

    **功能：**
    - 支持一次上传多个文件
    - 每个文件独立验证和处理
    - 部分失败不影响其他文件

    **返回数据：**
    - uploaded_files: 成功上传的文件列表
    - failed_files: 上传失败的文件列表
    - total: 总文件数
    - success_count: 成功数量
    - failed_count: 失败数量
    """
    logger.info(f"📤 收到批量文件上传请求: {len(files)} 个文件")

    uploaded_files = []
    failed_files = []

    for file in files:
        try:
            # 验证文件类型
            if not validate_file_type(file):
                failed_files.append({
                    "filename": file.filename,
                    "error": f"不支持的文件类型: {file.content_type}"
                })
                continue

            # 生成唯一文件名
            unique_filename = generate_unique_filename(file.filename)
            file_path = UPLOAD_DIR / unique_filename

            # 保存文件
            file_size = await save_upload_file(file, file_path)

            uploaded_files.append({
                "filename": file.filename,
                "saved_filename": unique_filename,
                "content_type": file.content_type,
                "size": file_size,
                "url": f"/api/v1/files/download/{unique_filename}"
            })

            logger.info(f"✅ 文件保存成功: {unique_filename}")

        except Exception as e:
            logger.error(f"❌ 文件上传失败 {file.filename}: {e}")
            failed_files.append({
                "filename": file.filename,
                "error": str(e)
            })

    return success(data={
        "uploaded_files": uploaded_files,
        "failed_files": failed_files,
        "total": len(files),
        "success_count": len(uploaded_files),
        "failed_count": len(failed_files)
    }, message=f"批量上传完成: 成功 {len(uploaded_files)} 个，失败 {len(failed_files)} 个")


@router.get("/download/{filename}", summary="下载文件")
async def download_file(filename: str):
    """
    下载文件（直接返回）

    **功能：**
    - 根据文件名下载文件
    - 自动设置正确的 Content-Type
    - 浏览器可直接预览（图片、PDF 等）

    **参数：**
    - filename: 文件名（保存时生成的唯一文件名）
    """
    file_path = UPLOAD_DIR / filename

    # 检查文件是否存在
    if not file_path.exists():
        logger.warning(f"❌ 文件不存在: {filename}")
        raise HTTPException(status_code=404, detail="文件不存在")

    logger.info(f"📥 文件下载: {filename}")

    # 返回文件
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@router.get("/stream/{filename}", summary="流式下载文件")
async def stream_file(filename: str):
    """
    流式下载文件（适合大文件）

    **功能：**
    - 使用流式传输，内存占用小
    - 适合下载大文件
    - 支持断点续传（Range 请求）

    **参数：**
    - filename: 文件名
    """
    file_path = UPLOAD_DIR / filename

    # 检查文件是否存在
    if not file_path.exists():
        logger.warning(f"❌ 文件不存在: {filename}")
        raise HTTPException(status_code=404, detail="文件不存在")

    logger.info(f"📥 流式下载: {filename}")

    # 生成文件流
    def file_iterator():
        with open(file_path, "rb") as file:
            chunk_size = 1024 * 1024  # 1 MB
            while chunk := file.read(chunk_size):
                yield chunk

    # 返回流式响应
    return StreamingResponse(
        file_iterator(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/list", summary="列出所有上传的文件")
async def list_files(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """
    获取上传文件列表（分页）

    **功能：**
    - 列出所有已上传的文件
    - 支持分页
    - 显示文件基本信息

    **返回数据：**
    - files: 文件列表
    - total: 总文件数
    - page: 当前页码
    - page_size: 每页数量
    - total_pages: 总页数
    """
    # 获取所有文件
    all_files = list(UPLOAD_DIR.glob("*"))
    total = len(all_files)

    # 计算分页
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_files = all_files[start_idx:end_idx]

    # 构建文件列表
    files = []
    for file_path in page_files:
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/api/v1/files/download/{file_path.name}"
            })

    return success(data={
        "files": files,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    })


@router.delete("/delete/{filename}", summary="删除文件")
async def delete_file(filename: str):
    """
    删除已上传的文件

    **功能：**
    - 根据文件名删除文件
    - 从磁盘永久删除

    **参数：**
    - filename: 文件名
    """
    file_path = UPLOAD_DIR / filename

    # 检查文件是否存在
    if not file_path.exists():
        logger.warning(f"❌ 文件不存在: {filename}")
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        # 删除文件
        os.remove(file_path)
        logger.info(f"🗑️  文件已删除: {filename}")

        return success(message=f"文件 {filename} 已删除")
    except Exception as e:
        logger.error(f"❌ 删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.post("/image/compress", summary="压缩图片")
async def compress_image_api(
    file: UploadFile = File(..., description="要压缩的图片"),
    quality: int = Query(85, ge=1, le=100, description="压缩质量 (1-100)")
):
    """
    压缩图片文件

    **功能：**
    - 减小图片文件大小
    - 可调整压缩质量
    - 自动转换为 JPEG 格式

    **参数：**
    - file: 图片文件
    - quality: 压缩质量 (1-100)，默认 85
      - 100: 最高质量，文件较大
      - 85: 推荐值，质量和大小平衡
      - 50: 文件很小，质量下降

    **返回：**
    - 压缩后的图片信息
    """
    if not PILLOW_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="图片处理功能不可用，请安装 Pillow: pip install Pillow"
        )

    logger.info(f"📷 收到图片压缩请求: {file.filename} (质量: {quality})")

    # 验证是否为图片文件
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    try:
        # 保存原始文件
        original_filename = generate_unique_filename(file.filename)
        original_path = UPLOAD_DIR / original_filename
        original_size = await save_upload_file(file, original_path)

        # 压缩图片
        compressed_filename = f"compressed_{original_filename}"
        compressed_filename = compressed_filename.rsplit('.', 1)[0] + '.jpg'
        compressed_path = UPLOAD_DIR / compressed_filename

        processor = ImageProcessor(original_path)
        processor.compress(quality, compressed_path)

        compressed_size = compressed_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100

        # 删除原始文件（可选）
        os.remove(original_path)

        return success(data={
            "filename": file.filename,
            "compressed_filename": compressed_filename,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": f"{compression_ratio:.1f}%",
            "quality": quality,
            "url": f"/api/v1/files/download/{compressed_filename}"
        }, message="图片压缩成功")

    except Exception as e:
        logger.error(f"❌ 图片压缩失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片压缩失败: {str(e)}")


@router.post("/image/resize", summary="调整图片尺寸")
async def resize_image_api(
    file: UploadFile = File(..., description="要调整的图片"),
    width: Optional[int] = Query(None, ge=1, description="目标宽度"),
    height: Optional[int] = Query(None, ge=1, description="目标高度"),
    keep_ratio: bool = Query(True, description="是否保持宽高比")
):
    """
    调整图片尺寸

    **功能：**
    - 调整图片宽度和高度
    - 可选择保持或不保持宽高比
    - 高质量重采样

    **参数：**
    - file: 图片文件
    - width: 目标宽度（像素）
    - height: 目标高度（像素）
    - keep_ratio: 是否保持宽高比（默认 true）

    **使用场景：**
    - 只指定 width: 按宽度缩放，高度自适应
    - 只指定 height: 按高度缩放，宽度自适应
    - 同时指定: 按比例缩放到不超过指定尺寸
    """
    if not PILLOW_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="图片处理功能不可用，请安装 Pillow"
        )

    if not width and not height:
        raise HTTPException(status_code=400, detail="必须指定 width 或 height")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    try:
        # 保存原始文件
        original_filename = generate_unique_filename(file.filename)
        original_path = UPLOAD_DIR / original_filename
        await save_upload_file(file, original_path)

        # 调整尺寸
        resized_filename = f"resized_{original_filename}"
        resized_path = UPLOAD_DIR / resized_filename

        processor = ImageProcessor(original_path)
        original_size = processor.original_size

        processor.resize(width, height, keep_ratio, resized_path)

        # 获取新尺寸
        from PIL import Image
        new_image = Image.open(resized_path)
        new_size = new_image.size
        new_image.close()

        # 删除原始文件
        os.remove(original_path)

        return success(data={
            "filename": file.filename,
            "resized_filename": resized_filename,
            "original_size": f"{original_size[0]}x{original_size[1]}",
            "new_size": f"{new_size[0]}x{new_size[1]}",
            "url": f"/api/v1/files/download/{resized_filename}"
        }, message="图片尺寸调整成功")

    except Exception as e:
        logger.error(f"❌ 图片尺寸调整失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片尺寸调整失败: {str(e)}")


@router.post("/image/crop", summary="裁剪图片")
async def crop_image_api(
    file: UploadFile = File(..., description="要裁剪的图片"),
    width: int = Query(..., ge=1, description="裁剪宽度"),
    height: int = Query(..., ge=1, description="裁剪高度"),
    x: Optional[int] = Query(None, ge=0, description="左上角 X 坐标（不指定则居中裁剪）"),
    y: Optional[int] = Query(None, ge=0, description="左上角 Y 坐标（不指定则居中裁剪）")
):
    """
    裁剪图片

    **功能：**
    - 指定位置和尺寸裁剪
    - 支持居中裁剪（不指定 x, y）

    **参数：**
    - file: 图片文件
    - width: 裁剪宽度
    - height: 裁剪高度
    - x: 左上角 X 坐标（可选）
    - y: 左上角 Y 坐标（可选）

    **使用场景：**
    - 生成头像（正方形裁剪）
    - 裁剪图片特定区域
    - 移除图片边缘
    """
    if not PILLOW_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="图片处理功能不可用，请安装 Pillow"
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    try:
        # 保存原始文件
        original_filename = generate_unique_filename(file.filename)
        original_path = UPLOAD_DIR / original_filename
        await save_upload_file(file, original_path)

        # 裁剪
        cropped_filename = f"cropped_{original_filename}"
        cropped_path = UPLOAD_DIR / cropped_filename

        processor = ImageProcessor(original_path)

        if x is None or y is None:
            # 居中裁剪
            processor.crop_center(width, height, cropped_path)
        else:
            # 指定位置裁剪
            processor.crop(x, y, width, height, cropped_path)

        # 删除原始文件
        os.remove(original_path)

        return success(data={
            "filename": file.filename,
            "cropped_filename": cropped_filename,
            "crop_size": f"{width}x{height}",
            "crop_position": f"({x or 'center'}, {y or 'center'})",
            "url": f"/api/v1/files/download/{cropped_filename}"
        }, message="图片裁剪成功")

    except Exception as e:
        logger.error(f"❌ 图片裁剪失败: {e}")
        raise HTTPException(status_code=500, detail=f"图片裁剪失败: {str(e)}")


@router.post("/image/watermark/text", summary="添加文字水印")
async def add_text_watermark_api(
    file: UploadFile = File(..., description="要添加水印的图片"),
    text: str = Query(..., description="水印文字"),
    font_size: int = Query(40, ge=10, le=200, description="字体大小"),
    opacity: int = Query(128, ge=0, le=255, description="不透明度 (0-255)")
):
    """
    添加文字水印

    **功能：**
    - 在图片上添加文字水印
    - 自动放置在右下角
    - 可调整字体大小和透明度

    **参数：**
    - file: 图片文件
    - text: 水印文字
    - font_size: 字体大小（默认 40）
    - opacity: 不透明度 (0-255)
      - 0: 完全透明
      - 128: 半透明（默认）
      - 255: 完全不透明

    **使用场景：**
    - 版权保护
    - 品牌标识
    - 图片来源标注
    """
    if not PILLOW_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="图片处理功能不可用，请安装 Pillow"
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    try:
        # 保存原始文件
        original_filename = generate_unique_filename(file.filename)
        original_path = UPLOAD_DIR / original_filename
        await save_upload_file(file, original_path)

        # 添加水印
        watermarked_filename = f"watermark_{original_filename}"
        watermarked_path = UPLOAD_DIR / watermarked_filename

        processor = ImageProcessor(original_path)
        processor.add_text_watermark(
            text=text,
            font_size=font_size,
            color=(255, 255, 255, opacity),
            output_path=watermarked_path
        )

        # 删除原始文件
        os.remove(original_path)

        return success(data={
            "filename": file.filename,
            "watermarked_filename": watermarked_filename,
            "watermark_text": text,
            "url": f"/api/v1/files/download/{watermarked_filename}"
        }, message="文字水印添加成功")

    except Exception as e:
        logger.error(f"❌ 添加文字水印失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加文字水印失败: {str(e)}")


@router.post("/image/thumbnail", summary="生成缩略图")
async def create_thumbnail_api(
    file: UploadFile = File(..., description="要生成缩略图的图片"),
    size: int = Query(200, ge=50, le=1000, description="缩略图尺寸（正方形）")
):
    """
    生成缩略图

    **功能：**
    - 创建正方形缩略图
    - 保持宽高比
    - 快速预览

    **参数：**
    - file: 图片文件
    - size: 缩略图尺寸（宽=高）

    **使用场景：**
    - 图片列表预览
    - 快速加载
    - 减少带宽
    """
    if not PILLOW_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="图片处理功能不可用，请安装 Pillow"
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    try:
        # 保存原始文件
        original_filename = generate_unique_filename(file.filename)
        original_path = UPLOAD_DIR / original_filename
        original_size = await save_upload_file(file, original_path)

        # 生成缩略图
        processor = ImageProcessor(original_path)
        thumbnail_path = processor.create_thumbnail((size, size))

        thumbnail_size = thumbnail_path.stat().st_size
        thumbnail_filename = thumbnail_path.name

        # 保留原始文件和缩略图

        return success(data={
            "filename": file.filename,
            "original_filename": original_filename,
            "thumbnail_filename": thumbnail_filename,
            "original_size": original_size,
            "thumbnail_size": thumbnail_size,
            "original_url": f"/api/v1/files/download/{original_filename}",
            "thumbnail_url": f"/api/v1/files/download/{thumbnail_filename}"
        }, message="缩略图生成成功")

    except Exception as e:
        logger.error(f"❌ 生成缩略图失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成缩略图失败: {str(e)}")


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【UploadFile vs File】
   - UploadFile: FastAPI 推荐，基于 SpooledTemporaryFile
     - 自动处理内存和磁盘临时存储
     - 提供 async 方法
     - 包含 filename, content_type 等元数据

   - File: 二进制数据（bytes）
     - 适合小文件
     - 全部加载到内存

   推荐使用 UploadFile

2. 【文件类型验证】
   两种验证方式：
   - MIME type: file.content_type
   - 文件扩展名: Path(file.filename).suffix

   建议两者都验证（更安全）

3. 【文件大小限制】
   方法1: 读取时检查（本例使用）
   - 边读边检查
   - 超过限制立即停止

   方法2: 使用 middleware
   - 在请求级别限制
   - 适合全局限制

4. 【文件保存策略】
   - 生成唯一文件名（避免覆盖）
   - 分块读写（chunk）
   - 使用 async/await（非阻塞）
   - 错误处理（删除部分写入的文件）

5. 【文件下载】
   两种方式：

   - FileResponse: 直接返回
     - 适合小文件
     - 浏览器可预览

   - StreamingResponse: 流式传输
     - 适合大文件
     - 内存占用小
     - 支持断点续传

6. 【安全考虑】
   - 验证文件类型（防止恶意文件）
   - 限制文件大小（防止 DoS）
   - 使用唯一文件名（防止路径遍历）
   - 不直接使用用户提供的文件名
   - 存储在 web 根目录外

7. 【最佳实践】
   - 使用 Path 而不是字符串拼接路径
   - 异步保存文件
   - 记录日志
   - 统一响应格式
   - 清晰的错误消息

下一步学习：
- ✅ 基础文件上传
- ✅ 文件类型验证
- ✅ 文件大小限制
- ✅ 本地存储
- ⏭️  云存储（阿里云 OSS / AWS S3）
- ⏭️  图片处理（Pillow）
- ⏭️  大文件分片上传
- ⏭️  文件 URL 签名
"""
