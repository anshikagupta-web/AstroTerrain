from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


@lru_cache
def get_session_factory():
    # Create the engine lazily so importing the FastAPI app does not require
    # a live database connection (or eagerly load the DB driver).
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    return sessionmaker(
        bind=engine,
        class_=Session,
        autocommit=False,
        autoflush=False,
    )


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
