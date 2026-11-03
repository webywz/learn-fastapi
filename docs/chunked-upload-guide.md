# 大文件分片上传学习指南

> 中文讲解为主，关键术语保留中英对照。

配套代码：`services/chunked_upload_service.py`、`api/v1/chunked_uploads.py`  
数据表：`file_upload_sessions` / `file_upload_parts`  
配套测试：`tests/test_chunked_upload_service.py`、`tests/test_api_chunked_upload.py`

---

## 1. 本模块落地了什么？

| 学习点 | 状态 | 落点 |
|--------|------|------|
| 为什么要分片 | 已落地 | 服务模块顶部注释 + 本文 §2 |
| init / upload-part / complete / abort | 已落地 | `/api/v1/files/chunked/*` |
| 幂等（同一片再传） | 已落地 | `save_part`：checksum 相同则 `reused=true` |
| 整文件 + 单片 SHA-256 | 已落地 | init / part / complete 都可带 checksum |
| 断点续传 | 已落地 | `GET /chunked/{upload_id}` 返回 `missing_parts` |
| 临时目录 + 原子移动 | 已落地 | `data/uploads/.chunks/{id}/` → `os.replace` 到 `uploads/` |
| 过期清理 | 已落地 | 默认 24h TTL；init / cleanup 会扫；也可手动删目录 |
| 单次上传 | **不替换** | `POST /api/v1/files/upload` 仍是小文件路径 |
| OSS / S3 Multipart | **未做** | 流程很像，但是另一套 SDK 和 ETag |

诚实边界：

- 分片完成后写入同一张 `files` 表，下载 / 列表 / 分享 / 审计接口不用改。
- 本课只做**本地磁盘**。`OSS_ENABLED=True` 时，分片路径仍然写本地。
- CI **不上传真正的大文件**。测试用十几字节的假分片证明拼得对。
- 单次上传默认 10MB；分片默认上限 100MB。这是教学数字，不是硬盘配额。

---

## 2. 为什么整文件一次 POST 不够？

| 问题 | 整文件 | 分片 |
|------|--------|------|
| 超时 | Nginx / worker 读超时，200MB 慢网会断 | 每片几 MB，单片超时只重那一片 |
| 内存 | 反向代理可能先把 body 读完 | 应用侧始终只处理一片 |
| 失败 | 传了 90% 也得从头来 | `missing_parts` 里缺啥补啥（续传） |
| 进度 | 只有一个总百分比 | 按片计数，刷新页面还能接着传 |

前端类比：`blob.slice(start, end)` + 多次 `fetch`，而不是一个 `<input type=file>` 直接 POST。

对标生产：AWS S3 / 阿里云 OSS 的 Multipart Upload 也是 init → upload part → complete / abort。本课用磁盘模拟这条状态机，方便以后换 SDK。

---

## 3. 怎么选：单次 vs 分片

```
文件 ≤ 10MB  →  POST /api/v1/files/upload          （简单）
文件更大     →  POST /api/v1/files/chunked/init …  （本模块）
```

分片接口也能传很小的文件（pytest 就是这么做的），只是多一次往返，日常没必要。

MIME 白名单和单次上传相同：图片 / PDF / Word / txt / csv。`.exe` 改个扩展名仍可能混进来——这和单次上传一样，本课不做 `python-magic` 嗅探。

---

## 4. 配置

环境变量（也可写进 `.env`）：

```env
UPLOAD_DIR="data/uploads"
MAX_UPLOAD_SIZE=10485760          # 单次 10MB
CHUNKED_MAX_FILE_SIZE=104857600   # 分片整文件 100MB
CHUNKED_DEFAULT_CHUNK_SIZE=1048576
CHUNKED_MAX_CHUNK_SIZE=5242880
CHUNKED_SESSION_TTL_SECONDS=86400 # 24 小时
```

临时目录：`{UPLOAD_DIR}/.chunks/{upload_id}/part_00001.bin`  
成品：`{UPLOAD_DIR}/{timestamp}_{uuid}_{filename}`  
`.chunks` 已由 `.gitignore` 的 `data/uploads/*` 排除，不要把测试垃圾提交上去。

---

## 5. 接口

前缀：`/api/v1/files`（和原来的文件模块在一起）

| 方法 | 端点 | 登录 | 说明 |
|------|------|------|------|
| GET | `/chunked` | 否 | 模块说明、上限、TTL |
| POST | `/chunked/init` | 是 | 只传元数据，返回 `upload_id` / `total_chunks` |
| GET | `/chunked/{upload_id}` | 是 | 进度；看 `missing_parts` 续传 |
| PUT | `/chunked/{upload_id}/parts/{part_number}` | 是 | `multipart` 字段 `chunk`，可选 `checksum` |
| POST | `/chunked/{upload_id}/complete` | 是 | 拼片、校验、写入 `files` 表 |
| DELETE | `/chunked/{upload_id}` | 是 | 取消，删临时目录 |
| POST | `/chunked/cleanup` | 是 | 把过期 pending 标 expired 并删目录 |

`part_number` 从 **1** 开始（和 S3 一样）。最后一片可以小于 `chunk_size`，前面的片必须刚好等于。

### init

```bash
curl -X POST http://127.0.0.1:8080/api/v1/files/chunked/init \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "lecture.txt",
    "content_type": "text/plain",
    "total_size": 12,
    "chunk_size": 4,
    "checksum": "<整文件 sha256 hex，可选>"
  }'
```

### 传一片

```bash
curl -X PUT "http://127.0.0.1:8080/api/v1/files/chunked/$UPLOAD_ID/parts/1" \
  -H "Authorization: Bearer $TOKEN" \
  -F "chunk=@part1.bin" \
  -F "checksum=<本片 sha256 hex，可选>"
```

同一片、同一 checksum 再 PUT 一次：`reused=true`，不会复制一份。这是断网重试能安全做的原因。

### 完成

```bash
curl -X POST "http://127.0.0.1:8080/api/v1/files/chunked/$UPLOAD_ID/complete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"checksum":"<可选，必须与 init 一致>"}'
```

成功后的 `data` 和单次上传同一套字段（`id` / `url` / `saved_filename` …）。  
再 complete 一次不会复制文件。

---

## 6. 落盘怎么保证不留下半成品？

1. 每一片先写 `part_00001.bin.tmp`，再 `os.replace` 成正式片文件。进程被杀最多丢这一片。
2. complete 时按 1..N 流式拷贝到 `assembled.bin`，核对大小和 SHA-256。
3. `os.replace(assembled, uploads/最终名)`：同一文件系统上这是原子的。
4. 写入 `files` 表和审计日志，然后删掉整个 `.chunks/{upload_id}/`。

不要在正式文件名上边读边 append——中途崩溃会留下「看起来存在、其实不完整」的文件。

---

## 7. 过期会话谁来扫？

默认 24 小时。pending 过期后：

- 下次访问该会话 → 状态改 `expired`，临时目录删除
- `POST /chunked/init` 和 `POST /chunked/cleanup` 会扫一遍过期会话

没有 Celery Beat 也没关系。实在忘了跑接口，可以手动删 `data/uploads/.chunks/` 下的目录；库里的会话下次访问会对不上磁盘，同样按过期处理。

已 complete 的成品走原来的删除接口，abort 动不了它。

---

## 8. 测试（离线、小文件）

```bash
pytest tests/test_chunked_upload_service.py tests/test_api_chunked_upload.py
```

用 4～13 字节的 txt 切成几片，断言：

- 拼出来的字节和原文件一致
- 同一片再传是幂等的
- checksum 错了会拒绝
- 缺片不能 complete
- abort 会删临时目录
- 别人拿不到你的 `upload_id`
- 原来的 `POST /upload` 仍然可用

不要往 CI 里丢几百 MB 的夹具。

---

## 9. 刻意没做的

- 阿里云 OSS `init_multipart` / `upload_part` / `complete_multipart`（ETag 列表）
- 浏览器直传（预签名 URL 把片传到云，不经过应用）
- 并发多片的服务端锁（教学用 SQLite，单 writer）
- 秒传（按整文件 SHA-256 命中已有 `files` 行直接返回）

这些都是合理的下一课作业，不是本 PR 的缺口。
