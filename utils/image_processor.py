"""
===========================================
图片处理工具 (Image Processor)
===========================================

功能：
  - 图片压缩
  - 图片裁剪（固定尺寸、按比例）
  - 添加水印（文字、图片）
  - 图片格式转换
  - 生成缩略图

依赖：
  pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from typing import Tuple, Optional
import io

from utils.logger import get_logger

logger = get_logger(__name__)


class ImageProcessor:
    """图片处理类"""

    def __init__(self, image_path: Path):
        """
        初始化图片处理器

        Args:
            image_path: 图片文件路径
        """
        self.image_path = image_path
        self.image = Image.open(image_path)
        self.original_size = self.image.size
        logger.info(f"📷 加载图片: {image_path.name} ({self.original_size})")

    def compress(
        self,
        quality: int = 85,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        压缩图片（减小文件大小）

        Args:
            quality: 压缩质量 (1-100)，数字越小文件越小但质量越低
            output_path: 输出路径（如果不指定，则覆盖原文件）

        Returns:
            Path: 压缩后的文件路径
        """
        if output_path is None:
            output_path = self.image_path

        # 转换 RGBA 为 RGB（JPEG 不支持透明度）
        if self.image.mode == 'RGBA':
            rgb_image = Image.new('RGB', self.image.size, (255, 255, 255))
            rgb_image.paste(self.image, mask=self.image.split()[3])
            self.image = rgb_image

        # 保存压缩后的图片
        self.image.save(
            output_path,
            format='JPEG',
            quality=quality,
            optimize=True
        )

        original_size = self.image_path.stat().st_size
        compressed_size = output_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100

        logger.info(
            f"✅ 图片压缩完成: "
            f"{original_size / 1024:.1f}KB → {compressed_size / 1024:.1f}KB "
            f"({compression_ratio:.1f}% 压缩率)"
        )

        return output_path

    def resize(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        keep_ratio: bool = True,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        调整图片尺寸

        Args:
            width: 目标宽度（像素）
            height: 目标高度（像素）
            keep_ratio: 是否保持宽高比
            output_path: 输出路径

        Returns:
            Path: 调整后的文件路径
        """
        if output_path is None:
            output_path = self.image_path

        original_width, original_height = self.image.size

        # 如果保持比例
        if keep_ratio:
            if width and not height:
                # 只指定宽度
                ratio = width / original_width
                height = int(original_height * ratio)
            elif height and not width:
                # 只指定高度
                ratio = height / original_height
                width = int(original_width * ratio)
            elif width and height:
                # 两者都指定，按较小的比例
                width_ratio = width / original_width
                height_ratio = height / original_height
                ratio = min(width_ratio, height_ratio)
                width = int(original_width * ratio)
                height = int(original_height * ratio)

        # 调整尺寸
        resized_image = self.image.resize(
            (width, height),
            Image.Resampling.LANCZOS  # 高质量重采样
        )

        # 保存
        resized_image.save(output_path)

        logger.info(
            f"✅ 图片尺寸调整: "
            f"{original_width}x{original_height} → {width}x{height}"
        )

        return output_path

    def crop(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        裁剪图片

        Args:
            x: 左上角 X 坐标
            y: 左上角 Y 坐标
            width: 裁剪宽度
            height: 裁剪高度
            output_path: 输出路径

        Returns:
            Path: 裁剪后的文件路径
        """
        if output_path is None:
            output_path = self.image_path

        # 裁剪区域 (left, upper, right, lower)
        crop_box = (x, y, x + width, y + height)
        cropped_image = self.image.crop(crop_box)

        # 保存
        cropped_image.save(output_path)

        logger.info(
            f"✅ 图片裁剪: "
            f"位置({x}, {y}) 尺寸{width}x{height}"
        )

        return output_path

    def crop_center(
        self,
        width: int,
        height: int,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        从中心裁剪图片

        Args:
            width: 裁剪宽度
            height: 裁剪高度
            output_path: 输出路径

        Returns:
            Path: 裁剪后的文件路径
        """
        img_width, img_height = self.image.size

        # 计算中心点
        left = (img_width - width) // 2
        top = (img_height - height) // 2

        return self.crop(left, top, width, height, output_path)

    def add_text_watermark(
        self,
        text: str,
        position: Tuple[int, int] = None,
        font_size: int = 40,
        color: Tuple[int, int, int, int] = (255, 255, 255, 128),
        output_path: Optional[Path] = None
    ) -> Path:
        """
        添加文字水印

        Args:
            text: 水印文字
            position: 水印位置 (x, y)，默认右下角
            font_size: 字体大小
            color: 文字颜色 (R, G, B, A)，A 是透明度
            output_path: 输出路径

        Returns:
            Path: 添加水印后的文件路径
        """
        if output_path is None:
            output_path = self.image_path

        # 转换为 RGBA 模式（支持透明度）
        if self.image.mode != 'RGBA':
            watermarked_image = self.image.convert('RGBA')
        else:
            watermarked_image = self.image.copy()

        # 创建文字层
        text_layer = Image.new('RGBA', watermarked_image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        # 尝试使用系统字体
        try:
            # Windows
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                # Linux
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                # 使用默认字体
                font = ImageFont.load_default()

        # 获取文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 默认位置：右下角，留 20 像素边距
        if position is None:
            img_width, img_height = watermarked_image.size
            position = (
                img_width - text_width - 20,
                img_height - text_height - 20
            )

        # 绘制文字
        draw.text(position, text, fill=color, font=font)

        # 合并图层
        watermarked_image = Image.alpha_composite(watermarked_image, text_layer)

        # 如果原图不是 RGBA，转回原格式
        if self.image.mode != 'RGBA':
            watermarked_image = watermarked_image.convert(self.image.mode)

        # 保存
        watermarked_image.save(output_path)

        logger.info(f"✅ 添加文字水印: {text}")

        return output_path

    def add_image_watermark(
        self,
        watermark_path: Path,
        position: Tuple[int, int] = None,
        opacity: float = 0.5,
        scale: float = 0.2,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        添加图片水印

        Args:
            watermark_path: 水印图片路径
            position: 水印位置 (x, y)，默认右下角
            opacity: 不透明度 (0-1)
            scale: 水印缩放比例（相对于原图）
            output_path: 输出路径

        Returns:
            Path: 添加水印后的文件路径
        """
        if output_path is None:
            output_path = self.image_path

        # 加载水印图片
        watermark = Image.open(watermark_path)

        # 转换为 RGBA
        if self.image.mode != 'RGBA':
            base_image = self.image.convert('RGBA')
        else:
            base_image = self.image.copy()

        if watermark.mode != 'RGBA':
            watermark = watermark.convert('RGBA')

        # 调整水印大小
        img_width, img_height = base_image.size
        wm_width = int(img_width * scale)
        wm_height = int(watermark.size[1] * (wm_width / watermark.size[0]))
        watermark = watermark.resize((wm_width, wm_height), Image.Resampling.LANCZOS)

        # 设置透明度
        alpha = watermark.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        watermark.putalpha(alpha)

        # 默认位置：右下角
        if position is None:
            position = (
                img_width - wm_width - 20,
                img_height - wm_height - 20
            )

        # 粘贴水印
        base_image.paste(watermark, position, watermark)

        # 转回原格式
        if self.image.mode != 'RGBA':
            base_image = base_image.convert(self.image.mode)

        # 保存
        base_image.save(output_path)

        logger.info(f"✅ 添加图片水印: {watermark_path.name}")

        return output_path

    def create_thumbnail(
        self,
        size: Tuple[int, int] = (200, 200),
        output_path: Optional[Path] = None
    ) -> Path:
        """
        创建缩略图

        Args:
            size: 缩略图尺寸 (width, height)
            output_path: 输出路径

        Returns:
            Path: 缩略图文件路径
        """
        if output_path is None:
            # 生成缩略图文件名
            stem = self.image_path.stem
            suffix = self.image_path.suffix
            output_path = self.image_path.parent / f"{stem}_thumb{suffix}"

        # 创建缩略图（保持比例）
        thumbnail = self.image.copy()
        thumbnail.thumbnail(size, Image.Resampling.LANCZOS)

        # 保存
        thumbnail.save(output_path)

        logger.info(
            f"✅ 创建缩略图: "
            f"{self.original_size} → {thumbnail.size}"
        )

        return output_path

    def convert_format(
        self,
        output_format: str,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        转换图片格式

        Args:
            output_format: 目标格式 (JPEG, PNG, WebP, etc.)
            output_path: 输出路径

        Returns:
            Path: 转换后的文件路径
        """
        if output_path is None:
            stem = self.image_path.stem
            output_path = self.image_path.parent / f"{stem}.{output_format.lower()}"

        # 如果是 JPEG，需要转换为 RGB
        if output_format.upper() == 'JPEG' and self.image.mode == 'RGBA':
            rgb_image = Image.new('RGB', self.image.size, (255, 255, 255))
            rgb_image.paste(self.image, mask=self.image.split()[3])
            rgb_image.save(output_path, format=output_format)
        else:
            self.image.save(output_path, format=output_format)

        logger.info(
            f"✅ 格式转换: "
            f"{self.image_path.suffix} → {output_format}"
        )

        return output_path

    def apply_filter(
        self,
        filter_type: str = "BLUR",
        output_path: Optional[Path] = None
    ) -> Path:
        """
        应用图片滤镜

        Args:
            filter_type: 滤镜类型 (BLUR, CONTOUR, DETAIL, SHARPEN, etc.)
            output_path: 输出路径

        Returns:
            Path: 滤镜后的文件路径
        """
        if output_path is None:
            output_path = self.image_path

        # 滤镜映射
        filters = {
            "BLUR": ImageFilter.BLUR,
            "CONTOUR": ImageFilter.CONTOUR,
            "DETAIL": ImageFilter.DETAIL,
            "EDGE_ENHANCE": ImageFilter.EDGE_ENHANCE,
            "EMBOSS": ImageFilter.EMBOSS,
            "SHARPEN": ImageFilter.SHARPEN,
            "SMOOTH": ImageFilter.SMOOTH,
        }

        if filter_type.upper() not in filters:
            raise ValueError(f"不支持的滤镜类型: {filter_type}")

        # 应用滤镜
        filtered_image = self.image.filter(filters[filter_type.upper()])

        # 保存
        filtered_image.save(output_path)

        logger.info(f"✅ 应用滤镜: {filter_type}")

        return output_path


# ============================================================
# 便捷函数
# ============================================================

def compress_image(
    image_path: Path,
    quality: int = 85,
    output_path: Optional[Path] = None
) -> Path:
    """
    快捷压缩图片

    Args:
        image_path: 图片路径
        quality: 压缩质量 (1-100)
        output_path: 输出路径

    Returns:
        Path: 压缩后的文件路径
    """
    processor = ImageProcessor(image_path)
    return processor.compress(quality, output_path)


def create_thumbnail(
    image_path: Path,
    size: Tuple[int, int] = (200, 200),
    output_path: Optional[Path] = None
) -> Path:
    """
    快捷创建缩略图

    Args:
        image_path: 图片路径
        size: 缩略图尺寸
        output_path: 输出路径

    Returns:
        Path: 缩略图文件路径
    """
    processor = ImageProcessor(image_path)
    return processor.create_thumbnail(size, output_path)


# ============================================================
# 学习笔记
# ============================================================
"""
关键概念总结：

1. 【Pillow 基础】
   - 打开图片: Image.open(path)
   - 保存图片: image.save(path)
   - 图片模式:
     - RGB: 彩色（无透明）
     - RGBA: 彩色（有透明）
     - L: 灰度

2. 【图片压缩】
   - quality 参数: 1-100
   - optimize=True: 优化文件大小
   - JPEG 不支持透明度，需转 RGB

3. 【图片调整】
   - resize(): 调整尺寸
   - thumbnail(): 创建缩略图（保持比例）
   - crop(): 裁剪

   重采样方法:
   - LANCZOS: 高质量（推荐）
   - BILINEAR: 中等质量
   - NEAREST: 低质量（快）

4. 【水印】
   文字水印:
   - ImageDraw.text()
   - 使用 RGBA 支持透明度

   图片水印:
   - paste() 方法
   - alpha_composite() 合并图层

5. 【图片格式转换】
   常见格式:
   - JPEG: 有损压缩，文件小
   - PNG: 无损压缩，支持透明
   - WebP: 现代格式，更小

6. 【最佳实践】
   - 处理前检查图片模式
   - JPEG 转换需处理透明度
   - 使用高质量重采样
   - 分块处理大图片
   - 错误处理和日志记录

7. 【性能优化】
   - 批量处理使用多线程
   - 大图片使用流式处理
   - 缓存处理结果
   - 异步处理耗时操作
"""
