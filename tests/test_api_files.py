from pathlib import Path


from common.error_codes import ErrorCode

from tests.test_api_auth import login_user, register_user


async def test_upload_file_persists_record_and_lists_for_current_user(client):
    await register_user(client)
    login_response = await login_user(client)
    token = login_response.json()["data"]["access_token"]

    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("hello.txt", b"hello world", "text/plain")},
    )
    upload_body = upload_response.json()

    assert upload_response.status_code == 200
    assert upload_body["code"] == 0
    assert upload_body["data"]["filename"] == "hello.txt"
    assert upload_body["data"]["owner_id"] > 0
    assert upload_body["data"]["storage"] == "local"

    saved_filename = upload_body["data"]["saved_filename"]
    saved_path = Path(upload_body["data"]["file_path"])
    assert saved_path.exists()

    list_response = await client.get(
        "/api/v1/files/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    list_body = list_response.json()

    assert list_response.status_code == 200
    assert list_body["code"] == 0
    assert list_body["data"]["total"] == 1
    listed_file = list_body["data"]["files"][0]
    assert listed_file["saved_filename"] == saved_filename

    detail_response = await client.get(
        f"/api/v1/files/detail/{listed_file['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    detail_body = detail_response.json()

    assert detail_response.status_code == 200
    assert detail_body["code"] == 0
    assert detail_body["data"]["saved_filename"] == saved_filename

    download_response = await client.get(
        f"/api/v1/files/download/{saved_filename}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert download_response.status_code == 200
    assert download_response.content == b"hello world"


async def test_list_files_is_scoped_to_current_user(client):
    await register_user(client, username="alice", email="alice@example.com")
    alice_token = (await login_user(client)).json()["data"]["access_token"]

    await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("alice.txt", b"alice", "text/plain")},
    )

    await register_user(client, username="bob", email="bob@example.com")
    bob_token = (await login_user(client, username="bob")).json()["data"]["access_token"]

    bob_list_response = await client.get(
        "/api/v1/files/list",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    bob_list_body = bob_list_response.json()

    assert bob_list_response.status_code == 200
    assert bob_list_body["code"] == 0
    assert bob_list_body["data"]["total"] == 0


async def test_delete_file_soft_deletes_record_and_writes_audit_log(client):
    await register_user(client)
    token = (await login_user(client)).json()["data"]["access_token"]

    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("cleanup.txt", b"cleanup", "text/plain")},
    )
    saved_filename = upload_response.json()["data"]["saved_filename"]
    saved_path = Path(upload_response.json()["data"]["file_path"])

    delete_response = await client.delete(
        f"/api/v1/files/delete/{saved_filename}",
        headers={"Authorization": f"Bearer {token}"},
    )
    delete_body = delete_response.json()

    assert delete_response.status_code == 200
    assert delete_body["code"] == 0
    assert not saved_path.exists()

    list_response = await client.get(
        "/api/v1/files/list",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.json()["data"]["total"] == 0

    detail_response = await client.get(
        f"/api/v1/files/detail/{upload_response.json()['data']['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    detail_body = detail_response.json()

    assert detail_response.status_code == 200
    assert detail_body["code"] == ErrorCode.RESOURCE_NOT_FOUND.code

    audit_response = await client.get(
        "/api/v1/files/audit",
        headers={"Authorization": f"Bearer {token}"},
    )
    audit_body = audit_response.json()

    assert audit_response.status_code == 200
    assert audit_body["code"] == 0
    assert audit_body["data"]["total"] == 2
    assert audit_body["data"]["logs"][0]["event_type"] == "deleted"
    assert audit_body["data"]["logs"][1]["event_type"] == "upload"


async def test_delete_file_rejects_other_users_file(client):
    await register_user(client, username="alice", email="alice@example.com")
    alice_token = (await login_user(client)).json()["data"]["access_token"]
    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("secret.txt", b"secret", "text/plain")},
    )
    saved_filename = upload_response.json()["data"]["saved_filename"]

    await register_user(client, username="bob", email="bob@example.com")
    bob_token = (await login_user(client, username="bob")).json()["data"]["access_token"]

    delete_response = await client.delete(
        f"/api/v1/files/delete/{saved_filename}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    delete_body = delete_response.json()

    assert delete_response.status_code == 200
    assert delete_body["code"] == ErrorCode.RESOURCE_NOT_FOUND.code


async def test_download_file_rejects_other_users_file(client):
    await register_user(client, username="alice", email="alice@example.com")
    alice_token = (await login_user(client)).json()["data"]["access_token"]
    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("private.txt", b"private", "text/plain")},
    )
    saved_filename = upload_response.json()["data"]["saved_filename"]

    await register_user(client, username="bob", email="bob@example.com")
    bob_token = (await login_user(client, username="bob")).json()["data"]["access_token"]

    download_response = await client.get(
        f"/api/v1/files/download/{saved_filename}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    download_body = download_response.json()

    assert download_response.status_code == 200
    assert download_body["code"] == ErrorCode.RESOURCE_NOT_FOUND.code


async def test_public_download_requires_visibility_change(client):
    await register_user(client)
    token = (await login_user(client)).json()["data"]["access_token"]
    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("public.txt", b"public-body", "text/plain")},
    )
    upload_body = upload_response.json()
    file_id = upload_body["data"]["id"]
    saved_filename = upload_body["data"]["saved_filename"]

    private_download_response = await client.get(f"/api/v1/files/public/download/{saved_filename}")
    private_download_body = private_download_response.json()

    assert private_download_response.status_code == 200
    assert private_download_body["code"] == ErrorCode.RESOURCE_NOT_FOUND.code

    visibility_response = await client.patch(
        f"/api/v1/files/visibility/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"visibility": "public"},
    )
    visibility_body = visibility_response.json()

    assert visibility_response.status_code == 200
    assert visibility_body["code"] == 0
    assert visibility_body["data"]["visibility"] == "public"

    public_download_response = await client.get(f"/api/v1/files/public/download/{saved_filename}")
    assert public_download_response.status_code == 200
    assert public_download_response.content == b"public-body"


async def test_signed_share_link_allows_anonymous_download(client):
    await register_user(client)
    token = (await login_user(client)).json()["data"]["access_token"]
    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("shared.txt", b"shared-body", "text/plain")},
    )
    upload_body = upload_response.json()
    file_id = upload_body["data"]["id"]

    share_response = await client.post(
        f"/api/v1/files/share/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"expires_minutes": 30},
    )
    share_body = share_response.json()

    assert share_response.status_code == 200
    assert share_body["code"] == 0
    assert "/api/v1/files/shared/" in share_body["data"]["share_url"]

    shared_download_response = await client.get(share_body["data"]["share_url"])
    assert shared_download_response.status_code == 200
    assert shared_download_response.content == b"shared-body"

    shares_response = await client.get(
        "/api/v1/files/shares",
        headers={"Authorization": f"Bearer {token}"},
    )
    shares_body = shares_response.json()

    assert shares_response.status_code == 200
    assert shares_body["code"] == 0
    assert shares_body["data"]["total"] == 1
    assert shares_body["data"]["shares"][0]["access_count"] == 1
    assert shares_body["data"]["shares"][0]["status"] == "active"
    assert shares_body["data"]["shares"][0]["share_url"]


async def test_signed_share_link_rejects_tampered_token(client):
    await register_user(client)
    token = (await login_user(client)).json()["data"]["access_token"]
    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("tamper.txt", b"tamper-body", "text/plain")},
    )
    file_id = upload_response.json()["data"]["id"]

    share_response = await client.post(
        f"/api/v1/files/share/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"expires_minutes": 30},
    )
    share_url = share_response.json()["data"]["share_url"]
    tampered_url = f"{share_url}tampered"

    tampered_response = await client.get(tampered_url)
    tampered_body = tampered_response.json()

    assert tampered_response.status_code == 200
    assert tampered_body["code"] == ErrorCode.RESOURCE_NOT_FOUND.code


async def test_revoked_share_link_cannot_be_downloaded(client):
    await register_user(client)
    token = (await login_user(client)).json()["data"]["access_token"]
    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("revoke.txt", b"revoke-body", "text/plain")},
    )
    file_id = upload_response.json()["data"]["id"]

    share_response = await client.post(
        f"/api/v1/files/share/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"expires_minutes": 30},
    )
    share_body = share_response.json()["data"]

    revoke_response = await client.delete(
        f"/api/v1/files/share/{share_body['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    revoke_body = revoke_response.json()

    assert revoke_response.status_code == 200
    assert revoke_body["code"] == 0
    assert revoke_body["data"]["status"] == "revoked"
    assert revoke_body["data"]["share_url"] is None

    list_response = await client.get(
        "/api/v1/files/shares",
        headers={"Authorization": f"Bearer {token}"},
    )
    list_body = list_response.json()

    assert list_response.status_code == 200
    assert list_body["code"] == 0
    assert list_body["data"]["total"] == 1
    assert list_body["data"]["shares"][0]["status"] == "revoked"

    revoked_download_response = await client.get(share_body["share_url"])
    revoked_download_body = revoked_download_response.json()

    assert revoked_download_response.status_code == 200
    assert revoked_download_body["code"] == ErrorCode.RESOURCE_NOT_FOUND.code


async def test_delete_file_revokes_existing_share_and_records_audit(client):
    await register_user(client)
    token = (await login_user(client)).json()["data"]["access_token"]
    upload_response = await client.post(
        "/api/v1/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("gone.txt", b"gone-body", "text/plain")},
    )
    upload_body = upload_response.json()["data"]

    share_response = await client.post(
        f"/api/v1/files/share/{upload_body['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"expires_minutes": 30},
    )
    share_body = share_response.json()["data"]

    delete_response = await client.delete(
        f"/api/v1/files/delete/{upload_body['saved_filename']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    delete_body = delete_response.json()

    assert delete_response.status_code == 200
    assert delete_body["code"] == 0

    shared_download_response = await client.get(share_body["share_url"])
    shared_download_body = shared_download_response.json()

    assert shared_download_response.status_code == 200
    assert shared_download_body["code"] == ErrorCode.RESOURCE_NOT_FOUND.code

    shares_response = await client.get(
        "/api/v1/files/shares",
        headers={"Authorization": f"Bearer {token}"},
    )
    shares_body = shares_response.json()

    assert shares_response.status_code == 200
    assert shares_body["code"] == 0
    assert shares_body["data"]["total"] == 1
    assert shares_body["data"]["shares"][0]["status"] == "revoked"

    audit_response = await client.get(
        f"/api/v1/files/audit?file_id={upload_body['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    audit_body = audit_response.json()

    assert audit_response.status_code == 200
    assert audit_body["code"] == 0
    event_types = [log["event_type"] for log in audit_body["data"]["logs"]]
    assert "upload" in event_types
    assert "share_created" in event_types
    assert "deleted" in event_types
