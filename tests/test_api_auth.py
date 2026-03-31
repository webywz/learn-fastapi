from common.error_codes import ErrorCode


async def register_user(
    client,
    *,
    username: str = "alice",
    email: str = "alice@example.com",
    password: str = "123456",
):
    return await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )


async def login_user(client, *, username: str = "alice", password: str = "123456"):
    return await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


async def test_root_health_check_returns_running_status(client):
    response = await client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["message"] == "success"
    assert body["data"]["status"] == "running"


async def test_register_login_and_get_current_user(client):
    register_response = await register_user(client)

    assert register_response.status_code == 200
    register_body = register_response.json()
    assert register_body["code"] == 0
    assert register_body["data"]["username"] == "alice"
    assert "hashed_password" not in register_body["data"]

    login_response = await login_user(client)
    login_body = login_response.json()

    assert login_body["code"] == 0
    token = login_body["data"]["access_token"]
    assert token

    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    me_body = me_response.json()

    assert me_response.status_code == 200
    assert me_body["code"] == 0
    assert me_body["data"]["username"] == "alice"
    assert me_body["data"]["email"] == "alice@example.com"


async def test_register_rejects_duplicate_username(client):
    await register_user(client)

    duplicate_response = await register_user(
        client,
        email="another@example.com",
    )
    duplicate_body = duplicate_response.json()

    assert duplicate_response.status_code == 200
    assert duplicate_body["code"] == ErrorCode.USER_ALREADY_EXISTS.code
    assert duplicate_body["message"] == ErrorCode.USER_ALREADY_EXISTS.message


async def test_login_rejects_invalid_password(client):
    await register_user(client)

    response = await login_user(client, password="wrong-password")
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == ErrorCode.INVALID_USERNAME_OR_PASSWORD.code
    assert body["message"] == "用户名或密码错误"


async def test_update_current_user_changes_profile_and_password(client):
    await register_user(client)
    login_response = await login_user(client)
    token = login_response.json()["data"]["access_token"]

    update_response = await client.put(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "alice.updated@example.com",
            "password": "newpass123",
        },
    )
    update_body = update_response.json()

    assert update_response.status_code == 200
    assert update_body["code"] == 0
    assert update_body["data"]["email"] == "alice.updated@example.com"

    old_login_response = await login_user(client, password="123456")
    old_login_body = old_login_response.json()
    assert old_login_body["code"] == ErrorCode.INVALID_USERNAME_OR_PASSWORD.code

    new_login_response = await login_user(client, password="newpass123")
    new_login_body = new_login_response.json()
    assert new_login_body["code"] == 0


async def test_register_validates_payload(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "ab",
            "email": "not-an-email",
            "password": "123",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == ErrorCode.PARAMS_INVALID.code
    assert "errors" in body["data"]


async def test_file_upload_requires_authentication(client):
    response = await client.post(
        "/api/v1/files/upload",
        files={"file": ("hello.txt", b"hello", "text/plain")},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == ErrorCode.UNAUTHORIZED.code
