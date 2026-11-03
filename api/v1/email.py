"""
===========================================
邮件教学路由 (Email Demo API)
===========================================

作用：
  演示「真的发一封邮件」需要的几块：
    配置 → 模板 → MIME（HTML + 纯文本 + 附件）→ SMTP / 队列

和旧的 /api/v1/tasks/email/* 的关系：
  - tasks 接口：只负责「丢给 Celery」，Broker 挂了就会失败
  - 本模块：默认同步走 EmailService（CI / 没 Redis 也能测）
    传 use_queue=true 才尝试 Celery；连不上 Broker 会回退同步发送

认证：
  - GET / 和 GET /preview/* 公开（方便浏览器看模板）
  - POST 发送类接口需要登录，避免被当成开放中继

类比前端：
  - preview ≈ 打开邮件的 Storybook
  - dry-run ≈ 开发环境只打日志，不调第三方
  - use_queue ≈ 把耗时请求丢进 Web Worker，失败再回退主线程
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from api.deps import get_current_user
from common.error_codes import ErrorCode
from common.exceptions import BusinessException
from common.response import success
from core.config import settings
from models.user import User
from schemas.email import (
    AttachmentEmailRequest,
    EmailSendRequest,
    PasswordResetEmailRequest,
    VerifyEmailRequest,
    WelcomeEmailRequest,
)
from services.email_service import (
    TEMPLATE_NAMES,
    EmailService,
    SendResult,
    build_demo_attachment,
    render_template,
    default_template_context,
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================
# Celery 可选封装：Broker 挂了必须还能走同步
# ============================================================

def _enqueue_or_none(task_name: str, kwargs: dict[str, Any]) -> Optional[str]:
    """
    尝试把任务丢进现有 Celery 队列。

    成功：返回 task_id
    失败（没 Redis、Broker 超时、任务没注册）：返回 None，调用方改走同步。
    """
    try:
        from tasks.email_tasks import (
            send_email,
            send_password_reset_email,
            send_templated_email,
            send_welcome_email,
        )
    except Exception as exc:  # pragma: no cover - 导入失败极少见
        logger.warning("无法导入邮件 Celery 任务，回退同步: %s", exc)
        return None

    task_map = {
        "send_email": send_email,
        "send_welcome_email": send_welcome_email,
        "send_password_reset_email": send_password_reset_email,
        "send_templated_email": send_templated_email,
    }
    task = task_map.get(task_name)
    if task is None:
        return None

    try:
        async_result = task.apply_async(kwargs=kwargs, queue="email")
        return async_result.id
    except Exception as exc:
        logger.warning("Celery 入队失败，回退同步发送: %s", exc)
        return None


async def _maybe_queue(
    *,
    use_queue: bool,
    task_name: str,
    kwargs: dict[str, Any],
    send: Callable[[], Awaitable[SendResult]],
) -> dict[str, Any]:
    if use_queue:
        task_id = _enqueue_or_none(task_name, kwargs)
        if task_id:
            return {
                "queued": True,
                "task_id": task_id,
                "queue": "email",
                "fallback": None,
                "message": "已提交到 Celery email 队列，可用 /api/v1/tasks/status/{task_id} 查询",
            }
        logger.info("use_queue=true 但 Broker 不可用，改为同步发送")

    result: SendResult = await send()
    payload = EmailService.result_to_dict(result)
    payload.update(
        {
            "queued": False,
            "task_id": None,
            "fallback": "sync" if use_queue else None,
            "message": (
                "Celery 不可用，已同步发送（dry-run 或 SMTP）"
                if use_queue
                else "已同步处理（未走队列）"
            ),
        }
    )
    return payload


# ============================================================
# 公开：模块说明 + 模板预览
# ============================================================

@router.get("/", summary="邮件模块说明")
async def email_overview():
    """
    教学说明（统一 JSON 信封）。

    用来回答：SMTP 配了没、有哪些模板、哪些接口要登录。
    """
    return success(
        data={
            "module": "email",
            "transport": "aiosmtplib",
            "templates": list(TEMPLATE_NAMES),
            "smtp": {
                "configured": settings.SMTP_CONFIGURED,
                "host": settings.SMTP_HOST or None,
                "port": settings.SMTP_PORT,
                "from": settings.SMTP_FROM,
                "starttls": settings.SMTP_STARTTLS,
                "use_tls": settings.SMTP_USE_TLS,
                "dry_run": settings.SMTP_SHOULD_DRY_RUN,
            },
            "endpoints": {
                "preview": "GET /api/v1/email/preview/{welcome|verify|password_reset}",
                "send": "POST /api/v1/email/send",
                "welcome": "POST /api/v1/email/welcome",
                "verify": "POST /api/v1/email/verify",
                "password_reset": "POST /api/v1/email/password-reset",
                "attachment": "POST /api/v1/email/attachment",
            },
            "notes": [
                "未配置 SMTP_HOST 时自动 dry-run，不连外网",
                "POST 接口需要登录；预览接口公开",
                "use_queue=true 时复用 Celery email 队列，Broker 挂了回退同步",
                "SendGrid / 阿里云邮件推送仍是可选，本模块只覆盖 SMTP",
            ],
        }
    )


@router.get(
    "/preview/{template_name}",
    summary="预览邮件模板",
)
async def preview_email_template(
    template_name: str,
    username: str = Query("alice", max_length=50),
    token: str = Query("demo-token", max_length=80),
    as_json: bool = Query(False, description="true 时返回 JSON（html + text）"),
):
    """
    浏览器直接打开就能看 HTML 长什么样。

    加 ?as_json=true 同时拿纯文本，方便写前端或对一下 fallback。
    """
    if template_name not in TEMPLATE_NAMES:
        raise BusinessException(
            ErrorCode.EMAIL_TEMPLATE_NOT_FOUND,
            message=f"未知模板: {template_name}",
        )

    context = default_template_context(
        template_name,  # type: ignore[arg-type]
        username=username,
        token=token,
    )
    rendered = render_template(template_name, context)

    if as_json:
        return success(
            data={
                "template": rendered.template,
                "subject": rendered.subject,
                "html": rendered.html,
                "text": rendered.text,
                "context": {
                    "username": context["username"],
                    "verify_url": context["verify_url"],
                    "reset_url": context["reset_url"],
                },
            }
        )
    return HTMLResponse(content=rendered.html)


# ============================================================
# 需登录：演示发送
# ============================================================

@router.post("/send", summary="发送自定义邮件")
async def send_custom_email(
    request: EmailSendRequest,
    current_user: User = Depends(get_current_user),
):
    """
    不走模板，直接发 text / html。

    适合：先确认 SMTP 通了，再接欢迎信 / 重置密码。
    """
    logger.info(
        "用户 %s 请求发送自定义邮件 to=%s queue=%s",
        current_user.id,
        request.to,
        request.use_queue,
    )
    data = await _maybe_queue(
        use_queue=request.use_queue,
        task_name="send_email",
        kwargs={
            "to": request.to,
            "subject": request.subject,
            "body": request.text or request.html or "",
            "html": request.html,
        },
        send=lambda: EmailService.send(
            to=request.to,
            subject=request.subject,
            text=request.text or "",
            html=request.html,
        ),
    )
    return success(data=data, message=data["message"])


@router.post("/welcome", summary="发送欢迎邮件（演示）")
async def send_welcome_demo(
    request: WelcomeEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """注册欢迎信。不会改用户表，只演示模板 + 发送路径。"""
    data = await _maybe_queue(
        use_queue=request.use_queue,
        task_name="send_welcome_email",
        kwargs={
            "user_id": current_user.id,
            "email": request.to,
            "username": request.username,
        },
        send=lambda: EmailService.send_template(
            "welcome",
            to=request.to,
            username=request.username,
        ),
    )
    return success(data=data, message=data["message"])


@router.post("/verify", summary="发送验证邮箱邮件（演示）")
async def send_verify_demo(
    request: VerifyEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """
    验证邮箱样式的演示。

    注意：这里不写库、不标记 email_verified。
    完整验证流（一次性 token、过期）仍是可选作业。
    """
    data = await _maybe_queue(
        use_queue=request.use_queue,
        task_name="send_templated_email",
        kwargs={
            "template": "verify",
            "to": request.to,
            "username": request.username,
            "token": request.verify_token,
        },
        send=lambda: EmailService.send_template(
            "verify",
            to=request.to,
            username=request.username,
            token=request.verify_token,
        ),
    )
    return success(data=data, message=data["message"])


@router.post("/password-reset", summary="发送密码重置邮件（演示）")
async def send_password_reset_demo(
    request: PasswordResetEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """
    密码重置样式的演示。

    注意：不会生成可用的重置会话，也不会改 hashed_password。
    """
    username = request.username or current_user.username
    data = await _maybe_queue(
        use_queue=request.use_queue,
        task_name="send_password_reset_email",
        kwargs={
            "email": request.to,
            "reset_token": request.reset_token or "demo-token",
            "username": username,
        },
        send=lambda: EmailService.send_template(
            "password_reset",
            to=request.to,
            username=username,
            token=request.reset_token,
        ),
    )
    return success(data=data, message=data["message"])


@router.post("/attachment", summary="发送带附件的演示邮件")
async def send_attachment_demo(
    request: AttachmentEmailRequest,
    current_user: User = Depends(get_current_user),
):
    """
    附件在内存里生成（txt 或最小 PDF），不写 data/uploads。
    """
    attachment = build_demo_attachment(request.kind)
    data = await _maybe_queue(
        use_queue=request.use_queue,
        task_name="send_templated_email",
        kwargs={
            "template": "welcome",
            "to": request.to,
            "username": current_user.username,
            "attach_kind": request.kind,
        },
        send=lambda: EmailService.send_template(
            "welcome",
            to=request.to,
            username=current_user.username,
            attachments=[attachment],
        ),
    )
    data["attachment"] = {
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "size": len(attachment.content),
    }
    return success(data=data, message=data["message"])
