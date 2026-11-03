"""
===========================================
邮件任务 (Email Tasks)
===========================================

作用：
  Celery 包装层。真正的 SMTP / 模板 / 附件都在
  services/email_service.py，这里只负责：
    1. 把异步发送桥到同步 Worker
    2. 失败后按 Celery 策略重新入队

为什么发邮件还要再包一层任务？
  - SMTP 往返 1-3 秒，API 里硬等用户会觉得卡
  - Worker 挂了可以靠 Broker 重试（分钟级）
  - 和「同一次请求内的秒级重试」是两层，见 EmailService 注释

什么时候不要走这里？
  - CI、没 Redis、只想看模板：用 /api/v1/email/* 同步路径
  - 那个接口 use_queue=true 时会调用本文件；Broker 挂了会回退同步

类比前端：
  - delay() ≈ 把任务丢进 Web Worker
  - self.retry() ≈ 失败后 setTimeout 再试
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Awaitable, Callable, List, Optional, TypeVar

from celery import shared_task

from services.email_service import EmailService, build_demo_attachment
from utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def run_async(factory: Callable[[], Awaitable[T]]) -> T:
    """
    在同步 Celery Worker 里跑一段 async。

    注意：协程必须在 factory() 里创建。
    不能先在外面 `coro = EmailService.send(...)` 再丢进另一个 loop，
    否则会报 "bound to a different event loop"。
    """

    def _call() -> T:
        return asyncio.run(factory())

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _call()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_call).result()


def _result_payload(result, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    payload = EmailService.result_to_dict(result)
    payload["status"] = "sent"
    if extra:
        payload.update(extra)
    return payload


# ============================================================
# 基础邮件任务
# ============================================================

@shared_task(
    bind=True,
    name="tasks.email_tasks.send_email",
    max_retries=3,
    default_retry_delay=60,
)
def send_email(
    self,
    to: str,
    subject: str,
    body: str,
    html: Optional[str] = None,
):
    """
    发送单封自定义邮件。

    装饰器:
        bind=True           才能 self.retry
        max_retries=3       Celery 层最多再入队 3 次
        default_retry_delay 每次隔 60 秒（和 EmailService 的 0.4s 不是同一层）

    调用:
        send_email.delay("user@example.com", "Welcome", "Hello!")
    """
    try:
        logger.info("Celery 发送邮件 to=%s subject=%s", to, subject)
        result = run_async(
            lambda: EmailService.send(
                to=to,
                subject=subject,
                text=body,
                html=html,
            )
        )
        return _result_payload(result)
    except Exception as exc:
        logger.exception("Celery 发送邮件失败 to=%s", to)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="tasks.email_tasks.send_welcome_email",
    max_retries=3,
    default_retry_delay=60,
)
def send_welcome_email(self, user_id: int, email: str, username: str):
    """用户注册后的欢迎信。模板：templates/email/welcome.*"""
    try:
        logger.info("Celery 欢迎邮件 user_id=%s to=%s", user_id, email)
        result = run_async(
            lambda: EmailService.send_template(
                "welcome",
                to=email,
                username=username,
            )
        )
        return _result_payload(result, extra={"user_id": user_id})
    except Exception as exc:
        logger.exception("Celery 欢迎邮件失败 user_id=%s", user_id)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="tasks.email_tasks.send_password_reset_email",
    max_retries=3,
    default_retry_delay=60,
)
def send_password_reset_email(
    self,
    email: str,
    reset_token: str,
    username: Optional[str] = None,
):
    """密码重置邮件。只发信，不改数据库密码。"""
    try:
        logger.info("Celery 密码重置邮件 to=%s", email)
        result = run_async(
            lambda: EmailService.send_template(
                "password_reset",
                to=email,
                username=username or "同学",
                token=reset_token,
            )
        )
        return _result_payload(result, extra={"email": email})
    except Exception as exc:
        logger.exception("Celery 密码重置邮件失败 to=%s", email)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="tasks.email_tasks.send_templated_email",
    max_retries=3,
    default_retry_delay=60,
)
def send_templated_email(
    self,
    template: str,
    to: str,
    username: str = "同学",
    token: Optional[str] = None,
    attach_kind: Optional[str] = None,
):
    """通用模板任务（验证信、带附件的欢迎信都走这里）。"""
    try:
        attachments = None
        if attach_kind in {"text", "pdf"}:
            attachments = [build_demo_attachment(attach_kind)]  # type: ignore[arg-type]
        result = run_async(
            lambda: EmailService.send_template(
                template,  # type: ignore[arg-type]
                to=to,
                username=username,
                token=token,
                attachments=attachments,
            )
        )
        return _result_payload(result)
    except Exception as exc:
        logger.exception("Celery 模板邮件失败 template=%s to=%s", template, to)
        raise self.retry(exc=exc)


# ============================================================
# 批量邮件任务
# ============================================================

@shared_task(name="tasks.email_tasks.send_bulk_emails")
def send_bulk_emails(emails: List[dict]):
    """
    批量发送。教学实现：一封一封走 EmailService。

    生产环境更常见的是交给 SendGrid / 阿里云批量接口，
    而不是自己在 Worker 里连 SMTP 循环一千次。
    """
    logger.info("Celery 批量发送 %s 封邮件", len(emails))
    success_count = 0
    failed_count = 0

    for email_data in emails:
        to = email_data.get("to", "")
        try:
            run_async(
                lambda data=email_data: EmailService.send(
                    to=data["to"],
                    subject=data["subject"],
                    text=data.get("body") or data.get("text") or "",
                    html=data.get("html"),
                )
            )
            success_count += 1
        except Exception as exc:
            logger.warning("批量发送失败 to=%s error=%s", to, exc)
            failed_count += 1

    return {
        "total": len(emails),
        "success": success_count,
        "failed": failed_count,
        "status": "sent",
    }


@shared_task(name="tasks.email_tasks.send_newsletter")
def send_newsletter(subject: str, content: str, user_ids: List[int]):
    """
    新闻通讯占位。

    真实项目会：查库拿邮箱 → 模板渲染 → 专业邮件服务批量 API。
    这里不连数据库，只记录要发给多少人，避免教学任务误发。
    """
    logger.info("新闻通讯占位 subject=%s users=%s（未实际群发）", subject, len(user_ids))
    return {"user_count": len(user_ids), "status": "skipped", "reason": "demo_placeholder"}


# ============================================================
# 学习笔记
# ============================================================
"""
1. 【任务调用】
   send_email.delay(to, subject, body)          # 异步
   send_email.apply_async(kwargs=..., countdown=60)
   send_email.run(...)                          # 测试里同步跑

2. 【两层重试】
   EmailService: 同一次调用内 0.4s、0.8s 再试（SMTP 抖动）
   Celery:       60s 后重新入队（Worker / 对端持续失败）
   认证失败、5xx 永久错不要在服务层重试。

3. 【Broker 挂了怎么办】
   /api/v1/email/* 默认同步发送。
   use_queue=true 时 apply_async 失败会回退同步。
   旧的 /api/v1/tasks/email/* 仍然只走队列，用来对比。

4. 【不要在任务里 time.sleep 假装发信】
   以前的 stub 已经换成 EmailService。没配 SMTP 就是 dry-run。
"""
