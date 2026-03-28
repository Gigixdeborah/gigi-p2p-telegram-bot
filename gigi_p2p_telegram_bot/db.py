"""
Database setup and helper functions.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL
from .models import Base

# Create asynchronous engine
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Session factory bound to the engine
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db() -> None:
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
