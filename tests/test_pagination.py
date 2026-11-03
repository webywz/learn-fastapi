from datetime import datetime, timezone

import pytest

from common.error_codes import ErrorCode
from common.exceptions import ValidationException
from core.pagination import (
    ListParams,
    compute_has_next_offset,
    compute_offset,
    compute_total_pages,
    cursor_from_item,
    decode_cursor,
    encode_cursor,
)
from schemas.user import UserCreate
from services.user_service import UserService


def test_compute_offset_and_total_pages():
    assert compute_offset(1, 10) == 0
    assert compute_offset(3, 10) == 20
    assert compute_total_pages(0, 10) == 0
    assert compute_total_pages(10, 10) == 1
    assert compute_total_pages(11, 10) == 2
    assert compute_has_next_offset(1, 10, 10) is False
    assert compute_has_next_offset(1, 10, 11) is True


def test_compute_offset_rejects_invalid_page():
    with pytest.raises(ValidationException) as exc_info:
        compute_offset(0, 10)
    assert exc_info.value.code == ErrorCode.PARAMS_INVALID.code


def test_encode_and_decode_cursor_roundtrip():
    created_at = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    cursor = encode_cursor({"id": 12, "created_at": created_at})
    payload = decode_cursor(cursor)

    assert payload["id"] == 12
    assert payload["created_at"] == created_at.isoformat()


@pytest.mark.parametrize(
    "cursor",
    ["", "   ", "not-a-cursor", "%%%", "e30", encode_cursor({"name": "no-id"})],
)
def test_decode_cursor_rejects_invalid_values(cursor):
    with pytest.raises(ValidationException) as exc_info:
        decode_cursor(cursor)
    assert exc_info.value.code == ErrorCode.INVALID_CURSOR.code
    assert exc_info.value.message == "分页游标无效"


def test_cursor_from_item_uses_id_and_sort_field():
    class Dummy:
        id = 7
        created_at = datetime(2024, 5, 6, tzinfo=timezone.utc)

    payload = decode_cursor(cursor_from_item(Dummy()))
    assert payload["id"] == 7
    assert payload["created_at"].startswith("2024-05-06")


async def test_list_users_offset_page_bounds_and_empty(db_session):
    empty = await UserService.list_users(db_session, ListParams(page=1, page_size=10))
    assert empty.items == []
    assert empty.total == 0
    assert empty.total_pages == 0
    assert empty.has_next is False
    assert empty.mode == "offset"

    for index in range(5):
        await UserService.create_user(
            db_session,
            UserCreate(
                username=f"user{index}",
                email=f"user{index}@example.com",
                password="123456",
            ),
        )

    first_page = await UserService.list_users(db_session, ListParams(page=1, page_size=2))
    assert [user.username for user in first_page.items] == ["user4", "user3"]
    assert first_page.total == 5
    assert first_page.has_next is True
    assert first_page.has_prev is False

    beyond = await UserService.list_users(db_session, ListParams(page=9, page_size=2))
    assert beyond.items == []
    assert beyond.total == 5
    assert beyond.has_next is False
    assert beyond.has_prev is True


async def test_list_users_cursor_walk_and_invalid_cursor(db_session):
    for index in range(3):
        await UserService.create_user(
            db_session,
            UserCreate(
                username=f"cursor{index}",
                email=f"cursor{index}@example.com",
                password="123456",
            ),
        )

    first = await UserService.list_users(db_session, ListParams(page_size=2))
    assert [user.username for user in first.items] == ["cursor2", "cursor1"]
    assert first.mode == "offset"
    assert first.has_next is True
    assert first.next_cursor

    second = await UserService.list_users(
        db_session,
        ListParams(page_size=2, cursor=first.next_cursor),
    )
    assert [user.username for user in second.items] == ["cursor0"]
    assert second.mode == "cursor"
    assert second.has_next is False
    assert second.next_cursor is None

    with pytest.raises(ValidationException) as exc_info:
        await UserService.list_users(db_session, ListParams(cursor="broken"))
    assert exc_info.value.code == ErrorCode.INVALID_CURSOR.code
