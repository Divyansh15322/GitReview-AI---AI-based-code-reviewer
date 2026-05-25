from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from backend.app.core.config import settings

# Configure SQLite asynchronous database URL (needs aiosqlite driver)
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite://"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

# Create Async Engine
# check_same_thread=False is required for SQLite to support multi-threaded operations in FastAPI
connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
engine = create_async_engine(
    db_url,
    connect_args=connect_args,
    echo=False,  # Set to True for verbose SQL logging in development
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for SQLAlchemy Models
class Base(DeclarativeBase):
    pass

# FastAPI Dependency for obtaining Database Sessions in API routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
