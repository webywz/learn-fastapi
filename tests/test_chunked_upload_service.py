import hashlib
from datetime import timedelta
import pytest

from common.error_codes import ErrorCode
from common.exceptions import BusinessException
from core.config import settings
from models.file import FileUploadSession
from models.user import User
from schemas.user import UserCreate
from services.chunked_upload_service import (
    STATUS_EXPIRED,
    STATUS_PENDING,
    ChunkedUploadService,
    expected_part_size,
    normalize_checksum,
    now_utc,
    resolve_chunk_plan,
    sha256_bytes,
    sha256_file,
)
from services.user_service import UserService


class FakeUpload:
    def __init__(self, data: bytes):
        self._data = data
        self._closed = False

    async def read(self, size: int = -1) -> bytes:
        if not self._data:
            return b""
        if size < 0:
            chunk, self._data = self._data, b""
            return chunk
        chunk, self._data = self._data[:size], self._data[size:]
        return chunk

    async def close(self) -> None:
        self._closed = True


@pytest.fixture(autouse=True)
def isolate_upload_dir(tmp_path, monkeypatch):
    target = tmp_path / "uploads"
    target.mkdir()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(target))
    return target


async def _user(db_session) -> User:
    return await UserService.create_user(
        db_session,
        UserCreate(
            username="alice",
            email="alice@example.com",
            password="123456",
        ),
    )


def test_normalize_checksum_accepts_prefix_and_upper():
    raw = "A" * 64
    assert normalize_checksum(f"SHA256:{raw}") == ("a" * 64)
    assert normalize_checksum(None) is None
    assert normalize_checksum("  ") is None


def test_normalize_checksum_rejects_garbage():
    with pytest.raises(BusinessException) as exc_info:
        normalize_checksum("not-a-hash")
    assert exc_info.value.code == ErrorCode.CHUNK_UPLOAD_INVALID.code


def test_resolve_chunk_plan_clamps_small_files():
    chunk_size, total_chunks = resolve_chunk_plan(12, None)
    assert total_chunks >= 1
    assert chunk_size == 12 or chunk_size == settings.CHUNKED_DEFAULT_CHUNK_SIZE


def test_expected_part_size_last_chunk_eats_remainder():
    assert expected_part_size(12, 5, 3, 1) == 5
    assert expected_part_size(12, 5, 3, 2) == 5
    assert expected_part_size(12, 5, 3, 3) == 2


def test_sha256_file_matches_bytes(tmp_path):
    payload = b"hello-chunk"
    path = tmp_path / "one.bin"
    path.write_bytes(payload)
    assert sha256_file(path) == sha256_bytes(payload)
    assert sha256_file(path) == hashlib.sha256(payload).hexdigest()


async def test_init_rejects_bad_mime(db_session):
    user = await _user(db_session)
    with pytest.raises(BusinessException) as exc_info:
        await ChunkedUploadService.init_session(
            db_session,
            owner_id=user.id,
            filename="malware.exe",
            content_type="application/octet-stream",
            total_size=12,
            chunk_size=4,
        )
    assert exc_info.value.code == ErrorCode.CHUNK_UPLOAD_INVALID.code


async def test_complete_assembles_tiny_chunks(db_session, isolate_upload_dir):
    user = await _user(db_session)
    payload = b"abcdefghijkl"
    checksum = sha256_bytes(payload)
    session = await ChunkedUploadService.init_session(
        db_session,
        owner_id=user.id,
        filename="lecture.txt",
        content_type="text/plain",
        total_size=len(payload),
        chunk_size=4,
        checksum=checksum,
    )
    assert session.total_chunks == 3

    for index, start in enumerate((0, 4, 8), start=1):
        await ChunkedUploadService.save_part(
            db_session,
            owner_id=user.id,
            upload_id=session.upload_id,
            part_number=index,
            chunk=FakeUpload(payload[start : start + 4]),
            checksum=sha256_bytes(payload[start : start + 4]),
        )

    file_record = await ChunkedUploadService.complete(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
    )
    saved = isolate_upload_dir / file_record.saved_filename
    assert saved.read_bytes() == payload
    assert file_record.size == 12
    assert not (isolate_upload_dir / ".chunks" / session.upload_id).exists()

    again = await ChunkedUploadService.complete(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
    )
    assert again.id == file_record.id


async def test_save_part_is_idempotent_when_checksum_matches(db_session):
    user = await _user(db_session)
    payload = b"abcd"
    session = await ChunkedUploadService.init_session(
        db_session,
        owner_id=user.id,
        filename="one.txt",
        content_type="text/plain",
        total_size=4,
        chunk_size=4,
    )
    first = await ChunkedUploadService.save_part(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
        part_number=1,
        chunk=FakeUpload(payload),
        checksum=sha256_bytes(payload),
    )
    second = await ChunkedUploadService.save_part(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
        part_number=1,
        chunk=FakeUpload(payload),
        checksum=sha256_bytes(payload),
    )
    assert first["reused"] is False
    assert second["reused"] is True
    assert second["checksum"] == first["checksum"]


async def test_save_part_rejects_checksum_mismatch(db_session):
    user = await _user(db_session)
    session = await ChunkedUploadService.init_session(
        db_session,
        owner_id=user.id,
        filename="bad.txt",
        content_type="text/plain",
        total_size=4,
        chunk_size=4,
    )
    with pytest.raises(BusinessException) as exc_info:
        await ChunkedUploadService.save_part(
            db_session,
            owner_id=user.id,
            upload_id=session.upload_id,
            part_number=1,
            chunk=FakeUpload(b"abcd"),
            checksum="0" * 64,
        )
    assert exc_info.value.code == ErrorCode.CHUNK_CHECKSUM_MISMATCH.code


async def test_complete_rejects_missing_parts(db_session):
    user = await _user(db_session)
    session = await ChunkedUploadService.init_session(
        db_session,
        owner_id=user.id,
        filename="gap.txt",
        content_type="text/plain",
        total_size=8,
        chunk_size=4,
    )
    await ChunkedUploadService.save_part(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
        part_number=1,
        chunk=FakeUpload(b"abcd"),
    )
    with pytest.raises(BusinessException) as exc_info:
        await ChunkedUploadService.complete(
            db_session,
            owner_id=user.id,
            upload_id=session.upload_id,
        )
    assert exc_info.value.code == ErrorCode.CHUNK_UPLOAD_INCOMPLETE.code
    assert exc_info.value.data["missing_parts"] == [2]


async def test_expired_pending_session_is_cleaned(db_session, isolate_upload_dir):
    user = await _user(db_session)
    session = await ChunkedUploadService.init_session(
        db_session,
        owner_id=user.id,
        filename="old.txt",
        content_type="text/plain",
        total_size=4,
        chunk_size=4,
    )
    await ChunkedUploadService.save_part(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
        part_number=1,
        chunk=FakeUpload(b"abcd"),
    )
    session.expires_at = now_utc() - timedelta(seconds=1)
    await db_session.commit()

    with pytest.raises(BusinessException) as exc_info:
        await ChunkedUploadService.get_owned_session(
            db_session,
            owner_id=user.id,
            upload_id=session.upload_id,
            allow_statuses={STATUS_PENDING},
        )
    assert exc_info.value.code == ErrorCode.CHUNK_UPLOAD_EXPIRED.code
    assert not (isolate_upload_dir / ".chunks" / session.upload_id).exists()

    reloaded = await db_session.get(FileUploadSession, session.id)
    assert reloaded.status == STATUS_EXPIRED


async def test_abort_removes_temp_dir(db_session, isolate_upload_dir):
    user = await _user(db_session)
    session = await ChunkedUploadService.init_session(
        db_session,
        owner_id=user.id,
        filename="drop.txt",
        content_type="text/plain",
        total_size=4,
        chunk_size=4,
    )
    await ChunkedUploadService.save_part(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
        part_number=1,
        chunk=FakeUpload(b"abcd"),
    )
    aborted = await ChunkedUploadService.abort(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
    )
    assert aborted.status == "aborted"
    assert not (isolate_upload_dir / ".chunks" / session.upload_id).exists()

    again = await ChunkedUploadService.abort(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
    )
    assert again.status == "aborted"


async def test_complete_file_checksum_mismatch(db_session):
    user = await _user(db_session)
    payload = b"abcd"
    session = await ChunkedUploadService.init_session(
        db_session,
        owner_id=user.id,
        filename="sum.txt",
        content_type="text/plain",
        total_size=4,
        chunk_size=4,
        checksum="1" * 64,
    )
    await ChunkedUploadService.save_part(
        db_session,
        owner_id=user.id,
        upload_id=session.upload_id,
        part_number=1,
        chunk=FakeUpload(payload),
    )
    with pytest.raises(BusinessException) as exc_info:
        await ChunkedUploadService.complete(
            db_session,
            owner_id=user.id,
            upload_id=session.upload_id,
        )
    assert exc_info.value.code == ErrorCode.CHUNK_CHECKSUM_MISMATCH.code
