"""
===========================================
邮件发送服务 (Email Service)
===========================================

作用：
  把「渲染模板 → 组装 MIME → 异步 SMTP 发送」收成一层。
  API 和 Celery 任务都调用这里，避免两边各写一份 SMTP。

为什么发邮件要单独做一层？
  1. SMTP 往返通常 1-3 秒，API 里同步硬等会拖慢接口
  2. 同一封欢迎信：演示接口要同步可测，生产再丢给 Celery
  3. 模板 / 附件 / 重试 / 日志集中在一处，方便单测 mock

发送路径（两层，不要混为一谈）：

  ┌────────────┬──────────────────────────┬──────────────────────┐
  │            │ 服务层（本文件）           │ Celery 任务层         │
  ├────────────┼──────────────────────────┼──────────────────────┤
  │ 时机       │ 同一次请求内              │ Worker 重新消费       │
  │ 间隔       │ 0.4s、0.8s…（秒级）       │ default_retry_delay   │
  │ 适合       │ 网络闪断、SMTP 暂时 4xx   │ Worker 挂了、持续失败 │
  │ 不重试     │ 5xx 永久错、认证失败      │ 业务参数本身就错      │
  └────────────┴──────────────────────────┴──────────────────────┘

离线 / CI：
  SMTP_HOST 为空 或 SMTP_DRY_RUN=True → 只组包打日志，不连外网。
  测试里把 smtp_send 换成 AsyncMock，断言参数，不需要真实 SMTP。

类比前端：
  - Jinja2 模板 ≈ React 组件：同一套 HTML，填不同 props
  - 纯文本 fallback ≈ 没有 CSS 时的降级文案
  - dry-run ≈ 开发环境 console.log，不真的调第三方
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Literal, Optional, Sequence

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from common.error_codes import ErrorCode
from common.exceptions import BusinessException, ValidationException
from core.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 模板目录 / Jinja2
# ============================================================
#
# 邮件 HTML 和网页 HTML 不是一回事：
#   - 多数客户端不认 <style> 外链，要写内联 style
#   - 必须同时给纯文本：有人关了 HTML，垃圾箱策略也更友好
#   - 模板很小，同步 render 足够；别为了「看起来异步」去开 Jinja enable_async
#

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "email"

TEMPLATE_NAMES = ("welcome", "verify", "password_reset")
TemplateName = Literal["welcome", "verify", "password_reset"]

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


# ============================================================
# 附件：运行时生成，不进仓库、不写 data/uploads
# ============================================================
#
# 教学只要证明 MIME multipart 能挂上附件。
# 一个几十字节的 txt、一个带 %PDF 头的最小文档就够，
# 不要把真实 PDF / 图片提交进 git。
#

DEMO_TEXT_FILENAME = "fastapi-email-demo.txt"
DEMO_PDF_FILENAME = "fastapi-email-demo.pdf"

# 最小可被大多数阅读器识别的 PDF（Helvetia 一行字，无外部资源）
MINIMAL_PDF_BYTES = (
    b"%PDF-1.1\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 360 144]"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 70>>stream\n"
    b"BT /F1 14 Tf 24 80 Td (FastAPI email attachment demo) Tj ET\n"
    b"endstream\nendobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


@dataclass(frozen=True)
class EmailAttachment:
    """一封邮件上的一个附件（内存里的字节，不落盘）。"""

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class RenderedEmail:
    """模板渲染结果：HTML + 纯文本必须成对出现。"""

    subject: str
    text: str
    html: str
    template: str
    context: dict[str, Any]


@dataclass
class SendResult:
    """发送（或 dry-run）之后给 API / Celery 的统一回执。"""

    to: list[str]
    subject: str
    mode: Literal["smtp", "dry_run"]
    message_id: str
    template: Optional[str] = None
    attachments: list[str] = field(default_factory=list)
    attempts: int = 1


# 可在测试里替换：AsyncMock(return_value=None)
SmtpSendFn = Callable[[EmailMessage], Awaitable[None]]


async def smtp_send(message: EmailMessage) -> None:
    """
    真正调用 aiosmtplib 的地方（也是测试 mock 的缝）。

    为什么抽成模块级函数？
      EmailService 里重试 / 组包逻辑不需要知道「怎么连上 SMTP」。
      pytest 只要 monkeypatch 这一个名字，就不会打到外网。
    """
    username = settings.SMTP_USER or None
    password = settings.SMTP_PASSWORD or None

    # aiosmtplib 5.x: use_tls=隐式 TLS；start_tls=连上后再升级
    # 两者互斥。本地 Mailpit(1025) 两个都关。
    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=username,
        password=password,
        start_tls=settings.SMTP_STARTTLS and not settings.SMTP_USE_TLS,
        use_tls=settings.SMTP_USE_TLS,
        timeout=settings.SMTP_TIMEOUT,
    )


def build_demo_attachment(kind: Literal["text", "pdf"] = "text") -> EmailAttachment:
    """运行时造一个很小的教学附件。"""
    if kind == "pdf":
        return EmailAttachment(
            filename=DEMO_PDF_FILENAME,
            content=MINIMAL_PDF_BYTES,
            content_type="application/pdf",
        )
    body = (
        "这是 FastAPI 邮件教学附件，运行时生成，不写入 data/uploads。\n"
        "如果你在收件箱里看到这个 txt，说明 MIME multipart 已经组好了。\n"
    ).encode("utf-8")
    return EmailAttachment(
        filename=DEMO_TEXT_FILENAME,
        content=body,
        content_type="text/plain; charset=utf-8",
    )


def _is_retryable(exc: BaseException) -> bool:
    """
    哪些错值得立刻再试一次？

    不重试（再试也没用）：
      - 认证失败（账号/密码/应用专用密码错了）
      - 收件人被拒绝（地址不存在，5xx）
      - SMTP 5xx 永久错误

    重试（多半是瞬时的）：
      - 连不上、超时、连接被掐
      - SMTP 4xx（服务忙、临时拒绝）
    """
    if isinstance(exc, aiosmtplib.SMTPAuthenticationError):
        return False
    if isinstance(exc, aiosmtplib.SMTPRecipientsRefused):
        return False
    if isinstance(exc, aiosmtplib.SMTPResponseException):
        # 4xx = 临时；5xx = 永久（别把密码错误循环打上去）
        return 400 <= exc.code < 500
    return isinstance(
        exc,
        (
            OSError,
            TimeoutError,
            asyncio.TimeoutError,
            aiosmtplib.SMTPConnectError,
            aiosmtplib.SMTPTimeoutError,
            aiosmtplib.SMTPServerDisconnected,
            aiosmtplib.SMTPException,
        ),
    )


def _as_recipients(to: str | Sequence[str]) -> list[str]:
    if isinstance(to, str):
        recipients = [to]
    else:
        recipients = list(to)
    cleaned = [item.strip() for item in recipients if item and item.strip()]
    if not cleaned:
        raise ValidationException(
            ErrorCode.EMAIL_PAYLOAD_INVALID,
            message="至少需要一个收件人",
        )
    return cleaned


def build_message(
    *,
    to: str | Sequence[str],
    subject: str,
    text: str,
    html: Optional[str] = None,
    attachments: Optional[Iterable[EmailAttachment]] = None,
    sender: Optional[str] = None,
) -> EmailMessage:
    """
    组装一封 multipart 邮件。

    结构（从外到内）：
      mixed
        ├─ alternative
        │    ├─ text/plain     ← 纯文本 fallback，必须有
        │    └─ text/html      ← 有模板时才加
        └─ attachment...       ← 可选

    EmailMessage.set_content / add_alternative / add_attachment
    会按上面的顺序自动升级 multipart，不用手写 MIMEMultipart。
    """
    recipients = _as_recipients(to)
    if not subject.strip():
        raise ValidationException(
            ErrorCode.EMAIL_PAYLOAD_INVALID,
            message="邮件主题不能为空",
        )
    if not (text and text.strip()) and not (html and html.strip()):
        raise ValidationException(
            ErrorCode.EMAIL_PAYLOAD_INVALID,
            message="邮件正文不能为空（至少要有 text 或 html）",
        )

    message = EmailMessage()
    message["From"] = sender or settings.SMTP_FROM
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject.strip()
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain="learn-fastapi.local")

    plain = text.strip() if text and text.strip() else "请使用支持 HTML 的客户端查看这封邮件。"
    message.set_content(plain, charset="utf-8")
    if html and html.strip():
        message.add_alternative(html, subtype="html", charset="utf-8")

    for item in attachments or []:
        maintype, _, subtype = item.content_type.partition("/")
        if not subtype:
            maintype, subtype = "application", "octet-stream"
        # Content-Type 可能带 "; charset=utf-8"，附件头只要主类型
        subtype = subtype.split(";", 1)[0].strip()
        message.add_attachment(
            item.content,
            maintype=maintype or "application",
            subtype=subtype,
            filename=item.filename,
        )
    return message


def default_template_context(
    template: TemplateName,
    *,
    username: str = "同学",
    token: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """欢迎 / 验证 / 重置密码 共用的演示上下文。"""
    token = token or secrets.token_urlsafe(16)
    base = settings.EMAIL_FRONTEND_BASE_URL.rstrip("/")
    context: dict[str, Any] = {
        "app_name": settings.APP_NAME,
        "username": username,
        "token": token,
        "verify_url": f"{base}/verify-email?token={token}",
        "reset_url": f"{base}/reset-password?token={token}",
        "support_email": "support@example.com",
    }
    if extra:
        context.update(extra)
    return context


def render_template(
    template: str,
    context: Optional[dict[str, Any]] = None,
) -> RenderedEmail:
    """
    渲染一对模板：{name}.html + {name}.txt。

    主题放在 HTML 模板顶部的 {# subject: ... #} 注释里，
    避免再维护一份 subject 映射表。纯文本模板没有这行也没关系。
    """
    if template not in TEMPLATE_NAMES:
        raise BusinessException(
            ErrorCode.EMAIL_TEMPLATE_NOT_FOUND,
            message=f"未知邮件模板: {template}（可选: {', '.join(TEMPLATE_NAMES)}）",
        )

    data = context or default_template_context(template)  # type: ignore[arg-type]
    try:
        html_template = jinja_env.get_template(f"{template}.html")
        text_template = jinja_env.get_template(f"{template}.txt")
    except TemplateNotFound as exc:
        raise BusinessException(
            ErrorCode.EMAIL_TEMPLATE_NOT_FOUND,
            message=f"缺少模板文件: {exc}",
        ) from exc

    html = html_template.render(**data)
    text = text_template.render(**data)
    subject = _subject_from_template(template, data)
    return RenderedEmail(
        subject=subject,
        text=text,
        html=html,
        template=template,
        context=data,
    )


def _subject_from_template(template: str, context: dict[str, Any]) -> str:
    subjects = {
        "welcome": f"欢迎加入 {context.get('app_name', settings.APP_NAME)}",
        "verify": "请验证你的邮箱",
        "password_reset": "重置你的密码",
    }
    return subjects[template]


class EmailService:
    """
    邮件业务入口。

    API 层调用 send / send_template；
    Celery 任务用 run_async(...) 包一层同步调用。
    """

    @staticmethod
    async def send(
        *,
        to: str | Sequence[str],
        subject: str,
        text: str,
        html: Optional[str] = None,
        attachments: Optional[Sequence[EmailAttachment]] = None,
        template: Optional[str] = None,
        sender: Optional[str] = None,
        smtp_send_fn: Optional[SmtpSendFn] = None,
    ) -> SendResult:
        recipients = _as_recipients(to)
        message = build_message(
            to=recipients,
            subject=subject,
            text=text,
            html=html,
            attachments=attachments,
            sender=sender,
        )
        message_id = str(message["Message-ID"] or "")
        attachment_names = [item.filename for item in (attachments or [])]
        send_fn = smtp_send_fn or smtp_send

        if settings.SMTP_SHOULD_DRY_RUN:
            logger.info(
                "邮件 dry-run（未连 SMTP）to=%s subject=%s template=%s attachments=%s",
                recipients,
                subject,
                template,
                attachment_names,
            )
            return SendResult(
                to=recipients,
                subject=subject,
                mode="dry_run",
                message_id=message_id,
                template=template,
                attachments=attachment_names,
                attempts=1,
            )

        max_tries = settings.SMTP_MAX_RETRIES + 1
        last_error: Optional[BaseException] = None
        for attempt in range(1, max_tries + 1):
            try:
                logger.info(
                    "邮件发送中 attempt=%s/%s to=%s subject=%s template=%s",
                    attempt,
                    max_tries,
                    recipients,
                    subject,
                    template,
                )
                await send_fn(message)
                logger.info(
                    "邮件发送成功 attempt=%s to=%s message_id=%s",
                    attempt,
                    recipients,
                    message_id,
                )
                return SendResult(
                    to=recipients,
                    subject=subject,
                    mode="smtp",
                    message_id=message_id,
                    template=template,
                    attachments=attachment_names,
                    attempts=attempt,
                )
            except Exception as exc:  # noqa: BLE001 — 要区分可否重试
                last_error = exc
                retryable = _is_retryable(exc)
                logger.warning(
                    "邮件发送失败 attempt=%s/%s retryable=%s to=%s error=%s",
                    attempt,
                    max_tries,
                    retryable,
                    recipients,
                    exc,
                )
                if not retryable or attempt >= max_tries:
                    break
                await asyncio.sleep(settings.SMTP_RETRY_BACKOFF * attempt)

        logger.error(
            "邮件最终失败 to=%s subject=%s error=%s",
            recipients,
            subject,
            last_error,
        )
        raise BusinessException(
            ErrorCode.EMAIL_SEND_FAILED,
            message=f"邮件发送失败: {last_error}",
        )

    @staticmethod
    async def send_template(
        template: TemplateName,
        *,
        to: str | Sequence[str],
        username: str = "同学",
        token: Optional[str] = None,
        extra_context: Optional[dict[str, Any]] = None,
        attachments: Optional[Sequence[EmailAttachment]] = None,
        smtp_send_fn: Optional[SmtpSendFn] = None,
    ) -> SendResult:
        """渲染指定模板再发送。欢迎 / 验证 / 重置密码都走这里。"""
        context = default_template_context(
            template,
            username=username,
            token=token,
            extra=extra_context,
        )
        rendered = render_template(template, context)
        return await EmailService.send(
            to=to,
            subject=rendered.subject,
            text=rendered.text,
            html=rendered.html,
            attachments=attachments,
            template=template,
            smtp_send_fn=smtp_send_fn,
        )

    @staticmethod
    def result_to_dict(result: SendResult) -> dict[str, Any]:
        return {
            "to": result.to,
            "subject": result.subject,
            "mode": result.mode,
            "message_id": result.message_id,
            "template": result.template,
            "attachments": result.attachments,
            "attempts": result.attempts,
            "smtp_configured": settings.SMTP_CONFIGURED,
            "dry_run": result.mode == "dry_run",
        }


# ============================================================
# 学习笔记
# ============================================================
"""
1. 【为什么 API 里不要直接 smtplib】
   标准库 smtplib 是同步阻塞的。FastAPI 的事件循环会被卡住，
   这期间别的请求也跑不动。aiosmtplib 才是 async/await。

2. 【HTML + 纯文本】
   multipart/alternative 让客户端自己挑。只发 HTML 的后果：
   纯文本客户端空白、部分反垃圾策略加分更差。

3. 【重试分层】
   - 服务层：这次请求内立刻再试（SMTP 抖动）
   - Celery：任务重新入队（进程挂了、持续失败）
   5xx / 认证失败不要重试，否则会把错误密码打爆对方。

4. 【测试怎么离线】
   monkeypatch services.email_service.smtp_send
   或调用时传入 smtp_send_fn=AsyncMock()
   不要在 CI 里连 Gmail。

5. 【第三方服务】
   SendGrid / 阿里云邮件推送走 HTTP API，不是 SMTP。
   本模块只覆盖 SMTP。换供应商时，替换 smtp_send 即可，
   模板和 API 不用动。
"""
