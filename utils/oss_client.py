"""
===========================================
阿里云 OSS 客户端 (Aliyun OSS Client)
===========================================

功能：
  - 文件上传到 OSS
  - 文件下载
  - 文件删除
  - 生成签名 URL（防盗链）
  - 批量上传

依赖：
  pip install oss2
"""

import oss2
from oss2 import Auth
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
import mimetypes

from core.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class OSSClient:
    """阿里云 OSS 客户端"""

    def __init__(self):
        """
        初始化 OSS 客户端

        需要配置：
        - OSS_ACCESS_KEY_ID: AccessKey ID
        - OSS_ACCESS_KEY_SECRET: AccessKey Secret
        - OSS_ENDPOINT: 地域节点
        - OSS_BUCKET: 存储桶名称
        """
        if not settings.OSS_ACCESS_KEY_ID or not settings.OSS_ACCESS_KEY_SECRET:
            raise ValueError(
                "OSS 配置缺失！请在 .env 文件中设置 "
                "OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET"
            )

        # 创建认证对象
        self.auth = Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )

        # 创建 Bucket 对象
        self.bucket = oss2.Bucket(
            self.auth,
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET
        )

        logger.info(f"✅ OSS 客户端初始化成功: {settings.OSS_BUCKET} ({settings.OSS_ENDPOINT})")

    def _get_object_key(self, filename: str) -> str:
        """
        生成对象存储路径（Key）

        格式: uploads/2023/12/26/filename.jpg

        Args:
            filename: 文件名

        Returns:
            str: 完整的对象存储路径
        """
        # 按日期组织目录结构
        date_path = datetime.now().strftime("%Y/%m/%d")
        object_key = f"{settings.OSS_PATH_PREFIX}{date_path}/{filename}"

        return object_key

    def upload_file(
        self,
        file_path: Path,
        object_name: Optional[str] = None
    ) -> str:
        """
        上传文件到 OSS

        Args:
            file_path: 本地文件路径
            object_name: OSS 中的对象名称（不指定则使用文件名）

        Returns:
            str: 文件访问 URL
        """
        if object_name is None:
            object_name = file_path.name

        # 生成对象 Key
        object_key = self._get_object_key(object_name)

        try:
            # 上传文件
            with open(file_path, 'rb') as f:
                result = self.bucket.put_object(object_key, f)

            # 检查上传结果
            if result.status == 200:
                file_url = self.get_file_url(object_key)
                logger.info(f"✅ 文件上传成功: {object_key}")
                return file_url
            else:
                raise Exception(f"上传失败，状态码: {result.status}")

        except Exception as e:
            logger.error(f"❌ 文件上传失败: {e}")
            raise

    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传字节数据到 OSS

        Args:
            data: 文件字节数据
            object_name: 对象名称
            content_type: MIME 类型

        Returns:
            str: 文件访问 URL
        """
        # 生成对象 Key
        object_key = self._get_object_key(object_name)

        try:
            # 设置 Content-Type
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type
            else:
                # 自动推断 Content-Type
                mime_type, _ = mimetypes.guess_type(object_name)
                if mime_type:
                    headers['Content-Type'] = mime_type

            # 上传数据
            result = self.bucket.put_object(
                object_key,
                data,
                headers=headers
            )

            if result.status == 200:
                file_url = self.get_file_url(object_key)
                logger.info(f"✅ 数据上传成功: {object_key}")
                return file_url
            else:
                raise Exception(f"上传失败，状态码: {result.status}")

        except Exception as e:
            logger.error(f"❌ 数据上传失败: {e}")
            raise

    async def upload_stream(
        self,
        file_obj: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件流到 OSS（适合 FastAPI UploadFile）

        Args:
            file_obj: 文件对象（支持 read() 方法）
            object_name: 对象名称
            content_type: MIME 类型

        Returns:
            str: 文件访问 URL
        """
        # 生成对象 Key
        object_key = self._get_object_key(object_name)

        try:
            # 读取文件数据
            data = await file_obj.read()

            # 设置 Content-Type
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type

            # 上传
            result = self.bucket.put_object(
                object_key,
                data,
                headers=headers
            )

            if result.status == 200:
                file_url = self.get_file_url(object_key)
                logger.info(f"✅ 流式上传成功: {object_key} ({len(data)} bytes)")
                return file_url
            else:
                raise Exception(f"上传失败，状态码: {result.status}")

        except Exception as e:
            logger.error(f"❌ 流式上传失败: {e}")
            raise

    def download_file(
        self,
        object_key: str,
        local_path: Path
    ) -> None:
        """
        从 OSS 下载文件

        Args:
            object_key: OSS 对象 Key
            local_path: 本地保存路径
        """
        try:
            result = self.bucket.get_object_to_file(object_key, str(local_path))
            logger.info(f"✅ 文件下载成功: {object_key} → {local_path}")

        except oss2.exceptions.NoSuchKey:
            logger.error(f"❌ 文件不存在: {object_key}")
            raise FileNotFoundError(f"文件不存在: {object_key}")

        except Exception as e:
            logger.error(f"❌ 文件下载失败: {e}")
            raise

    def delete_file(self, object_key: str) -> bool:
        """
        删除 OSS 文件

        Args:
            object_key: OSS 对象 Key

        Returns:
            bool: 是否删除成功
        """
        try:
            result = self.bucket.delete_object(object_key)

            if result.status == 204:
                logger.info(f"🗑️  文件已删除: {object_key}")
                return True
            else:
                logger.warning(f"⚠️  删除失败，状态码: {result.status}")
                return False

        except Exception as e:
            logger.error(f"❌ 删除文件失败: {e}")
            return False

    def file_exists(self, object_key: str) -> bool:
        """
        检查文件是否存在

        Args:
            object_key: OSS 对象 Key

        Returns:
            bool: 文件是否存在
        """
        try:
            self.bucket.head_object(object_key)
            return True
        except oss2.exceptions.NoSuchKey:
            return False
        except Exception as e:
            logger.error(f"❌ 检查文件存在性失败: {e}")
            return False

    def get_file_url(self, object_key: str) -> str:
        """
        获取文件访问 URL

        Args:
            object_key: OSS 对象 Key

        Returns:
            str: 文件访问 URL
        """
        # 如果设置了自定义域名
        if settings.OSS_DOMAIN:
            protocol = "https" if settings.OSS_USE_SSL else "http"
            return f"{protocol}://{settings.OSS_DOMAIN}/{object_key}"

        # 使用 OSS 默认域名
        return f"{settings.OSS_BASE_URL}/{object_key}"

    def generate_signed_url(
        self,
        object_key: str,
        expires: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        生成签名 URL（临时访问链接）

        用途：
        - 私有文件的临时访问
        - 防盗链
        - 限时下载

        Args:
            object_key: OSS 对象 Key
            expires: 过期时间（秒），默认 1 小时
            method: HTTP 方法（GET, PUT 等）

        Returns:
            str: 签名 URL
        """
        try:
            url = self.bucket.sign_url(
                method,
                object_key,
                expires,
                slash_safe=True
            )

            logger.info(f"🔐 生成签名 URL: {object_key} (有效期: {expires}秒)")
            return url

        except Exception as e:
            logger.error(f"❌ 生成签名 URL 失败: {e}")
            raise

    def list_files(
        self,
        prefix: str = "",
        max_keys: int = 100
    ) -> list:
        """
        列出 OSS 文件

        Args:
            prefix: 对象前缀（目录）
            max_keys: 最多返回数量

        Returns:
            list: 文件列表
        """
        try:
            files = []

            for obj in oss2.ObjectIterator(self.bucket, prefix=prefix, max_keys=max_keys):
                files.append({
                    'key': obj.key,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'url': self.get_file_url(obj.key)
                })

            logger.info(f"📂 列出文件: {len(files)} 个")
            return files

        except Exception as e:
            logger.error(f"❌ 列出文件失败: {e}")
            raise

    def get_file_info(self, object_key: str) -> dict:
        """
        获取文件元信息

        Args:
            object_key: OSS 对象 Key

        Returns:
            dict: 文件信息
        """
        try:
            meta = self.bucket.head_object(object_key)

            return {
                'key': object_key,
                'size': meta.content_length,
                'content_type': meta.content_type,
                'last_modified': meta.last_modified,
                'etag': meta.etag,
                'url': self.get_file_url(object_key)
            }

        except oss2.exceptions.NoSuchKey:
            raise FileNotFoundError(f"文件不存在: {object_key}")

        except Exception as e:
            logger.error(f"❌ 获取文件信息失败: {e}")
            raise


# ============================================================
# 全局单例
# ============================================================

_oss_client: Optional[OSSClient] = None


def get_oss_client() -> OSSClient:
    """
    获取 OSS 客户端实例（单例模式）

    Returns:
        OSSClient: OSS 客户端
    """
    global _oss_client

    if _oss_client is None:
        _oss_client = OSSClient()

    return _oss_client


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【OSS 对象存储】
   - Bucket: 存储空间（容器）
   - Object: 存储对象（文件）
   - Key: 对象唯一标识（路径）

   类比：
   - Bucket = 仓库
   - Object = 货物
   - Key = 货架位置

2. 【OSS vs 本地存储】

   本地存储：
   ✅ 免费
   ✅ 简单
   ❌ 容量有限
   ❌ 不适合分布式
   ❌ 无 CDN 加速

   OSS 存储：
   ✅ 容量无限
   ✅ 高可用（99.9%）
   ✅ CDN 加速
   ✅ 适合生产环境
   ❌ 需要付费

3. 【上传方式】

   方式1: 上传本地文件
   upload_file(Path("photo.jpg"))

   方式2: 上传字节数据
   upload_bytes(data, "photo.jpg")

   方式3: 上传文件流（FastAPI）
   upload_stream(file.file, file.filename)

4. 【访问控制】

   公共读：任何人都可以访问
   - 使用场景：网站图片、公开文档
   - URL: https://bucket.oss-cn-beijing.aliyuncs.com/file.jpg

   私有：需要签名才能访问
   - 使用场景：用户隐私文件、付费内容
   - URL: 签名 URL（临时有效）

5. 【签名 URL】
   防盗链和权限控制

   # 生成 1 小时有效的下载链接
   url = generate_signed_url("file.jpg", expires=3600)

   特点：
   - 有时间限制
   - 包含签名（无法伪造）
   - 适合私有文件

6. 【文件组织】
   推荐按日期组织：

   uploads/
   ├── 2023/
   │   ├── 12/
   │   │   ├── 26/
   │   │   │   ├── file1.jpg
   │   │   │   └── file2.png

   好处：
   - 易于管理
   - 避免单目录文件过多
   - 便于按日期查询

7. 【最佳实践】

   ✅ 使用唯一文件名（避免覆盖）
   ✅ 设置正确的 Content-Type
   ✅ 使用 CDN 加速（绑定自定义域名）
   ✅ 定期清理过期文件
   ✅ 监控存储用量和费用

   ❌ 不要把密钥提交到代码
   ❌ 不要使用原始文件名（安全风险）
   ❌ 不要忽略错误处理

8. 【成本优化】

   - 使用存储类型（标准/低频/归档）
   - 设置生命周期规则（自动删除过期文件）
   - 使用 CDN 减少回源流量
   - 压缩图片（减少存储和流量）

9. 【安全性】

   - AccessKey 使用 RAM 子账号（最小权限）
   - 定期轮换密钥
   - 启用 HTTPS
   - 配置防盗链
   - 开启日志审计

下一步学习：
- ✅ OSS 基础上传/下载
- ⏭️  图片处理后上传 OSS
- ⏭️  大文件分片上传
- ⏭️  CDN 加速配置
"""
