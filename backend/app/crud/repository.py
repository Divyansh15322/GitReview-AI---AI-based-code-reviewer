from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.repository import Repository
from backend.app.schemas.repository import RepositoryCreate

async def get_repository(db: AsyncSession, repo_id: int) -> Optional[Repository]:
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    return result.scalars().first()

async def get_repository_by_github_id(db: AsyncSession, github_id: int) -> Optional[Repository]:
    result = await db.execute(select(Repository).where(Repository.github_id == github_id))
    return result.scalars().first()

async def get_repository_by_full_name(db: AsyncSession, full_name: str) -> Optional[Repository]:
    result = await db.execute(select(Repository).where(Repository.full_name == full_name))
    return result.scalars().first()

async def get_repositories_by_user(db: AsyncSession, user_id: int) -> List[Repository]:
    result = await db.execute(select(Repository).where(Repository.user_id == user_id))
    return list(result.scalars().all())

async def create_repository(db: AsyncSession, repo_in: RepositoryCreate) -> Repository:
    db_repo = Repository(
        github_id=repo_in.github_id,
        name=repo_in.name,
        owner_name=repo_in.owner_name,
        full_name=repo_in.full_name,
        html_url=repo_in.html_url,
        user_id=repo_in.user_id,
        webhook_id=repo_in.webhook_id,
        webhook_secret=repo_in.webhook_secret,
        is_active=True,
        is_indexed=False
    )
    db.add(db_repo)
    await db.commit()
    await db.refresh(db_repo)
    return db_repo

async def update_repository_indexing_status(db: AsyncSession, repo_id: int, is_indexed: bool) -> Optional[Repository]:
    db_repo = await get_repository(db, repo_id)
    if db_repo:
        db_repo.is_indexed = is_indexed
        await db.commit()
        await db.refresh(db_repo)
    return db_repo
