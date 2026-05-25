from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def get_user_by_github_id(db: AsyncSession, github_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.github_id == github_id))
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    db_user = User(
        github_id=user_in.github_id,
        username=user_in.username,
        email=user_in.email,
        avatar_url=user_in.avatar_url,
        access_token=user_in.access_token
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user_token(db: AsyncSession, user_id: int, access_token: str) -> Optional[User]:
    db_user = await get_user(db, user_id)
    if db_user:
        db_user.access_token = access_token
        await db.commit()
        await db.refresh(db_user)
    return db_user
