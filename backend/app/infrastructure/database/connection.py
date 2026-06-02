from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.shared.config import get_settings

settings = get_settings()

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        password = settings.get_db_password()
        url = (
            f"postgresql+psycopg://{settings.db_host}/{settings.db_name}"
            f"?user=clbilling_admin&password={password}"
            f"&sslmode={'require' if settings.env != 'local' else 'disable'}"
        )
        # pool_pre_ping=True detecta conexiones muertas (importante con Aurora que escala a 0)
        _engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=settings.env == "local",
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


class Base(DeclarativeBase):
    pass
