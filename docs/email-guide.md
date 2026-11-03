# 邮件发送学习指南

> 中文讲解为主，关键术语保留中英对照。

配套代码：`services/email_service.py`、`api/v1/email.py`、`tasks/email_tasks.py`  
模板：`templates/email/`  
配套测试：`tests/test_email_service.py`、`tests/test_api_email.py`

---

## 1. 本模块落地了什么？

| 学习点 | 状态 | 落点 |
|--------|------|------|
| SMTP 配置（环境变量） | 已落地 | `core/config.py`、`.env.example` |
| aiosmtplib 异步发送 | 已落地 | `services/email_service.py` |
| Jinja2 HTML + 纯文本 | 已落地 | `templates/email/{welcome,verify,password_reset}.*` |
| 邮件附件 | 已落地 | 运行时生成 txt / 最小 PDF，不入库 |
| Celery 队列 | 已落地（可选） | 同一套 `EmailService`；Broker 挂了回退同步 |
| 失败重试 + 日志 | 已落地 | 服务层秒级重试 + Celery 分钟级重试 |
| SendGrid / 阿里云邮件推送 | **未做** | 仍是可选，HTTP API 不是 SMTP |

诚实边界：

- **欢迎信 / 验证信 / 重置密码** 是演示接口，不写用户表、不改密码。
- 完整的「邮箱验证」「忘记密码」业务流还在练习清单里。
- CI **不连真实 SMTP**。没配 `SMTP_HOST` 就 dry-run；单测 mock `aiosmtplib` / `smtp_send`。

---

## 2. 为什么 API 里不要直接 `smtplib`？

标准库 `smtplib` 是**同步阻塞**的。FastAPI 的事件循环被堵住时，别的请求也得等。

```python
# ❌ 卡住整个 worker
import smtplib
smtplib.SMTP("smtp.gmail.com", 587).send_message(msg)

# ✅ 异步
await aiosmtplib.send(msg, hostname="smtp.gmail.com", port=587, start_tls=True)
```

SMTP 往返通常 1–3 秒。生产环境再往外加一层 Celery，让接口先返回。

---

## 3. 配置

环境变量（也可写进 `.env`，不要提交密码）：

```env
SMTP_HOST=""          # 留空 = 自动 dry-run
SMTP_PORT=587
SMTP_USER=""
SMTP_PASSWORD=""
SMTP_FROM="FastAPI Tutorial <noreply@example.com>"
SMTP_STARTTLS=True    # 587 常见
SMTP_USE_TLS=False    # 465 隐式 TLS
SMTP_DRY_RUN=False
EMAIL_FRONTEND_BASE_URL="https://example.com"
```

常见端口：

| 场景 | host | port | STARTTLS | USE_TLS |
|------|------|------|----------|---------|
| Gmail / 企业邮 | smtp.xxx.com | 587 | True | False |
| 隐式 TLS | smtp.xxx.com | 465 | False | True |
| 本机 Mailpit / Mailhog | localhost | 1025 | False | False |

没配主机，或 `SMTP_DRY_RUN=True`：只渲染、组 MIME、打日志，**不连外网**。  
这和 SSE 模块「Redis 挂了走内存」是同一教学思路。

---

## 4. 模板：HTML + 纯文本

邮件客户端经常剥掉 CSS，有的只显示纯文本。所以每封信都是一对：

```text
templates/email/welcome.html
templates/email/welcome.txt
```

Jinja2 填 `username` / `verify_url` / `reset_url`。  
HTML 用**内联 style**（多数邮箱不认外链样式表）。

浏览器预览：

```text
GET /api/v1/email/preview/welcome
GET /api/v1/email/preview/verify?as_json=true
GET /api/v1/email/preview/password_reset?username=alice&token=demo
```

---

## 5. MIME 和附件

一封完整教学邮件的结构：

```text
multipart/mixed
  ├─ multipart/alternative
  │    ├─ text/plain
  │    └─ text/html
  └─ attachment (text/plain 或 application/pdf)
```

附件在内存里生成（`build_demo_attachment`），**不写 `data/uploads/`**，也不往仓库塞 PDF。

---

## 6. 接口

前缀：`/api/v1/email`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/email/` | 否 | 模块说明、SMTP 是否配置、是否 dry-run |
| GET | `/api/v1/email/preview/{name}` | 否 | 预览 HTML；`as_json=true` 同时给纯文本 |
| POST | `/api/v1/email/send` | 是 | 自定义 text/html |
| POST | `/api/v1/email/welcome` | 是 | 欢迎信演示 |
| POST | `/api/v1/email/verify` | 是 | 验证邮箱样式（不写库） |
| POST | `/api/v1/email/password-reset` | 是 | 重置密码样式（不改密码） |
| POST | `/api/v1/email/attachment` | 是 | 带 txt / 最小 PDF |

旧接口 `/api/v1/tasks/email/*` 仍然**只丢 Celery**，用来对比「队列教学」和「真发送」。

请求示例：

```bash
# 先登录拿 token
curl -X POST http://127.0.0.1:8080/api/v1/email/welcome \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"to":"you@example.com","username":"alice"}'
```

没配 SMTP 时响应里会有 `"mode": "dry_run"`，这是成功，不是失败。

---

## 7. Celery：可选，不是门槛

```text
API 默认同步 → EmailService
     │
     ├─ use_queue=false（默认）→ 当时就发 / dry-run
     └─ use_queue=true
            ├─ apply_async 成功 → 返回 task_id
            └─ Redis / Broker 挂了 → 回退同步（CI 仍绿）
```

Celery 任务（`tasks/email_tasks.py`）内部还是 `EmailService`，不再 `time.sleep` 假装发送。

启动 Worker（本机有 Redis 时）：

```bash
celery -A core.celery_app worker -Q email --loglevel=info
```

---

## 8. 失败和重试（两层）

| 层 | 间隔 | 适合 | 不要重试 |
|----|------|------|----------|
| `EmailService` | 0.4s、0.8s… | 超时、断开、SMTP 4xx | 认证失败、收件人拒绝、5xx |
| Celery | 默认 60s，最多 3 次 | Worker 挂了、对端持续失败 | 参数本身就错 |

日志会写：收件人、主题、第几次、是否 dry-run、最终失败原因。  
**不要把 SMTP 密码打进日志。**

---

## 9. 怎么测（必须离线绿）

```bash
pytest tests/test_email_service.py tests/test_api_email.py
```

覆盖：

- 模板渲染出 HTML + 纯文本
- MIME 带附件
- 空 `SMTP_HOST` 走 dry-run，不调用 `aiosmtplib`
- mock 发送函数验证 SMTP 路径
- 超时会重试，认证失败不重试
- 未登录不能 POST
- `use_queue=true` 且 Broker 报错时回退同步
- Celery 任务用 `.run()` 直接调，不需要 Redis

---

## 10. 还没做的（保持可选）

- SendGrid、Mailgun、阿里云邮件推送（HTTP API）
- 注册成功后自动发欢迎信（会改变现有注册语义，留给作业）
- 完整邮箱验证 / 忘记密码（token 落库、过期、一次一用）
- 打开率、退信 webhook、订阅退订

换供应商时，优先替换 `smtp_send`，模板和路由可以不动。

---

## 11. 常见问题

**Q: Swagger 里预览接口返回的是 HTML？**  
A: 默认就是给浏览器看的。加 `?as_json=true` 拿 `{html, text, subject}`。

**Q: 为什么注册接口没有自动发信？**  
A: 现有 `tests/test_api_auth.py` 和教学节奏都不依赖外设。先用 `/email/welcome` 看通路，再自己接到 `UserService.create_user`。

**Q: Gmail 报认证失败？**  
A: 用应用专用密码，不要用登录密码；From 地址要属于该账号。

**Q: 本地不想申请邮箱怎么办？**  
A: 跑 [Mailpit](https://mailpit.axllent.org/)：`SMTP_HOST=localhost SMTP_PORT=1025 SMTP_STARTTLS=False`。
