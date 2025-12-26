# 阿里云 OSS 集成 - 快速开始

## ✅ 已完成的集成

恭喜！阿里云 OSS 已经成功集成到你的 FastAPI 项目中。

### 🎯 功能概览

- ✅ 文件上传到 OSS
- ✅ 自动生成唯一文件名
- ✅ 支持本地存储和 OSS 存储切换
- ✅ 文件访问 URL 生成
- ✅ 签名 URL（防盗链）
- ✅ 文件列表和管理

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install oss2
```

### 2. 配置已完成

配置示例（请替换为你自己的密钥）：

```bash
OSS_ENABLED=True
OSS_ACCESS_KEY_ID="你的 AccessKey ID"
OSS_ACCESS_KEY_SECRET="你的 AccessKey Secret"
OSS_REGION="oss-cn-beijing"
OSS_BUCKET="你的 Bucket 名称"
OSS_ENDPOINT="oss-cn-beijing.aliyuncs.com"
OSS_PATH_PREFIX="uploads/"
OSS_USE_SSL=True
```

⚠️ **重要安全提醒：**
- 请使用你自己的阿里云 AccessKey
- 不要将 `.env` 文件提交到 Git
- 确保 `.gitignore` 包含 `.env`
- 定期轮换密钥以确保安全

### 3. 启动服务

```bash
python main.py
```

看到以下信息说明 OSS 已成功初始化：

```
✅ OSS 客户端初始化成功: ywzstore (oss-cn-beijing.aliyuncs.com)
```

### 4. 测试上传

#### 方式 1：使用 API 文档测试

1. 打开浏览器访问：http://localhost:8080/docs
2. 找到 `POST /api/v1/files/upload`
3. 点击 "Try it out"
4. 选择文件并上传
5. 查看返回的 OSS URL

#### 方式 2：使用 cURL

```bash
curl -X POST "http://localhost:8080/api/v1/files/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.jpg"
```

#### 方式 3：使用 Python

```python
import requests

url = "http://localhost:8080/api/v1/files/upload"
files = {'file': open('test.jpg', 'rb')}

response = requests.post(url, files=files)
result = response.json()

print("上传结果：")
print(f"存储方式: {result['data']['storage']}")  # oss
print(f"访问地址: {result['data']['url']}")
```

### 5. 验证 OSS 上传

上传成功后，返回的 URL 类似：

```
https://ywzstore.oss-cn-beijing.aliyuncs.com/uploads/2023/12/26/20231226_abc123_test.jpg
```

在浏览器中打开这个 URL，应该能看到你上传的文件。

---

## 📁 项目结构

```
learn-fastapi/
├── api/
│   └── v1/
│       └── files.py              # 文件上传路由（已集成 OSS）
├── utils/
│   ├── oss_client.py             # OSS 客户端（新增）
│   └── image_processor.py        # 图片处理工具
├── core/
│   └── config.py                 # 配置文件（已添加 OSS 配置）
├── docs/
│   ├── oss_integration_guide.md  # OSS 集成详细文档
│   ├── OSS_README.md             # 本文件
│   └── file_upload_guide.md      # 文件上传文档
├── .env                          # 环境配置（已添加 OSS 配置）
└── main.py                       # 主应用
```

---

## 🎮 功能演示

### 上传文件到 OSS

```python
import requests

# 上传文件
url = "http://localhost:8080/api/v1/files/upload"
files = {'file': open('photo.jpg', 'rb')}
response = requests.post(url, files=files)

result = response.json()

# 打印结果
print(f"""
✅ 上传成功！

文件名: {result['data']['filename']}
保存名: {result['data']['saved_filename']}
大小: {result['data']['size']} bytes
类型: {result['data']['content_type']}
存储: {result['data']['storage']}
URL: {result['data']['url']}
""")
```

### 使用 OSS 客户端

```python
from utils.oss_client import get_oss_client
from pathlib import Path

# 获取客户端
oss = get_oss_client()

# 上传文件
file_url = oss.upload_file(Path("photo.jpg"))
print(f"文件 URL: {file_url}")

# 生成签名 URL（1 小时有效）
object_key = "uploads/2023/12/26/photo.jpg"
signed_url = oss.generate_signed_url(object_key, expires=3600)
print(f"签名 URL: {signed_url}")

# 列出文件
files = oss.list_files(prefix="uploads/2023/12/", max_keys=10)
for file in files:
    print(f"- {file['key']} ({file['size']} bytes)")
```

---

## ⚙️ 切换存储方式

### 使用 OSS 存储

编辑 `.env` 文件：

```bash
OSS_ENABLED=True
```

重启服务，文件将上传到 OSS。

### 使用本地存储

编辑 `.env` 文件：

```bash
OSS_ENABLED=False
```

重启服务，文件将保存到 `data/uploads/` 目录。

---

## 📊 对比测试

### 测试脚本

```python
import requests
import time

url = "http://localhost:8080/api/v1/files/upload"

# 测试上传
files = {'file': open('test.jpg', 'rb')}
start = time.time()
response = requests.post(url, files=files)
elapsed = time.time() - start

result = response.json()
storage = result['data']['storage']

print(f"""
📊 上传测试结果

存储方式: {storage}
上传耗时: {elapsed:.2f} 秒
文件大小: {result['data']['size'] / 1024:.2f} KB
访问地址: {result['data']['url']}
""")
```

---

## 🔒 安全建议

### 1. 轮换 AccessKey

由于密钥已暴露，建议：

1. 登录阿里云控制台
2. 进入 AccessKey 管理
3. 禁用当前密钥
4. 创建新密钥
5. 更新 `.env` 文件

### 2. 使用 RAM 子账号

不要使用主账号的 AccessKey！

1. 创建 RAM 用户
2. 仅授予 OSS 权限
3. 使用 RAM 用户的 AccessKey

### 3. 设置 Bucket 权限

根据需求选择：

- **私有**：最安全，使用签名 URL 访问
- **公共读**：适合公开图片，但要防盗链
- **公共读写**：⚠️ 不推荐，有安全风险

### 4. 配置防盗链

1. 进入 OSS 控制台
2. 选择 Bucket → 权限管理 → 防盗链
3. 设置 Referer 白名单

---

## 💰 成本估算

### 阿里云 OSS 价格（华北2-北京，2023年）

| 项目 | 价格 | 说明 |
|------|------|------|
| 标准存储 | ¥0.12/GB/月 | 经常访问的数据 |
| 低频访问 | ¥0.08/GB/月 | 不常访问的数据 |
| 流量费 | ¥0.50/GB | 外网下行流量 |
| API 请求 | ¥0.01/万次 | PUT 请求 |

### 每月成本示例

假设：
- 存储 100 GB 图片
- 每月下载流量 500 GB
- 10万次 PUT 请求

```
存储费用: 100 GB × ¥0.12 = ¥12
流量费用: 500 GB × ¥0.50 = ¥250
请求费用: 10 万次 × ¥0.01 = ¥1

总计: ¥263/月
```

### 优化建议

1. **启用 CDN**：降低流量费用 60%+
2. **压缩图片**：减少存储和流量
3. **生命周期规则**：自动转换存储类型
4. **设置防盗链**：避免盗用流量

---

## 📚 文档索引

- **OSS 集成详细文档**：`docs/oss_integration_guide.md`
- **文件上传使用指南**：`docs/file_upload_guide.md`
- **快速开始**：`docs/file_upload_quickstart.md`
- **API 文档**：http://localhost:8080/docs

---

## 🐛 常见问题

### Q: 上传时提示 "OSS 功能不可用"

**A:** 安装 oss2 库

```bash
pip install oss2
```

### Q: 上传成功但无法访问

**A:** 检查 Bucket 权限设置

1. OSS 控制台 → 选择 Bucket
2. 权限管理 → 读写权限
3. 设置为"公共读"或使用签名 URL

### Q: 如何知道文件上传到哪里了？

**A:** 查看返回数据中的 `storage` 字段

- `"storage": "oss"` - 已上传到 OSS
- `"storage": "local"` - 保存在本地

### Q: 本地测试用 OSS 会花钱吗？

**A:** 会产生少量费用

- 存储费用极低（GB/月 ¥0.12）
- 主要是流量费用
- 建议先在本地测试，确认无误后再启用 OSS

---

## ✅ 下一步

现在你已经成功集成了 OSS，可以继续学习：

1. ✅ **图片处理后上传 OSS**
   - 压缩后上传
   - 水印后上传
   - 多尺寸上传

2. ⏭️ **大文件分片上传**
   - 支持断点续传
   - 上传进度显示

3. ⏭️ **CDN 加速**
   - 绑定自定义域名
   - 配置 HTTPS
   - 缓存策略

4. ⏭️ **图床应用**
   - 拖拽上传
   - 图片管理
   - 分享链接

---

## 🎉 恭喜

你已经成功集成了阿里云 OSS！

现在你的应用拥有：
- ✅ 无限存储空间
- ✅ 高可用性（99.9%）
- ✅ CDN 加速能力
- ✅ 生产级文件存储方案

继续探索更多功能吧！🚀
