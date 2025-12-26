# 阿里云 OSS 集成指南

## 📚 目录

1. [什么是 OSS](#什么是-oss)
2. [安装配置](#安装配置)
3. [使用说明](#使用说明)
4. [API 示例](#api-示例)
5. [切换存储方式](#切换存储方式)
6. [常见问题](#常见问题)
7. [最佳实践](#最佳实践)

---

## 什么是 OSS

### OSS（Object Storage Service）对象存储服务

阿里云 OSS 是一种海量、安全、低成本、高可靠的云存储服务。

**主要特点：**
- ✅ 容量无限制
- ✅ 99.9% 可用性
- ✅ 支持 CDN 加速
- ✅ 按量付费，成本低
- ✅ 自动备份和容灾

**vs 本地存储：**

| 特性 | 本地存储 | OSS 存储 |
|------|----------|----------|
| 容量 | 有限 | 无限 |
| 可靠性 | 依赖服务器 | 99.9% SLA |
| 访问速度 | 快（同机房）| 可用 CDN 加速 |
| 扩展性 | 困难 | 自动扩展 |
| 成本 | 存储成本高 | 按量付费，低成本 |
| 适用场景 | 开发/小型项目 | 生产/大规模应用 |

---

## 安装配置

### 1. 安装依赖

```bash
pip install oss2
```

### 2. 获取 OSS 凭证

登录阿里云控制台：https://oss.console.aliyun.com

#### Step 1: 创建 Bucket

1. 进入 OSS 控制台
2. 点击"创建 Bucket"
3. 填写基本信息：
   - Bucket 名称：例如 `my-app-files`
   - 地域：选择离用户最近的地域
   - 存储类型：标准存储
   - 读写权限：私有（推荐）或公共读

#### Step 2: 获取 AccessKey

1. 点击右上角头像 → AccessKey 管理
2. 创建 AccessKey（推荐使用 RAM 子账号）
3. 记录：
   - AccessKey ID
   - AccessKey Secret（⚠️ 只显示一次，请妥善保管）

### 3. 配置项目

#### 方式 1：编辑 `.env` 文件（推荐）

```bash
# ========================================
# 阿里云 OSS 配置
# ========================================

# 启用 OSS（True=OSS, False=本地）
OSS_ENABLED=True

# OSS 凭证
OSS_ACCESS_KEY_ID="你的 AccessKey ID"
OSS_ACCESS_KEY_SECRET="你的 AccessKey Secret"

# OSS 配置
OSS_REGION="oss-cn-beijing"
OSS_BUCKET="你的 Bucket 名称"
OSS_ENDPOINT="oss-cn-beijing.aliyuncs.com"
OSS_PATH_PREFIX="uploads/"
OSS_USE_SSL=True

# 自定义域名（可选）
# OSS_DOMAIN="cdn.yourdomain.com"
```

#### 方式 2：环境变量

```bash
# Linux / macOS
export OSS_ENABLED=True
export OSS_ACCESS_KEY_ID="xxx"
export OSS_ACCESS_KEY_SECRET="xxx"

# Windows
set OSS_ENABLED=True
set OSS_ACCESS_KEY_ID=xxx
set OSS_ACCESS_KEY_SECRET=xxx
```

### 4. 地域节点对照表

| 地域 | Endpoint |
|------|----------|
| 华北2（北京） | oss-cn-beijing.aliyuncs.com |
| 华东1（杭州） | oss-cn-hangzhou.aliyuncs.com |
| 华东2（上海） | oss-cn-shanghai.aliyuncs.com |
| 华南1（深圳） | oss-cn-shenzhen.aliyuncs.com |
| 香港 | oss-cn-hongkong.aliyuncs.com |
| 美国（硅谷）| oss-us-west-1.aliyuncs.com |

更多节点：https://help.aliyun.com/document_detail/31837.html

---

## 使用说明

### 启动服务

```bash
python main.py
```

启动时会看到：

```
✅ OSS 客户端初始化成功: ywzstore (oss-cn-beijing.aliyuncs.com)
```

### 文件上传流程

1. **启用 OSS 时**（`OSS_ENABLED=True`）：
   - 文件直接上传到阿里云 OSS
   - 返回 OSS 公网 URL
   - 不占用服务器存储空间

2. **禁用 OSS 时**（`OSS_ENABLED=False`）：
   - 文件保存到本地 `data/uploads/` 目录
   - 返回本地下载 URL
   - 占用服务器磁盘空间

---

## API 示例

### 1. 上传文件到 OSS

#### cURL

```bash
curl -X POST "http://localhost:8080/api/v1/files/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@photo.jpg"
```

#### Python

```python
import requests

url = "http://localhost:8080/api/v1/files/upload"
files = {'file': open('photo.jpg', 'rb')}

response = requests.post(url, files=files)
result = response.json()

print(result)
```

#### 响应示例（OSS）

```json
{
  "code": 0,
  "message": "文件上传成功（OSS）",
  "data": {
    "filename": "photo.jpg",
    "saved_filename": "20231226_a1b2c3d4_photo.jpg",
    "content_type": "image/jpeg",
    "size": 245678,
    "url": "https://ywzstore.oss-cn-beijing.aliyuncs.com/uploads/2023/12/26/20231226_a1b2c3d4_photo.jpg",
    "storage": "oss"
  }
}
```

#### 响应示例（本地）

```json
{
  "code": 0,
  "message": "文件上传成功（本地）",
  "data": {
    "filename": "photo.jpg",
    "saved_filename": "20231226_a1b2c3d4_photo.jpg",
    "content_type": "image/jpeg",
    "size": 245678,
    "url": "/api/v1/files/download/20231226_a1b2c3d4_photo.jpg",
    "storage": "local"
  }
}
```

### 2. 访问上传的文件

#### OSS 文件访问

直接通过 OSS URL 访问：

```
https://ywzstore.oss-cn-beijing.aliyuncs.com/uploads/2023/12/26/photo.jpg
```

#### 本地文件访问

通过 API 下载：

```
http://localhost:8080/api/v1/files/download/photo.jpg
```

---

## 切换存储方式

### 从本地存储切换到 OSS

1. **安装 OSS SDK**

```bash
pip install oss2
```

2. **配置 .env 文件**

```bash
OSS_ENABLED=True
OSS_ACCESS_KEY_ID="你的 ID"
OSS_ACCESS_KEY_SECRET="你的 Secret"
OSS_BUCKET="你的 Bucket"
OSS_ENDPOINT="oss-cn-beijing.aliyuncs.com"
```

3. **重启服务**

```bash
# 停止服务（Ctrl+C）
# 重新启动
python main.py
```

4. **测试上传**

```bash
curl -X POST "http://localhost:8080/api/v1/files/upload" \
  -F "file=@test.jpg"
```

### 从 OSS 切换回本地存储

修改 `.env`：

```bash
OSS_ENABLED=False
```

重启服务即可。

---

## 常见问题

### Q1: 上传时提示 "OSS 功能不可用"

**原因：** oss2 库未安装

**解决：**

```bash
pip install oss2
```

### Q2: 提示 "InvalidAccessKeyId"

**原因：** AccessKey ID 错误或不存在

**解决：**
1. 检查 `.env` 文件中的 `OSS_ACCESS_KEY_ID` 是否正确
2. 登录阿里云控制台验证 AccessKey

### Q3: 提示 "SignatureDoesNotMatch"

**原因：** AccessKey Secret 错误

**解决：**
1. 检查 `.env` 文件中的 `OSS_ACCESS_KEY_SECRET`
2. 确保没有多余的空格或引号

### Q4: 上传成功但无法访问文件

**原因：** Bucket 权限设置为私有

**解决：**

**方式 1：** 设置 Bucket 为公共读
1. 进入 OSS 控制台
2. 选择 Bucket → 权限管理
3. 设置读写权限为 "公共读"

**方式 2：** 使用签名 URL（推荐）

```python
from utils.oss_client import get_oss_client

oss = get_oss_client()
# 生成 1 小时有效的签名 URL
signed_url = oss.generate_signed_url(
    "uploads/2023/12/26/photo.jpg",
    expires=3600
)
```

### Q5: 上传速度慢

**原因：** 地域选择不当或网络问题

**解决：**
1. 选择离用户最近的 OSS 地域
2. 启用 CDN 加速
3. 使用内网 Endpoint（服务器在阿里云时）

### Q6: 如何迁移已有的本地文件到 OSS？

**方法：** 使用 OSS 客户端批量上传

```python
from pathlib import Path
from utils.oss_client import get_oss_client

oss = get_oss_client()
upload_dir = Path("data/uploads")

for file_path in upload_dir.glob("**/*"):
    if file_path.is_file():
        print(f"上传: {file_path}")
        oss.upload_file(file_path, file_path.name)
```

---

## 最佳实践

### 1. 安全性

#### ✅ 使用 RAM 子账号

不要使用主账号的 AccessKey！

1. 进入 RAM 控制台
2. 创建 RAM 用户
3. 仅授予 OSS 权限
4. 使用 RAM 用户的 AccessKey

#### ✅ 密钥管理

- 不要把密钥提交到 Git
- 使用环境变量或密钥管理服务
- 定期轮换密钥

#### ✅ Bucket 权限

- 默认使用"私有"权限
- 需要公开访问时使用签名 URL
- 配置防盗链和 IP 白名单

### 2. 成本优化

#### 选择合适的存储类型

| 存储类型 | 使用场景 | 价格 |
|----------|----------|------|
| 标准存储 | 经常访问 | 高 |
| 低频访问 | 不常访问 | 中 |
| 归档存储 | 冷数据 | 低 |

#### 生命周期规则

自动转换或删除过期文件：

```
规则示例：
- 30 天后转为低频访问
- 90 天后转为归档存储
- 180 天后删除
```

#### 开启 CDN

- 减少 OSS 回源流量
- 提升访问速度
- 降低流量费用

### 3. 性能优化

#### 文件组织

```
uploads/
├── 2023/
│   ├── 12/
│   │   ├── 26/
│   │   │   ├── image1.jpg
│   │   │   └── image2.png
```

好处：
- 避免单目录文件过多
- 便于管理和清理
- 提升列举性能

#### 压缩图片

上传前压缩：

```python
# 压缩后再上传
compressed_image = compress_image("photo.jpg", quality=85)
oss.upload_file(compressed_image)
```

#### 使用 CDN

绑定自定义域名并开启 CDN：

```bash
# .env 配置
OSS_DOMAIN="cdn.yourdomain.com"
```

### 4. 监控和告警

#### 开启日志审计

- 记录所有访问日志
- 监控异常访问
- 定期审计

#### 设置费用告警

- 进入费用中心
- 设置每日/每月预算
- 超额自动告警

---

## 代码示例

### 完整上传流程

```python
import requests

# 1. 上传文件到 OSS
url = "http://localhost:8080/api/v1/files/upload"
files = {'file': open('photo.jpg', 'rb')}
response = requests.post(url, files=files)

result = response.json()
file_url = result['data']['url']
storage = result['data']['storage']

print(f"✅ 文件上传成功！")
print(f"存储方式: {storage}")
print(f"访问地址: {file_url}")

# 2. 访问文件
if storage == "oss":
    print(f"直接访问: {file_url}")
else:
    print(f"通过 API 访问: http://localhost:8080{file_url}")
```

### 直接使用 OSS 客户端

```python
from utils.oss_client import get_oss_client
from pathlib import Path

# 获取 OSS 客户端
oss = get_oss_client()

# 1. 上传文件
file_url = oss.upload_file(Path("photo.jpg"))
print(f"文件 URL: {file_url}")

# 2. 下载文件
oss.download_file("uploads/2023/12/26/photo.jpg", Path("downloaded.jpg"))

# 3. 删除文件
oss.delete_file("uploads/2023/12/26/photo.jpg")

# 4. 检查文件是否存在
exists = oss.file_exists("uploads/2023/12/26/photo.jpg")
print(f"文件存在: {exists}")

# 5. 生成签名 URL（1 小时有效）
signed_url = oss.generate_signed_url(
    "uploads/2023/12/26/photo.jpg",
    expires=3600
)
print(f"签名 URL: {signed_url}")

# 6. 列出文件
files = oss.list_files(prefix="uploads/2023/12/", max_keys=100)
for file in files:
    print(f"{file['key']} - {file['size']} bytes")
```

---

## 下一步

- ✅ OSS 基础集成
- ⏭️ 图片处理后上传 OSS
- ⏭️ 大文件分片上传
- ⏭️ 视频转码和处理
- ⏭️ CDN 加速配置

---

## 参考资料

- [阿里云 OSS 官方文档](https://help.aliyun.com/product/31815.html)
- [Python SDK 文档](https://help.aliyun.com/document_detail/32026.html)
- [OSS 定价](https://www.aliyun.com/price/product#/oss/detail)

---

## 技术支持

- 阿里云工单：https://workorder.console.aliyun.com/
- 项目 Issues：GitHub Issues
- 在线文档：http://localhost:8080/docs
