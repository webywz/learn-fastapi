from common.error_codes import ErrorCode
from tests.test_api_auth import login_user, register_user


async def _auth_headers(client, username="alice", email="alice@example.com"):
    await register_user(client, username=username, email=email)
    token = (await login_user(client, username=username)).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _upload_file(client, headers, name, content=b"hello"):
    response = await client.post(
        "/api/v1/files/upload",
        headers=headers,
        files={"file": (name, content, "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["code"] == 0
    return response.json()["data"]


async def test_list_files_keeps_legacy_shape_and_adds_pagination_fields(client):
    headers = await _auth_headers(client)
    uploaded = await _upload_file(client, headers, "legacy.txt")

    response = await client.get("/api/v1/files/list", headers=headers)
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 0
    data = body["data"]
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1
    assert data["files"][0]["saved_filename"] == uploaded["saved_filename"]
    assert data["has_next"] is False
    assert data["has_prev"] is False
    assert data["next_cursor"] is None
    assert data["mode"] == "offset"


async def test_list_files_empty_page_and_out_of_range(client):
    headers = await _auth_headers(client)

    empty_response = await client.get("/api/v1/files/list", headers=headers)
    empty = empty_response.json()["data"]
    assert empty["files"] == []
    assert empty["total"] == 0
    assert empty["total_pages"] == 0
    assert empty["has_next"] is False

    await _upload_file(client, headers, "only.txt")
    beyond = await client.get(
        "/api/v1/files/list",
        headers=headers,
        params={"page": 9, "page_size": 2},
    )
    beyond_data = beyond.json()["data"]
    assert beyond.status_code == 200
    assert beyond.json()["code"] == 0
    assert beyond_data["files"] == []
    assert beyond_data["total"] == 1
    assert beyond_data["has_next"] is False
    assert beyond_data["has_prev"] is True


async def test_list_files_rejects_page_below_one(client):
    headers = await _auth_headers(client)
    response = await client.get(
        "/api/v1/files/list",
        headers=headers,
        params={"page": 0},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == ErrorCode.PARAMS_INVALID.code


async def test_list_files_cursor_walks_pages(client):
    headers = await _auth_headers(client)
    names = []
    for index in range(5):
        record = await _upload_file(client, headers, f"page-{index}.txt", f"c{index}".encode())
        names.append(record["filename"])

    first = await client.get(
        "/api/v1/files/list",
        headers=headers,
        params={"page_size": 2},
    )
    first_data = first.json()["data"]
    assert first_data["mode"] == "offset"
    assert first_data["total"] == 5
    assert [item["filename"] for item in first_data["files"]] == ["page-4.txt", "page-3.txt"]
    assert first_data["has_next"] is True
    assert first_data["next_cursor"]

    second = await client.get(
        "/api/v1/files/list",
        headers=headers,
        params={"page_size": 2, "cursor": first_data["next_cursor"]},
    )
    second_data = second.json()["data"]
    assert second_data["mode"] == "cursor"
    assert second_data["total"] == 5
    assert [item["filename"] for item in second_data["files"]] == ["page-2.txt", "page-1.txt"]
    assert second_data["has_next"] is True
    assert second_data["has_prev"] is True

    third = await client.get(
        "/api/v1/files/list",
        headers=headers,
        params={"page_size": 2, "cursor": second_data["next_cursor"]},
    )
    third_data = third.json()["data"]
    assert [item["filename"] for item in third_data["files"]] == ["page-0.txt"]
    assert third_data["has_next"] is False
    assert third_data["next_cursor"] is None


async def test_list_files_rejects_invalid_cursor(client):
    headers = await _auth_headers(client)
    await _upload_file(client, headers, "cursor.txt")

    response = await client.get(
        "/api/v1/files/list",
        headers=headers,
        params={"cursor": "not-a-valid-cursor"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == ErrorCode.INVALID_CURSOR.code
    assert body["message"] == "分页游标无效"


async def test_list_users_requires_auth_and_paginates(client):
    anonymous = await client.get("/api/v1/users")
    assert anonymous.status_code == 200
    assert anonymous.json()["code"] == ErrorCode.UNAUTHORIZED.code

    await register_user(client, username="alice", email="alice@example.com")
    await register_user(client, username="bob", email="bob@example.com")
    await register_user(client, username="carol", email="carol@example.com")
    token = (await login_user(client, username="alice")).json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.get("/api/v1/users", headers=headers, params={"page_size": 2})
    first_body = first.json()
    assert first.status_code == 200
    assert first_body["code"] == 0
    data = first_body["data"]
    assert data["total"] == 3
    assert data["page_size"] == 2
    assert [item["username"] for item in data["items"]] == ["carol", "bob"]
    assert "hashed_password" not in data["items"][0]
    assert data["has_next"] is True
    assert data["mode"] == "offset"

    second = await client.get(
        "/api/v1/users",
        headers=headers,
        params={"page_size": 2, "cursor": data["next_cursor"]},
    )
    second_data = second.json()["data"]
    assert [item["username"] for item in second_data["items"]] == ["alice"]
    assert second_data["mode"] == "cursor"
    assert second_data["has_next"] is False


async def test_list_users_rejects_invalid_cursor(client):
    headers = await _auth_headers(client)
    response = await client.get(
        "/api/v1/users",
        headers=headers,
        params={"cursor": "%%%"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == ErrorCode.INVALID_CURSOR.code
