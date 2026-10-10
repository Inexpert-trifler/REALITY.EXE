import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.init_db import init_db


@pytest.mark.asyncio
async def test_init_db_utility(db_session: AsyncSession):
    """Test init_db utility verifies database connection cleanly."""
    await init_db(db_session)
