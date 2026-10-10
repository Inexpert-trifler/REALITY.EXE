import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


@pytest.mark.asyncio
async def test_db_user_creation(db_session: AsyncSession):
    """Test creating a user record in the database."""
    user = User(
        email="testplayer@reality.exe",
        username="testplayer",
        password_hash=hash_password("SuperSecret123!"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "testplayer@reality.exe"

    result = await db_session.execute(select(User).where(User.username == "testplayer"))
    queried_user = result.scalar_one_or_none()
    assert queried_user is not None
    assert queried_user.id == user.id
