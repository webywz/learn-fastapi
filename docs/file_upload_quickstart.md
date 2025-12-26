# 文件上传功能快速开始

## 🎯 已实现的功能

### ✅ 基础功能
- [x] FastAPI 文件上传（UploadFile）
- [x] 文件类型验证（MIME type）
- [x] 文件大小限制（10 MB）
- [x] 本地存储（保存到磁盘）
- [x] 文件下载（流式传输）

### ✅ 图片处理
- [x] 图片压缩（Pillow）
- [x] 尺寸调整（缩放）
- [x] 图片裁剪（居中/指定位置）
- [x] 添加文字水印
- [x] 生成缩略图

### ⏭️ 待实现功能
- [ ] 云存储集成（阿里云 OSS / AWS S3）
- [ ] 大文件分片上传
- [ ] 文件 URL 签名（防盗链）

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装图片处理库
pip install Pillow
```

### 2. 启动服务

```bash
# 方式1：直接运行
python main.py

# 方式2：使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### 3. 访问 API 文档

在浏览器中打开：
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

### 4. 测试功能

运行测试脚本：

```bash
python scripts/test_file_upload.py
```

---

## 📁 项目结构

```
learn-fastapi/
├── api/
│   └── v1/
│       └── files.py          # 文件上传路由
├── utils/
│   └── image_processor.py    # 图片处理工具
├── data/
│   └── uploads/              # 上传文件存储目录
├── docs/
│   ├── file_upload_guide.md  # 详细使用文档
│   └── file_upload_quickstart.md  # 快速开始（本文件）
├── scripts/
│   └── test_file_upload.py   # 测试脚本
└── main.py                   # 主应用
```

---

## 🔗 主要 API 端点

### 文件上传
- `POST /api/v1/files/upload` - 上传单个文件
- `POST /api/v1/files/upload/multiple` - 批量上传

### 图片处理
- `POST /api/v1/files/image/compress` - 压缩图片
- `POST /api/v1/files/image/resize` - 调整尺寸
- `POST /api/v1/files/image/crop` - 裁剪图片
- `POST /api/v1/files/image/watermark/text` - 添加水印
- `POST /api/v1/files/image/thumbnail` - 生成缩略图

### 文件管理
- `GET /api/v1/files/list` - 获取文件列表
- `GET /api/v1/files/download/{filename}` - 下载文件
- `DELETE /api/v1/files/delete/{filename}` - 删除文件

---

## 💡 快速示例

### 上传并压缩图片

```python
import requests

# 1. 上传图片
url = "http://localhost:8080/api/v1/files/upload"
files = {'file': open('photo.jpg', 'rb')}
response = requests.post(url, files=files)
print(response.json())

# 2. 压缩图片
url = "http://localhost:8080/api/v1/files/image/compress"
params = {'quality': 85}
files = {'file': open('photo.jpg', 'rb')}
response = requests.post(url, params=params, files=files)
print(response.json())
```

### 生成缩略图

```python
import requests

url = "http://localhost:8080/api/v1/files/image/thumbnail"
params = {'size': 200}
files = {'file': open('photo.jpg', 'rb')}

response = requests.post(url, params=params, files=files)
data = response.json()

print(f"原图: {data['data']['original_url']}")
print(f"缩略图: {data['data']['thumbnail_url']}")
```

---

## 📚 学习资源

- **详细文档**: `docs/file_upload_guide.md`
- **API 文档**: http://localhost:8080/docs
- **源代码**:
  - 路由实现: `api/v1/files.py`
  - 图片处理: `utils/image_processor.py`

---

## 🎓 学习要点

### 1. FastAPI 文件上传

```python
from fastapi import UploadFile, File

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # 读取文件
    content = await file.read()

    # 获取文件信息
    filename = file.filename
    content_type = file.content_type

    return {"filename": filename}
```

**关键点：**
- 使用 `UploadFile` 而不是 `bytes`（更高效）
- `async/await` 处理文件读写
- 分块读取大文件

### 2. 文件类型验证

```python
ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"]
}

def validate_file_type(file: UploadFile) -> bool:
    # 验证 MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        return False

    # 验证扩展名
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = ALLOWED_MIME_TYPES[file.content_type]

    return file_ext in allowed_extensions
```

**安全要点：**
- 同时验证 MIME type 和扩展名
- 不信任客户端提供的文件名
- 生成唯一文件名避免冲突

### 3. 图片处理（Pillow）

```python
from PIL import Image

# 打开图片
image = Image.open("photo.jpg")

# 压缩
image.save("compressed.jpg", quality=85, optimize=True)

# 调整尺寸
resized = image.resize((800, 600), Image.Resampling.LANCZOS)

# 裁剪
cropped = image.crop((100, 100, 400, 400))

# 生成缩略图
image.thumbnail((200, 200), Image.Resampling.LANCZOS)
```

**最佳实践：**
- 使用 LANCZOS 重采样（高质量）
- 压缩质量选择 85（平衡质量和大小）
- 处理 RGBA → RGB 转换（JPEG 不支持透明）

### 4. 流式文件下载

```python
from fastapi.responses import StreamingResponse

def file_iterator():
    with open(file_path, "rb") as file:
        while chunk := file.read(1024 * 1024):  # 1MB chunks
            yield chunk

return StreamingResponse(
    file_iterator(),
    media_type="application/octet-stream"
)
```

**优势：**
- 内存占用小（适合大文件）
- 支持断点续传
- 更好的用户体验

---

## 🔧 常见配置

### 修改文件大小限制

编辑 `api/v1/files.py`:

```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 改为 50 MB
```

### 添加新文件类型

编辑 `api/v1/files.py`:

```python
ALLOWED_MIME_TYPES = {
    # ... 现有类型
    "video/mp4": [".mp4"],           # 视频
    "application/zip": [".zip"],     # 压缩包
}
```

### 修改上传目录

编辑 `api/v1/files.py`:

```python
UPLOAD_DIR = Path("data/uploads")  # 修改为你的目录
```

---

## ⚠️ 注意事项

1. **Pillow 依赖**
   - 图片处理功能需要 Pillow
   - 未安装时会自动跳过，不影响基础上传

2. **文件存储**
   - 当前使用本地存储
   - 生产环境建议使用云存储（OSS/S3）

3. **安全性**
   - 已实现基础验证
   - 建议添加认证和授权
   - 限制上传频率（防滥用）

4. **性能**
   - 大文件处理建议异步队列
   - 考虑使用 CDN 加速下载

---

## 🎯 下一步

1. **学习云存储集成**
   - 阿里云 OSS
   - AWS S3
   - 本地存储 vs 云存储对比

2. **实现大文件上传**
   - 分片上传
   - 断点续传
   - 上传进度追踪

3. **增强安全性**
   - 文件 URL 签名
   - 防盗链
   - 访问权限控制

---

## 📞 帮助与支持

- 📖 完整文档: `docs/file_upload_guide.md`
- 🔧 测试脚本: `scripts/test_file_upload.py`
- 📝 API 文档: http://localhost:8080/docs

祝学习愉快！🎉
