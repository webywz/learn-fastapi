import hashlib

from common.error_codes import ErrorCode
from core.config import settings
from tests.test_api_auth import login_user, register_user


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def _auth(client, username="alice", email="alice@example.com"):
    await register_user(client, username=username, email=email)
    token = (await login_user(client, username=username)).json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _put_part(client, headers, upload_id, part_number, data, checksum=None):
    files = {"chunk": (f"part{part_number}.bin", data, "application/octet-stream")}
    form = {}
    if checksum is not None:
        form["checksum"] = checksum
    return await client.put(
        f"/api/v1/files/chunked/{upload_id}/parts/{part_number}",
        headers=headers,
        files=files,
        data=form,
    )


async def test_chunked_overview_is_public(client):
    response = await client.get("/api/v1/files/chunked")
    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["module"] == "chunked-upload"
    assert body["data"]["checksum"] == "sha256"
    assert "init" in body["data"]["endpoints"]
    assert body["data"]["single_shot_max_bytes"] == 10 * 1024 * 1024


async def test_chunked_init_requires_auth(client):
    response = await client.post(
        "/api/v1/files/chunked/init",
        json={
            "filename": "hello.txt",
            "content_type": "text/plain",
            "total_size": 4,
            "chunk_size": 4,
        },
    )
    body = response.json()
    assert response.status_code == 200
    assert body["code"] == ErrorCode.UNAUTHORIZED.code


async def test_chunked_upload_happy_path_lists_and_downloads(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    headers = await _auth(client)
    payload = b"hello world!!"  # 13 bytes → 4 + 4 + 5
    checksum = _sha256(payload)

    init_response = await client.post(
        "/api/v1/files/chunked/init",
        headers=headers,
        json={
            "filename": "hello.txt",
            "content_type": "text/plain",
            "total_size": len(payload),
            "chunk_size": 4,
            "checksum": checksum,
        },
    )
    init_body = init_response.json()
    assert init_body["code"] == 0
    upload_id = init_body["data"]["upload_id"]
    assert init_body["data"]["total_chunks"] == 4
    assert init_body["data"]["missing_parts"] == [1, 2, 3, 4]

    parts = [payload[0:4], payload[4:8], payload[8:12], payload[12:13]]
    for index, part in enumerate(parts, start=1):
        part_response = await _put_part(
            client,
            headers,
            upload_id,
            index,
            part,
            checksum=_sha256(part),
        )
        assert part_response.json()["code"] == 0

    status_response = await client.get(
        f"/api/v1/files/chunked/{upload_id}",
        headers=headers,
    )
    status_body = status_response.json()
    assert status_body["code"] == 0
    assert status_body["data"]["missing_parts"] == []
    assert len(status_body["data"]["uploaded_parts"]) == 4

    complete_response = await client.post(
        f"/api/v1/files/chunked/{upload_id}/complete",
        headers=headers,
        json={"checksum": checksum},
    )
    complete_body = complete_response.json()
    assert complete_body["code"] == 0
    assert complete_body["data"]["filename"] == "hello.txt"
    assert complete_body["data"]["size"] == 13
    assert complete_body["data"]["storage"] == "local"
    saved_filename = complete_body["data"]["saved_filename"]

    list_response = await client.get("/api/v1/files/list", headers=headers)
    assert list_response.json()["data"]["total"] == 1
    assert list_response.json()["data"]["files"][0]["saved_filename"] == saved_filename

    download_response = await client.get(
        f"/api/v1/files/download/{saved_filename}",
        headers=headers,
    )
    assert download_response.status_code == 200
    assert download_response.content == payload

    again = await client.post(
        f"/api/v1/files/chunked/{upload_id}/complete",
        headers=headers,
        json={},
    )
    assert again.json()["code"] == 0
    assert again.json()["data"]["id"] == complete_body["data"]["id"]


async def test_chunked_part_idempotent_and_resume(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    headers = await _auth(client)
    payload = b"abcdef"

    init_body = (
        await client.post(
            "/api/v1/files/chunked/init",
            headers=headers,
            json={
                "filename": "resume.txt",
                "content_type": "text/plain",
                "total_size": 6,
                "chunk_size": 3,
            },
        )
    ).json()["data"]
    upload_id = init_body["upload_id"]

    first = await _put_part(client, headers, upload_id, 1, b"abc", checksum=_sha256(b"abc"))
    reused = await _put_part(client, headers, upload_id, 1, b"abc", checksum=_sha256(b"abc"))
    assert first.json()["data"]["reused"] is False
    assert reused.json()["data"]["reused"] is True

    status = await client.get(f"/api/v1/files/chunked/{upload_id}", headers=headers)
    assert status.json()["data"]["missing_parts"] == [2]

    await _put_part(client, headers, upload_id, 2, b"def")
    complete = await client.post(
        f"/api/v1/files/chunked/{upload_id}/complete",
        headers=headers,
        json={},
    )
    assert complete.json()["code"] == 0


async def test_chunked_rejects_wrong_part_checksum(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    headers = await _auth(client)
    init_body = (
        await client.post(
            "/api/v1/files/chunked/init",
            headers=headers,
            json={
                "filename": "bad.txt",
                "content_type": "text/plain",
                "total_size": 4,
                "chunk_size": 4,
            },
        )
    ).json()["data"]
    response = await _put_part(
        client,
        headers,
        init_body["upload_id"],
        1,
        b"abcd",
        checksum="0" * 64,
    )
    body = response.json()
    assert body["code"] == ErrorCode.CHUNK_CHECKSUM_MISMATCH.code


async def test_chunked_abort_then_complete_fails(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    headers = await _auth(client)
    init_body = (
        await client.post(
            "/api/v1/files/chunked/init",
            headers=headers,
            json={
                "filename": "abort.txt",
                "content_type": "text/plain",
                "total_size": 4,
                "chunk_size": 4,
            },
        )
    ).json()["data"]
    upload_id = init_body["upload_id"]
    await _put_part(client, headers, upload_id, 1, b"abcd")

    abort = await client.delete(f"/api/v1/files/chunked/{upload_id}", headers=headers)
    assert abort.json()["code"] == 0
    assert abort.json()["data"]["status"] == "aborted"

    complete = await client.post(
        f"/api/v1/files/chunked/{upload_id}/complete",
        headers=headers,
        json={},
    )
    assert complete.json()["code"] == ErrorCode.CHUNK_UPLOAD_ABORTED.code


async def test_chunked_session_is_scoped_to_owner(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    alice = await _auth(client, username="alice", email="alice@example.com")
    init_body = (
        await client.post(
            "/api/v1/files/chunked/init",
            headers=alice,
            json={
                "filename": "secret.txt",
                "content_type": "text/plain",
                "total_size": 4,
                "chunk_size": 4,
            },
        )
    ).json()["data"]

    bob = await _auth(client, username="bob", email="bob@example.com")
    status = await client.get(
        f"/api/v1/files/chunked/{init_body['upload_id']}",
        headers=bob,
    )
    assert status.json()["code"] == ErrorCode.CHUNK_UPLOAD_NOT_FOUND.code


async def test_chunked_init_rejects_disallowed_type(client):
    headers = await _auth(client)
    response = await client.post(
        "/api/v1/files/chunked/init",
        headers=headers,
        json={
            "filename": "x.exe",
            "content_type": "application/x-msdownload",
            "total_size": 4,
        },
    )
    assert response.json()["code"] == ErrorCode.CHUNK_UPLOAD_INVALID.code


async def test_single_shot_upload_still_works(client):
    headers = await _auth(client)
    response = await client.post(
        "/api/v1/files/upload",
        headers=headers,
        files={"file": ("hello.txt", b"hello world", "text/plain")},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["filename"] == "hello.txt"


async def test_chunked_cleanup_endpoint(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    headers = await _auth(client)
    response = await client.post("/api/v1/files/chunked/cleanup", headers=headers)
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["expired"] == 0
