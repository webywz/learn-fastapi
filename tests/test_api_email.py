from common.error_codes import ErrorCode
from core.config import settings
from tasks.email_tasks import send_welcome_email


async def _login(client, *, username="alice", email="alice@example.com"):
    await client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "123456"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "123456"},
    )
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_email_overview_reports_dry_run(client):
    response = await client.get("/api/v1/email/")
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["transport"] == "aiosmtplib"
    assert "welcome" in body["data"]["templates"]
    assert "password_reset" in body["data"]["templates"]
    assert body["data"]["smtp"]["dry_run"] is True
    assert "welcome" in body["data"]["endpoints"]


async def test_preview_welcome_html_and_json(client):
    html_response = await client.get("/api/v1/email/preview/welcome")
    assert html_response.status_code == 200
    assert "text/html" in html_response.headers["content-type"]
    assert "alice" in html_response.text
    assert "欢迎加入" in html_response.text

    json_response = await client.get(
        "/api/v1/email/preview/password_reset",
        params={"as_json": True, "username": "bob", "token": "reset-1"},
    )
    payload = json_response.json()
    assert payload["code"] == 0
    assert payload["data"]["template"] == "password_reset"
    assert "bob" in payload["data"]["html"]
    assert "reset-1" in payload["data"]["text"]
    assert "reset-password" in payload["data"]["context"]["reset_url"]


async def test_preview_unknown_template(client):
    response = await client.get("/api/v1/email/preview/nope")
    body = response.json()
    assert body["code"] == ErrorCode.EMAIL_TEMPLATE_NOT_FOUND.code


async def test_send_requires_authentication(client):
    response = await client.post(
        "/api/v1/email/welcome",
        json={"to": "alice@example.com", "username": "alice"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["code"] == ErrorCode.UNAUTHORIZED.code


async def test_demo_endpoints_work_offline_without_broker(client):
    headers = await _login(client)

    welcome = await client.post(
        "/api/v1/email/welcome",
        headers=headers,
        json={"to": "alice@example.com", "username": "alice"},
    )
    welcome_body = welcome.json()
    assert welcome_body["code"] == 0
    assert welcome_body["data"]["queued"] is False
    assert welcome_body["data"]["mode"] == "dry_run"
    assert welcome_body["data"]["template"] == "welcome"

    verify = await client.post(
        "/api/v1/email/verify",
        headers=headers,
        json={"to": "alice@example.com", "username": "alice", "verify_token": "v1"},
    )
    assert verify.json()["data"]["template"] == "verify"

    reset = await client.post(
        "/api/v1/email/password-reset",
        headers=headers,
        json={"to": "alice@example.com", "reset_token": "r1"},
    )
    assert reset.json()["data"]["template"] == "password_reset"

    attachment = await client.post(
        "/api/v1/email/attachment",
        headers=headers,
        json={"to": "alice@example.com", "kind": "pdf"},
    )
    attachment_body = attachment.json()
    assert attachment_body["code"] == 0
    assert attachment_body["data"]["attachment"]["filename"].endswith(".pdf")
    assert attachment_body["data"]["attachments"]


async def test_custom_send_and_queue_fallback(client, monkeypatch):
    headers = await _login(client, username="bob", email="bob@example.com")

    custom = await client.post(
        "/api/v1/email/send",
        headers=headers,
        json={
            "to": "bob@example.com",
            "subject": "hello",
            "text": "plain",
            "html": "<p>plain</p>",
        },
    )
    assert custom.json()["data"]["mode"] == "dry_run"
    assert custom.json()["data"]["queued"] is False

    def boom(*_args, **_kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(send_welcome_email, "apply_async", boom)

    fallback = await client.post(
        "/api/v1/email/welcome",
        headers=headers,
        json={
            "to": "bob@example.com",
            "username": "bob",
            "use_queue": True,
        },
    )
    fallback_body = fallback.json()
    assert fallback_body["code"] == 0
    assert fallback_body["data"]["queued"] is False
    assert fallback_body["data"]["fallback"] == "sync"
    assert fallback_body["data"]["mode"] == "dry_run"


async def test_queue_success_does_not_send_inline(client, monkeypatch):
    headers = await _login(client, username="cara", email="cara@example.com")

    class FakeResult:
        id = "task-email-1"

    monkeypatch.setattr(
        send_welcome_email,
        "apply_async",
        lambda *args, **kwargs: FakeResult(),
    )

    response = await client.post(
        "/api/v1/email/welcome",
        headers=headers,
        json={
            "to": "cara@example.com",
            "username": "cara",
            "use_queue": True,
        },
    )
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["queued"] is True
    assert body["data"]["task_id"] == "task-email-1"
    assert body["data"]["queue"] == "email"


async def test_smtp_mode_via_api_uses_mock(client, monkeypatch):
    headers = await _login(client, username="dave", email="dave@example.com")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(settings, "SMTP_DRY_RUN", False)

    captured = {"n": 0}

    async def fake_send(_message):
        captured["n"] += 1

    monkeypatch.setattr("services.email_service.smtp_send", fake_send)

    response = await client.post(
        "/api/v1/email/send",
        headers=headers,
        json={"to": "dave@example.com", "subject": "mocked", "text": "hi"},
    )
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["mode"] == "smtp"
    assert captured["n"] == 1
