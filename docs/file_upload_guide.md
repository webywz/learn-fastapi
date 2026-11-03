# 文件上传和处理功能使用指南

## 📚 目录

1. [安装依赖](#安装依赖)
2. [基础文件上传](#基础文件上传)
3. [图片处理](#图片处理)
4. [API 端点列表](#api-端点列表)
5. [使用示例](#使用示例)
6. [错误处理](#错误处理)

---

## 安装依赖

### 1. 安装 Pillow（图片处理库）

```bash
pip install Pillow
```

### 2. 启动服务

```bash
python main.py
```

服务将运行在 `http://localhost:8080`

### 3. 访问 API 文档

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

---

## 基础文件上传

### 支持的文件类型

| 类型 | MIME Type | 扩展名 |
|------|-----------|--------|
| 图片 | image/jpeg | .jpg, .jpeg |
| 图片 | image/png | .png |
| 图片 | image/gif | .gif |
| 图片 | image/webp | .webp |
| 文档 | application/pdf | .pdf |
| 文档 | application/msword | .doc |
| 文档 | application/vnd.openxmlformats-officedocument.wordprocessingml.document | .docx |
| 文本 | text/plain | .txt |
| 文本 | text/csv | .csv |

### 文件大小限制

- 最大文件大小：10 MB
- 超过限制会自动拒绝

---

## 图片处理

### 功能列表

1. **图片压缩** - 减小文件大小
2. **尺寸调整** - 缩放图片
3. **图片裁剪** - 裁剪指定区域
4. **文字水印** - 添加版权保护
5. **缩略图** - 生成预览图

---

## API 端点列表

### 文件上传

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/files/upload` | 上传单个文件 |
| POST | `/api/v1/files/upload/multiple` | 批量上传文件 |
| GET | `/api/v1/files/list` | 获取文件列表（分页） |
| POST | `/api/v1/files/chunked/init` | 初始化分片上传 |
| PUT | `/api/v1/files/chunked/{upload_id}/parts/{n}` | 上传一个分片 |
| POST | `/api/v1/files/chunked/{upload_id}/complete` | 完成分片并写入文件表 |
| DELETE | `/api/v1/files/chunked/{upload_id}` | 取消分片上传 |

### 文件下载

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/files/download/{filename}` | 下载文件 |
| GET | `/api/v1/files/stream/{filename}` | 流式下载（大文件） |

### 文件管理

| 方法 | 端点 | 说明 |
|------|------|------|
| DELETE | `/api/v1/files/delete/{filename}` | 删除文件 |

### 图片处理

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/files/image/compress` | 压缩图片 |
| POST | `/api/v1/files/image/resize` | 调整尺寸 |
| POST | `/api/v1/files/image/crop` | 裁剪图片 |
| POST | `/api/v1/files/image/watermark/text` | 添加文字水印 |
| POST | `/api/v1/files/image/thumbnail` | 生成缩略图 |

---

## 使用示例

### 1. 上传单个文件

#### cURL

```bash
curl -X POST "http://localhost:8080/api/v1/files/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/image.jpg"
```

#### Python

```python
import requests

url = "http://localhost:8080/api/v1/files/upload"
files = {'file': open('image.jpg', 'rb')}

response = requests.post(url, files=files)
print(response.json())
```

#### JavaScript (Fetch API)

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8080/api/v1/files/upload', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

#### 响应示例

```json
{
  "code": 0,
  "message": "文件上传成功",
  "data": {
    "filename": "image.jpg",
    "saved_filename": "20231226_a1b2c3d4_image.jpg",
    "content_type": "image/jpeg",
    "size": 245678,
    "url": "/api/v1/files/download/20231226_a1b2c3d4_image.jpg"
  }
}
```

---

### 2. 批量上传文件

#### cURL

```bash
curl -X POST "http://localhost:8080/api/v1/files/upload/multiple" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@image1.jpg" \
  -F "files=@image2.png" \
  -F "files=@document.pdf"
```

#### Python

```python
import requests

url = "http://localhost:8080/api/v1/files/upload/multiple"
files = [
    ('files', open('image1.jpg', 'rb')),
    ('files', open('image2.png', 'rb')),
    ('files', open('document.pdf', 'rb'))
]

response = requests.post(url, files=files)
print(response.json())
```

---

### 3. 压缩图片

#### cURL

```bash
curl -X POST "http://localhost:8080/api/v1/files/image/compress?quality=85" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@large_image.jpg"
```

#### Python

```python
import requests

url = "http://localhost:8080/api/v1/files/image/compress"
params = {'quality': 85}
files = {'file': open('large_image.jpg', 'rb')}

response = requests.post(url, params=params, files=files)
print(response.json())
```

#### 响应示例

```json
{
  "code": 0,
  "message": "图片压缩成功",
  "data": {
    "filename": "large_image.jpg",
    "compressed_filename": "compressed_20231226_a1b2c3d4_large_image.jpg",
    "original_size": 2456789,
    "compressed_size": 456789,
    "compression_ratio": "81.4%",
    "quality": 85,
    "url": "/api/v1/files/download/compressed_20231226_a1b2c3d4_large_image.jpg"
  }
}
```

---

### 4. 调整图片尺寸

#### 按宽度缩放（高度自适应）

```bash
curl -X POST "http://localhost:8080/api/v1/files/image/resize?width=800" \
  -F "file=@image.jpg"
```

#### 按高度缩放（宽度自适应）

```bash
curl -X POST "http://localhost:8080/api/v1/files/image/resize?height=600" \
  -F "file=@image.jpg"
```

#### 指定宽高（保持比例）

```bash
curl -X POST "http://localhost:8080/api/v1/files/image/resize?width=800&height=600&keep_ratio=true" \
  -F "file=@image.jpg"
```

#### Python 示例

```python
import requests

url = "http://localhost:8080/api/v1/files/image/resize"
params = {
    'width': 800,
    'height': 600,
    'keep_ratio': True
}
files = {'file': open('image.jpg', 'rb')}

response = requests.post(url, params=params, files=files)
print(response.json())
```

---

### 5. 裁剪图片

#### 居中裁剪（生成头像）

```bash
curl -X POST "http://localhost:8080/api/v1/files/image/crop?width=200&height=200" \
  -F "file=@photo.jpg"
```

#### 指定位置裁剪

```bash
curl -X POST "http://localhost:8080/api/v1/files/image/crop?width=300&height=200&x=100&y=50" \
  -F "file=@photo.jpg"
```

#### Python 示例

```python
import requests

url = "http://localhost:8080/api/v1/files/image/crop"

# 居中裁剪
params = {'width': 200, 'height': 200}
files = {'file': open('photo.jpg', 'rb')}

response = requests.post(url, params=params, files=files)
print(response.json())
```

---

### 6. 添加文字水印

#### cURL

```bash
curl -X POST "http://localhost:8080/api/v1/files/image/watermark/text?text=Copyright%202023&font_size=40&opacity=128" \
  -F "file=@image.jpg"
```

#### Python 示例

```python
import requests

url = "http://localhost:8080/api/v1/files/image/watermark/text"
params = {
    'text': 'Copyright © 2023',
    'font_size': 40,
    'opacity': 128  # 0-255
}
files = {'file': open('image.jpg', 'rb')}

response = requests.post(url, params=params, files=files)
print(response.json())
```

---

### 7. 生成缩略图

#### cURL

```bash
curl -X POST "http://localhost:8080/api/v1/files/image/thumbnail?size=200" \
  -F "file=@large_photo.jpg"
```

#### Python 示例

```python
import requests

url = "http://localhost:8080/api/v1/files/image/thumbnail"
params = {'size': 200}  # 200x200 像素
files = {'file': open('large_photo.jpg', 'rb')}

response = requests.post(url, params=params, files=files)
print(response.json())
```

#### 响应示例

```json
{
  "code": 0,
  "message": "缩略图生成成功",
  "data": {
    "filename": "large_photo.jpg",
    "original_filename": "20231226_a1b2c3d4_large_photo.jpg",
    "thumbnail_filename": "20231226_a1b2c3d4_large_photo_thumb.jpg",
    "original_size": 2456789,
    "thumbnail_size": 12345,
    "original_url": "/api/v1/files/download/20231226_a1b2c3d4_large_photo.jpg",
    "thumbnail_url": "/api/v1/files/download/20231226_a1b2c3d4_large_photo_thumb.jpg"
  }
}
```

---

### 8. 下载文件

#### 直接下载

```bash
curl -O "http://localhost:8080/api/v1/files/download/20231226_a1b2c3d4_image.jpg"
```

#### 流式下载（大文件）

```bash
curl -O "http://localhost:8080/api/v1/files/stream/20231226_a1b2c3d4_large_file.zip"
```

#### Python 示例

```python
import requests

url = "http://localhost:8080/api/v1/files/download/20231226_a1b2c3d4_image.jpg"
response = requests.get(url)

# 保存文件
with open('downloaded_image.jpg', 'wb') as f:
    f.write(response.content)
```

---

### 9. 获取文件列表

#### cURL

```bash
curl "http://localhost:8080/api/v1/files/list?page=1&page_size=10"
```

#### Python 示例

```python
import requests

url = "http://localhost:8080/api/v1/files/list"
params = {'page': 1, 'page_size': 10}

response = requests.get(url, params=params)
print(response.json())
```

#### 响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "files": [
      {
        "filename": "20231226_a1b2c3d4_image.jpg",
        "size": 245678,
        "created_at": "2023-12-26T10:30:00",
        "modified_at": "2023-12-26T10:30:00",
        "url": "/api/v1/files/download/20231226_a1b2c3d4_image.jpg"
      }
    ],
    "total": 25,
    "page": 1,
    "page_size": 10,
    "total_pages": 3
  }
}
```

---

### 10. 删除文件

#### cURL

```bash
curl -X DELETE "http://localhost:8080/api/v1/files/delete/20231226_a1b2c3d4_image.jpg"
```

#### Python 示例

```python
import requests

url = "http://localhost:8080/api/v1/files/delete/20231226_a1b2c3d4_image.jpg"
response = requests.delete(url)
print(response.json())
```

---

## 错误处理

### 常见错误码

| 状态码 | 错误信息 | 说明 |
|--------|----------|------|
| 400 | 不支持的文件类型 | 文件类型不在允许列表中 |
| 400 | 文件大小超过限制 | 文件超过 10 MB |
| 404 | 文件不存在 | 请求的文件未找到 |
| 500 | 文件保存失败 | 服务器内部错误 |
| 500 | 图片处理功能不可用 | Pillow 未安装 |

### 错误响应示例

```json
{
  "detail": "不支持的文件类型: application/x-msdownload"
}
```

---

## 最佳实践

### 1. 文件上传

- **验证文件类型**：在客户端和服务端都进行验证
- **限制文件大小**：避免上传过大的文件
- **显示上传进度**：提升用户体验

### 2. 图片处理

- **压缩质量选择**：
  - Web 展示：quality=85（推荐）
  - 高质量打印：quality=95
  - 缩略图：quality=70

- **尺寸调整**：
  - 保持宽高比避免变形
  - 不要放大图片（会降低质量）

- **水印位置**：
  - 默认右下角
  - 避免遮挡重要内容

### 3. 性能优化

- 使用缩略图进行列表展示
- 大文件使用流式下载
- 考虑使用 CDN 加速文件访问

---

## 完整示例：图片上传和处理流程

```python
import requests

# 1. 上传原始图片
upload_url = "http://localhost:8080/api/v1/files/upload"
files = {'file': open('photo.jpg', 'rb')}
upload_response = requests.post(upload_url, files=files)
original_file = upload_response.json()['data']['saved_filename']

print(f"✅ 上传成功: {original_file}")

# 2. 压缩图片（用于网页展示）
compress_url = "http://localhost:8080/api/v1/files/image/compress"
params = {'quality': 85}
files = {'file': open('photo.jpg', 'rb')}
compress_response = requests.post(compress_url, params=params, files=files)
compressed_file = compress_response.json()['data']['compressed_filename']

print(f"✅ 压缩成功: {compressed_file}")

# 3. 生成缩略图（用于列表展示）
thumbnail_url = "http://localhost:8080/api/v1/files/image/thumbnail"
params = {'size': 200}
files = {'file': open('photo.jpg', 'rb')}
thumbnail_response = requests.post(thumbnail_url, params=params, files=files)
thumbnail_file = thumbnail_response.json()['data']['thumbnail_filename']

print(f"✅ 缩略图生成成功: {thumbnail_file}")

# 4. 添加水印（用于版权保护）
watermark_url = "http://localhost:8080/api/v1/files/image/watermark/text"
params = {
    'text': '© MyWebsite 2023',
    'font_size': 30,
    'opacity': 128
}
files = {'file': open('photo.jpg', 'rb')}
watermark_response = requests.post(watermark_url, params=params, files=files)
watermarked_file = watermark_response.json()['data']['watermarked_filename']

print(f"✅ 水印添加成功: {watermarked_file}")

print("\n📊 处理结果：")
print(f"原图: /api/v1/files/download/{original_file}")
print(f"压缩版: /api/v1/files/download/{compressed_file}")
print(f"缩略图: /api/v1/files/download/{thumbnail_file}")
print(f"水印版: /api/v1/files/download/{watermarked_file}")
```

---

## 下一步学习

- ✅ 大文件分片上传（见 `docs/chunked-upload-guide.md`）
- ✅ 文件分享链接（签名 URL）
- ⏭️ 云存储 OSS Multipart（和本地分片状态机类似，未接 SDK）
- ⏭️ 图片 CDN 加速
- ⏭️ 异步处理和队列

---

## 常见问题 (FAQ)

### Q1: 如何修改文件大小限制？

修改 `api/v1/files.py` 中的 `MAX_FILE_SIZE` 常量：

```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
```

### Q2: 如何添加新的文件类型支持？

修改 `ALLOWED_MIME_TYPES` 字典：

```python
ALLOWED_MIME_TYPES = {
    # ... 现有类型
    "video/mp4": [".mp4"],
    "application/zip": [".zip"]
}
```

### Q3: 图片处理失败怎么办？

确保已安装 Pillow：

```bash
pip install Pillow
```

### Q4: 如何自定义水印位置？

当前版本水印固定在右下角。如需自定义位置，可以修改 `utils/image_processor.py` 中的 `add_text_watermark` 方法，将 `position` 参数暴露到 API。

---

## 技术支持

- API 文档：http://localhost:8080/docs
- 项目仓库：[GitHub](https://github.com/your-repo)
- 问题反馈：[Issues](https://github.com/your-repo/issues)
