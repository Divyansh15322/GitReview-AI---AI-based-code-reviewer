from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.models.review import Review, ReviewComment
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.schemas.review import ReviewCreate, ReviewCommentCreate

async def get_review(db: AsyncSession, review_id: int) -> Optional[Review]:
    result = await db.execute(select(Review).where(Review.id == review_id))
    return result.scalars().first()

async def get_review_with_comments(db: AsyncSession, review_id: int) -> Optional[Review]:
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.comments))
        .where(Review.id == review_id)
    )
    return result.scalars().first()

async def get_reviews_by_pr(db: AsyncSession, pr_id: int) -> List[Review]:
    result = await db.execute(
        select(Review)
        .where(Review.pull_request_id == pr_id)
        .order_by(Review.created_at.desc())
    )
    return list(result.scalars().all())

async def get_latest_review_by_pr(db: AsyncSession, pr_id: int) -> Optional[Review]:
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.comments))
        .where(Review.pull_request_id == pr_id)
        .order_by(Review.created_at.desc())
    )
    return result.scalars().first()

async def create_review(db: AsyncSession, review_in: ReviewCreate) -> Review:
    db_review = Review(
        pull_request_id=review_in.pull_request_id,
        status=review_in.status,
        bug_count=review_in.bug_count,
        security_count=review_in.security_count,
        performance_count=review_in.performance_count,
        clean_code_count=review_in.clean_code_count,
        score=review_in.score,
        duration_seconds=review_in.duration_seconds,
        summary=review_in.summary
    )
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return db_review

async def update_review(db: AsyncSession, review_id: int, update_data: Dict[str, Any]) -> Optional[Review]:
    db_review = await get_review(db, review_id)
    if db_review:
        for key, value in update_data.items():
            if hasattr(db_review, key):
                setattr(db_review, key, value)
        await db.commit()
        await db.refresh(db_review)
    return db_review

async def create_review_comment(db: AsyncSession, comment_in: ReviewCommentCreate) -> ReviewComment:
    db_comment = ReviewComment(
        review_id=comment_in.review_id,
        file_path=comment_in.file_path,
        line_number=comment_in.line_number,
        diff_hunk=comment_in.diff_hunk,
        category=comment_in.category,
        severity=comment_in.severity,
        title=comment_in.title,
        body=comment_in.body,
        suggestion=comment_in.suggestion
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

async def get_review_analytics(db: AsyncSession, user_id: int) -> Dict[str, Any]:
    """
    Computes high-level aggregated review analytics for the user's connected repositories.
    """
    # Find all repository IDs connected to this user
    repos_query = await db.execute(select(Repository.id).where(Repository.user_id == user_id))
    repo_ids = [r for r in repos_query.scalars().all()]
    
    if not repo_ids:
        return {
            "total_reviews": 0, "avg_score": 0, "bug_count": 0, "security_count": 0,
            "performance_count": 0, "clean_code_count": 0, "weekly_trends": [], "recent_issues": []
        }
    
    # Aggregated totals query
    totals_stmt = (
        select(
            func.count(Review.id).label("total"),
            func.avg(Review.score).label("avg_score"),
            func.sum(Review.bug_count).label("bugs"),
            func.sum(Review.security_count).label("sec"),
            func.sum(Review.performance_count).label("perf"),
            func.sum(Review.clean_code_count).label("clean")
        )
        .join(PullRequest, Review.pull_request_id == PullRequest.id)
        .where(PullRequest.repository_id.in_(repo_ids))
    )
    totals_res = (await db.execute(totals_stmt)).first()
    
    # Query for historical score and count charts
    history_stmt = (
        select(
            func.date(Review.created_at).label("date"),
            func.count(Review.id).label("count"),
            func.avg(Review.score).label("score")
        )
        .join(PullRequest, Review.pull_request_id == PullRequest.id)
        .where(PullRequest.repository_id.in_(repo_ids))
        .group_by(func.date(Review.created_at))
        .order_by("date")
    )
    history_res = (await db.execute(history_stmt)).all()
    
    # Query for most frequent issues (top 5 files or patterns)
    issues_stmt = (
        select(
            ReviewComment.file_path,
            ReviewComment.category,
            ReviewComment.severity,
            func.count(ReviewComment.id).label("count")
        )
        .join(Review, ReviewComment.review_id == Review.id)
        .join(PullRequest, Review.pull_request_id == PullRequest.id)
        .where(PullRequest.repository_id.in_(repo_ids))
        .group_by(ReviewComment.file_path, ReviewComment.category, ReviewComment.severity)
        .order_by(func.count(ReviewComment.id).desc())
        .limit(5)
    )
    issues_res = (await db.execute(issues_stmt)).all()

    return {
        "total_reviews": totals_res[0] or 0,
        "avg_score": round(float(totals_res[1] or 0), 1),
        "bug_count": int(totals_res[2] or 0),
        "security_count": int(totals_res[3] or 0),
        "performance_count": int(totals_res[4] or 0),
        "clean_code_count": int(totals_res[5] or 0),
        "weekly_trends": [{"date": r[0], "count": r[1], "score": round(float(r[2]), 1)} for r in history_res],
        "top_issues": [{"file_path": r[0], "category": r[1], "severity": r[2], "count": r[3]} for r in issues_res]
    }
