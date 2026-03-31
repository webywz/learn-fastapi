import pytest

from common.error_codes import ErrorCode
from common.exceptions import BusinessException
from core.security import verify_password
from schemas.user import UserCreate
from services.user_service import UserService


async def test_create_user_hashes_password(db_session):
    user = await UserService.create_user(
        db_session,
        UserCreate(
            username="alice",
            email="alice@example.com",
            password="123456",
        ),
    )

    assert user.id is not None
    assert user.hashed_password != "123456"
    assert verify_password("123456", user.hashed_password)


async def test_create_user_rejects_duplicate_email(db_session):
    await UserService.create_user(
        db_session,
        UserCreate(
            username="alice",
            email="alice@example.com",
            password="123456",
        ),
    )

    with pytest.raises(BusinessException) as exc_info:
        await UserService.create_user(
            db_session,
            UserCreate(
                username="bob",
                email="alice@example.com",
                password="abcdef",
            ),
        )

    assert exc_info.value.code == ErrorCode.EMAIL_ALREADY_EXISTS.code
