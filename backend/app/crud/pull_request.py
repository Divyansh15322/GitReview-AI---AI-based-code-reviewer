from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.pull_request import PullRequest
from backend.app.schemas.pull_request import PullRequestCreate

async def get_pull_request(db: AsyncSession, pr_id: int) -> Optional[PullRequest]:
    result = await db.execute(select(PullRequest).where(PullRequest.id == pr_id))
    return result.scalars().first()

async def get_pull_request_by_number(db: AsyncSession, repository_id: int, number: int) -> Optional[PullRequest]:
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.repository_id == repository_id,
            PullRequest.number == number
        )
    )
    return result.scalars().first()

async def get_pull_requests_by_repo(db: AsyncSession, repository_id: int) -> List[PullRequest]:
    result = await db.execute(
        select(PullRequest)
        .where(PullRequest.repository_id == repository_id)
        .order_by(PullRequest.created_at.desc())
    )
    return list(result.scalars().all())

async def create_pull_request(db: AsyncSession, pr_in: PullRequestCreate) -> PullRequest:
    db_pr = PullRequest(
        repository_id=pr_in.repository_id,
        number=pr_in.number,
        title=pr_in.title,
        state=pr_in.state,
        head_sha=pr_in.head_sha,
        base_sha=pr_in.base_sha,
        html_url=pr_in.html_url,
        user_username=pr_in.user_username
    )
    db.add(db_pr)
    await db.commit()
    await db.refresh(db_pr)
    return db_pr

async def update_pull_request_state(db: AsyncSession, pr_id: int, state: str) -> Optional[PullRequest]:
    db_pr = await get_pull_request(db, pr_id)
    if db_pr:
        db_pr.state = state
        await db.commit()
        await db.refresh(db_pr)
    return db_pr
