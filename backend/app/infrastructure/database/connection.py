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
            f"?user={settings.db_user}&password={password}"
            f"&sslmode={'require' if settings.env != 'local' else 'disable'}"
        )
        # pool_pre_ping=True detecta conexiones muertas (importante con Aurora que escala a 0)
        # connect_args timeout: max espera para despertar Aurora desde 0 capacity
        _engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=50,  # espera hasta 50s para obtener conexión del pool
            connect_args={"connect_timeout": 45},  # timeout de conexión TCP a Aurora
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
