"""
文件上传功能测试脚本

使用方法：
1. 确保 FastAPI 服务已启动：python main.py
2. 准备一张测试图片：test_image.jpg
3. 运行此脚本：python scripts/test_file_upload.py
"""

import requests
import json
from pathlib import Path
from PIL import Image, ImageDraw
import io


# API 基础 URL
BASE_URL = "http://localhost:8080/api/v1/files"


def print_response(title, response):
    """打印响应结果"""
    print(f"\n{'='*60}")
    print(f"📌 {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")

    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text[:200]}")


def create_test_image(filename="test_image.jpg", size=(800, 600)):
    """创建一个测试图片"""
    print(f"\n🎨 创建测试图片: {filename} ({size[0]}x{size[1]})")

    # 创建彩色渐变图片
    image = Image.new('RGB', size)
    draw = ImageDraw.Draw(image)

    # 绘制渐变背景
    for i in range(size[1]):
        color_value = int(255 * (i / size[1]))
        draw.rectangle(
            [(0, i), (size[0], i+1)],
            fill=(color_value, 100, 255-color_value)
        )

    # 添加文字
    draw.text((50, 50), "Test Image", fill=(255, 255, 255))

    # 保存
    image.save(filename)
    print(f"✅ 测试图片已创建: {filename}")

    return filename


def test_1_upload_single_file():
    """测试1：上传单个文件"""
    print("\n" + "="*60)
    print("测试 1: 上传单个文件")
    print("="*60)

    # 创建测试图片
    test_file = create_test_image("test_upload_1.jpg")

    # 上传
    url = f"{BASE_URL}/upload"
    files = {'file': open(test_file, 'rb')}

    response = requests.post(url, files=files)
    print_response("上传单个文件", response)

    # 清理
    Path(test_file).unlink()

    return response.json()


def test_2_upload_multiple_files():
    """测试2：批量上传文件"""
    print("\n" + "="*60)
    print("测试 2: 批量上传文件")
    print("="*60)

    # 创建多个测试图片
    test_files = []
    for i in range(3):
        filename = f"test_upload_{i+2}.jpg"
        create_test_image(filename, size=(400, 300))
        test_files.append(filename)

    # 批量上传
    url = f"{BASE_URL}/upload/multiple"
    files = [('files', open(f, 'rb')) for f in test_files]

    response = requests.post(url, files=files)
    print_response("批量上传文件", response)

    # 清理
    for f in test_files:
        Path(f).unlink()

    return response.json()


def test_3_compress_image():
    """测试3：压缩图片"""
    print("\n" + "="*60)
    print("测试 3: 压缩图片")
    print("="*60)

    # 创建较大的测试图片
    test_file = create_test_image("test_compress.jpg", size=(2000, 1500))

    # 压缩（质量 85）
    url = f"{BASE_URL}/image/compress"
    params = {'quality': 85}
    files = {'file': open(test_file, 'rb')}

    response = requests.post(url, params=params, files=files)
    print_response("压缩图片 (quality=85)", response)

    # 清理
    Path(test_file).unlink()

    return response.json()


def test_4_resize_image():
    """测试4：调整图片尺寸"""
    print("\n" + "="*60)
    print("测试 4: 调整图片尺寸")
    print("="*60)

    test_file = create_test_image("test_resize.jpg", size=(1200, 800))

    # 调整尺寸（宽度 600，保持比例）
    url = f"{BASE_URL}/image/resize"
    params = {
        'width': 600,
        'keep_ratio': True
    }
    files = {'file': open(test_file, 'rb')}

    response = requests.post(url, params=params, files=files)
    print_response("调整图片尺寸 (width=600, keep_ratio=True)", response)

    # 清理
    Path(test_file).unlink()

    return response.json()


def test_5_crop_image():
    """测试5：裁剪图片"""
    print("\n" + "="*60)
    print("测试 5: 裁剪图片（居中）")
    print("="*60)

    test_file = create_test_image("test_crop.jpg", size=(1000, 800))

    # 居中裁剪为正方形（用于头像）
    url = f"{BASE_URL}/image/crop"
    params = {
        'width': 400,
        'height': 400
    }
    files = {'file': open(test_file, 'rb')}

    response = requests.post(url, params=params, files=files)
    print_response("裁剪图片 (400x400, 居中)", response)

    # 清理
    Path(test_file).unlink()

    return response.json()


def test_6_add_watermark():
    """测试6：添加文字水印"""
    print("\n" + "="*60)
    print("测试 6: 添加文字水印")
    print("="*60)

    test_file = create_test_image("test_watermark.jpg", size=(800, 600))

    # 添加水印
    url = f"{BASE_URL}/image/watermark/text"
    params = {
        'text': '© FastAPI Tutorial 2023',
        'font_size': 40,
        'opacity': 128
    }
    files = {'file': open(test_file, 'rb')}

    response = requests.post(url, params=params, files=files)
    print_response("添加文字水印", response)

    # 清理
    Path(test_file).unlink()

    return response.json()


def test_7_create_thumbnail():
    """测试7：生成缩略图"""
    print("\n" + "="*60)
    print("测试 7: 生成缩略图")
    print("="*60)

    test_file = create_test_image("test_thumbnail.jpg", size=(1200, 900))

    # 生成缩略图
    url = f"{BASE_URL}/image/thumbnail"
    params = {'size': 200}
    files = {'file': open(test_file, 'rb')}

    response = requests.post(url, params=params, files=files)
    print_response("生成缩略图 (200x200)", response)

    # 清理
    Path(test_file).unlink()

    return response.json()


def test_8_list_files():
    """测试8：获取文件列表"""
    print("\n" + "="*60)
    print("测试 8: 获取文件列表")
    print("="*60)

    url = f"{BASE_URL}/list"
    params = {
        'page': 1,
        'page_size': 10
    }

    response = requests.get(url, params=params)
    print_response("获取文件列表", response)

    return response.json()


def test_9_download_file(filename):
    """测试9：下载文件"""
    print("\n" + "="*60)
    print("测试 9: 下载文件")
    print("="*60)

    url = f"{BASE_URL}/download/{filename}"

    response = requests.get(url)

    if response.status_code == 200:
        # 保存到本地
        output_path = f"downloaded_{filename}"
        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f"✅ 文件已下载: {output_path} ({len(response.content)} bytes)")

        # 清理
        Path(output_path).unlink()
    else:
        print(f"❌ 下载失败: {response.status_code}")

    return response


def test_10_delete_file(filename):
    """测试10：删除文件"""
    print("\n" + "="*60)
    print("测试 10: 删除文件")
    print("="*60)

    url = f"{BASE_URL}/delete/{filename}"

    response = requests.delete(url)
    print_response("删除文件", response)

    return response.json()


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("🚀 开始文件上传功能测试")
    print("="*60)

    try:
        # 测试 1: 上传单个文件
        result1 = test_1_upload_single_file()
        uploaded_filename = result1['data']['saved_filename']

        # 测试 2: 批量上传
        test_2_upload_multiple_files()

        # 测试 3: 压缩图片
        result3 = test_3_compress_image()
        compressed_filename = result3['data']['compressed_filename']

        # 测试 4: 调整尺寸
        test_4_resize_image()

        # 测试 5: 裁剪图片
        test_5_crop_image()

        # 测试 6: 添加水印
        test_6_add_watermark()

        # 测试 7: 生成缩略图
        test_7_create_thumbnail()

        # 测试 8: 获取文件列表
        test_8_list_files()

        # 测试 9: 下载文件
        test_9_download_file(uploaded_filename)

        # 测试 10: 删除文件
        test_10_delete_file(uploaded_filename)
        test_10_delete_file(compressed_filename)

        print("\n")
        print("="*60)
        print("✅ 所有测试完成！")
        print("="*60)

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误: 无法连接到服务器")
        print("请确保 FastAPI 服务已启动：python main.py")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
