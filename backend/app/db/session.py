from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


@lru_cache(maxsize=1)
def session_factory() -> async_sessionmaker[AsyncSession]:
    # Lazy initialization permits contract tests to override DB dependencies
    # without requiring a running PostgreSQL instance.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory()() as session:
        yield session
