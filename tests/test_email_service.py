import asyncio

import aiosmtplib
import pytest

from common.error_codes import ErrorCode
from common.exceptions import BusinessException, ValidationException
from core.config import settings
from services.email_service import (
    DEMO_PDF_FILENAME,
    DEMO_TEXT_FILENAME,
    EmailService,
    MINIMAL_PDF_BYTES,
    build_demo_attachment,
    build_message,
    render_template,
    smtp_send,
)
from tasks.email_tasks import send_email, send_templated_email, send_welcome_email


def test_render_welcome_and_password_reset_have_html_and_text():
    welcome = render_template(
        "welcome",
        {
            "app_name": "Demo App",
            "username": "alice",
            "token": "tok-1",
            "verify_url": "https://example.com/verify-email?token=tok-1",
            "reset_url": "https://example.com/reset-password?token=tok-1",
            "support_email": "support@example.com",
        },
    )
    assert "alice" in welcome.html
    assert "alice" in welcome.text
    assert "verify-email" in welcome.html
    assert welcome.subject.startswith("欢迎加入")

    reset = render_template(
        "password_reset",
        {
            "app_name": "Demo App",
            "username": "alice",
            "token": "tok-2",
            "verify_url": "https://example.com/verify-email?token=tok-2",
            "reset_url": "https://example.com/reset-password?token=tok-2",
            "support_email": "support@example.com",
        },
    )
    assert "reset-password" in reset.html
    assert "tok-2" in reset.text
    assert "重置" in reset.subject


def test_unknown_template_raises_business_error():
    with pytest.raises(BusinessException) as exc_info:
        render_template("not-a-template", {})

    assert exc_info.value.code == ErrorCode.EMAIL_TEMPLATE_NOT_FOUND.code


def test_build_message_is_multipart_with_attachment():
    attachment = build_demo_attachment("text")
    message = build_message(
        to="alice@example.com",
        subject="带附件",
        text="纯文本正文",
        html="<p>HTML 正文</p>",
        attachments=[attachment],
    )

    assert message["To"] == "alice@example.com"
    assert message["Subject"] == "带附件"
    assert message.get_content_maintype() == "multipart"

    bodies = []
    filenames = []
    for part in message.walk():
        if part.get_content_maintype() == "multipart":
            continue
        if part.get_filename():
            filenames.append(part.get_filename())
        else:
            bodies.append(part.get_content())

    assert any("纯文本正文" in str(item) for item in bodies)
    assert any("HTML 正文" in str(item) for item in bodies)
    assert DEMO_TEXT_FILENAME in filenames


def test_demo_pdf_attachment_is_tiny_and_has_header():
    attachment = build_demo_attachment("pdf")
    assert attachment.filename == DEMO_PDF_FILENAME
    assert attachment.content.startswith(b"%PDF-")
    assert attachment.content == MINIMAL_PDF_BYTES
    assert len(attachment.content) < 2048


def test_empty_payload_is_rejected():
    with pytest.raises(ValidationException) as exc_info:
        build_message(to="alice@example.com", subject="空", text="", html="")

    assert exc_info.value.code == ErrorCode.EMAIL_PAYLOAD_INVALID.code


async def test_dry_run_does_not_call_smtp(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_DRY_RUN", False)

    called = {"n": 0}

    async def forbidden(_message):
        called["n"] += 1
        raise AssertionError("dry-run 不该连 SMTP")

    result = await EmailService.send(
        to="alice@example.com",
        subject="dry-run",
        text="hello",
        smtp_send_fn=forbidden,
    )

    assert result.mode == "dry_run"
    assert called["n"] == 0
    assert result.to == ["alice@example.com"]


async def test_smtp_path_uses_injected_sender(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(settings, "SMTP_DRY_RUN", False)

    captured = {}

    async def fake_send(message):
        captured["subject"] = message["Subject"]
        captured["to"] = message["To"]

    result = await EmailService.send(
        to="bob@example.com",
        subject="真实路径",
        text="正文",
        html="<p>正文</p>",
        smtp_send_fn=fake_send,
    )

    assert result.mode == "smtp"
    assert result.attempts == 1
    assert captured["subject"] == "真实路径"
    assert captured["to"] == "bob@example.com"


async def test_retries_transient_smtp_timeout(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(settings, "SMTP_DRY_RUN", False)
    monkeypatch.setattr(settings, "SMTP_MAX_RETRIES", 2)
    monkeypatch.setattr(settings, "SMTP_RETRY_BACKOFF", 0)

    calls = {"n": 0}

    async def flaky(_message):
        calls["n"] += 1
        if calls["n"] < 3:
            raise aiosmtplib.SMTPTimeoutError("temporary")

    result = await EmailService.send(
        to="alice@example.com",
        subject="retry",
        text="hello",
        smtp_send_fn=flaky,
    )

    assert calls["n"] == 3
    assert result.attempts == 3
    assert result.mode == "smtp"


async def test_auth_failure_is_not_retried(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(settings, "SMTP_DRY_RUN", False)
    monkeypatch.setattr(settings, "SMTP_MAX_RETRIES", 3)
    monkeypatch.setattr(settings, "SMTP_RETRY_BACKOFF", 0)

    calls = {"n": 0}

    async def unauthorized(_message):
        calls["n"] += 1
        raise aiosmtplib.SMTPAuthenticationError(535, "invalid credentials")

    with pytest.raises(BusinessException) as exc_info:
        await EmailService.send(
            to="alice@example.com",
            subject="auth",
            text="hello",
            smtp_send_fn=unauthorized,
        )

    assert calls["n"] == 1
    assert exc_info.value.code == ErrorCode.EMAIL_SEND_FAILED.code


async def test_send_template_welcome_dry_run():
    result = await EmailService.send_template(
        "welcome",
        to="alice@example.com",
        username="alice",
    )
    assert result.mode == "dry_run"
    assert result.template == "welcome"


def test_celery_wrapper_uses_same_service():
    payload = send_email.run(
        to="alice@example.com",
        subject="来自任务",
        body="同步调用任务，不需要 Redis",
    )
    assert payload["status"] == "sent"
    assert payload["mode"] == "dry_run"
    assert payload["to"] == ["alice@example.com"]

    welcome = send_welcome_email.run(1, "alice@example.com", "alice")
    assert welcome["template"] == "welcome"
    assert welcome["user_id"] == 1

    templated = send_templated_email.run(
        "verify",
        "alice@example.com",
        username="alice",
        token="abc",
    )
    assert templated["template"] == "verify"


async def test_default_smtp_send_forwards_config(monkeypatch):
    """默认 smtp_send 会把配置传给 aiosmtplib；测试只 mock 库函数。"""
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USER", "user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(settings, "SMTP_STARTTLS", True)
    monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT", 9)

    captured = {}

    async def fake_aiosmtp_send(message, **kwargs):
        captured.update(kwargs)
        captured["message"] = message

    monkeypatch.setattr("services.email_service.aiosmtplib.send", fake_aiosmtp_send)

    message = build_message(to="a@b.com", subject="cfg", text="hi")
    await smtp_send(message)

    assert captured["hostname"] == "smtp.example.com"
    assert captured["port"] == 587
    assert captured["username"] == "user"
    assert captured["start_tls"] is True
    assert captured["use_tls"] is False


def test_run_async_from_running_loop():
    """Celery 桥接在已有事件循环里也不能炸。"""
    from tasks.email_tasks import run_async

    async def inner():
        return await asyncio.sleep(0, result=42)

    async def outer():
        return run_async(inner)

    result = asyncio.run(outer())
    assert result == 42
