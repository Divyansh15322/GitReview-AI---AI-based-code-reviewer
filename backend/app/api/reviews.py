import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.services.github import GitHubService
from backend.app.crud import (
    get_repository_by_full_name, create_pull_request, get_pull_request_by_number,
    create_review, update_review, create_review_comment, get_review_with_comments,
    get_reviews_by_pr, get_review_analytics, get_pull_request, get_repository, get_user
)
from backend.app.schemas.review import ReviewResponse, ReviewDetailResponse, ReviewTrigger, ReviewCreate, ReviewCommentCreate
from backend.app.schemas.pull_request import PullRequestCreate

router = APIRouter(prefix="/reviews", tags=["Reviews"])

async def trigger_review_pipeline_task(
    review_id: int,
    repo_id: int,
    pr_id: int,
    pr_number: int,
    head_sha: str,
    base_sha: str,
    access_token: str,
    db: AsyncSession
):
    """
    Core review orchestrator. Executes as an asynchronous background worker task:
    1. Fetches raw PR diffs from GitHub.
    2. Parses diff to isolate added lines and line mappings.
    3. Runs parallel Multi-Agent LangGraph workflow.
    4. Records findings in database and publishes inline review comments to GitHub.
    """
    start_time = time.time()
    
    # Update state to running
    await update_review(db, review_id, {"status": "running"})
    
    github_service = GitHubService(access_token=access_token)
    repo = await get_repository(db, repo_id)
    
    try:
        # Fetch PR Diff
        diff_text = await github_service.get_pr_diff(repo.full_name, pr_number)
        
        # Parse modified line hunks
        parsed_files = github_service.parse_diff(diff_text)
        
        if not parsed_files:
            # Complete review immediately if no changes were parsed
            duration = round(time.time() - start_time, 2)
            await update_review(db, review_id, {
                "status": "completed",
                "score": 100,
                "summary": "### 🎉 Code Review Complete: No modified files found in this Pull Request.",
                "duration_seconds": duration
            })
            return

        # Run multi-agent LangGraph workflow. Import lazily so API startup stays fast.
        from backend.app.agents import run_code_review_workflow

        final_state = await run_code_review_workflow(
            repository_id=repo_id,
            repository_full_name=repo.full_name,
            pr_number=pr_number,
            commit_sha=head_sha,
            parsed_files=parsed_files
        )
        
        # Parse final findings
        comments_list = final_state.get("comments", [])
        
        # Save comments to database and prepare payload for GitHub
        github_comments_payload = []
        
        for c in comments_list:
            # Create DB comment
            comment_create = ReviewCommentCreate(
                review_id=review_id,
                file_path=c["file_path"],
                line_number=c.get("line_number"),
                diff_hunk=c.get("diff_hunk"),
                category=c["category"],
                severity=c["severity"],
                title=c["title"],
                body=c["body"],
                suggestion=c.get("suggestion")
            )
            await create_review_comment(db, comment_create)
            
            # Format suggestions neatly as standard GitHub markdown suggestion blocks
            formatted_body = f"### 🤖 AI Reviewer: **{c['title']}**\n\n_{c['body']}_"
            if c.get("suggestion"):
                formatted_body += f"\n\n```suggestion\n{c['suggestion']}\n```"
                
            github_comments_payload.append({
                "path": c["file_path"],
                "line": c["line_number"],
                "body": formatted_body
            })

        # Submit comments and summary to GitHub Pull Request
        summary_markdown = final_state.get("summary", "Review completed successfully.")
        
        try:
            await github_service.post_pr_review(
                repo_full_name=repo.full_name,
                pr_number=pr_number,
                commit_sha=head_sha,
                comments=github_comments_payload,
                summary_body=summary_markdown
            )
        except Exception as gh_err:
            print(f"Failed to post comments back to GitHub API: {gh_err}")

        # Record metrics and completion state in database
        duration = round(time.time() - start_time, 2)
        await update_review(db, review_id, {
            "status": "completed",
            "bug_count": final_state.get("bug_count", 0),
            "security_count": final_state.get("security_count", 0),
            "performance_count": final_state.get("performance_count", 0),
            "clean_code_count": final_state.get("clean_code_count", 0),
            "score": final_state.get("score", 100),
            "summary": summary_markdown,
            "duration_seconds": duration
        })

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        print(f"Exception running Review Workflow: {e}")
        await update_review(db, review_id, {
            "status": "failed",
            "summary": f"### 🛑 Review Run Failed\n\nAn unexpected exception occurred during execution:\n```\n{str(e)}\n```",
            "duration_seconds": duration
        })
    finally:
        await github_service.close()

@router.post("/trigger", response_model=ReviewResponse)
async def trigger_manual_review(
    payload: ReviewTrigger,
    user_id: int = Query(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually triggers pull request code reviews by supplying repository full name and PR number.
    Perfect for quick hackathon demonstrations!
    """
    # 1. Fetch Repository record from SQLite
    repo = await get_repository_by_full_name(db, payload.repository_full_name)
    if not repo:
        raise HTTPException(
            status_code=404, 
            detail=f"Repository '{payload.repository_full_name}' is not onboarded yet. Connect it first."
        )
        
    user = await get_user(db, repo.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Owner credentials not found")

    # 2. Fetch/Mock PR metadata from GitHub
    github_service = GitHubService(access_token=user.access_token)
    try:
        pr_data = await github_service.get_pr_info(repo.full_name, payload.pr_number)
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Could not retrieve Pull Request from GitHub: {str(e)}"
        )
    finally:
        await github_service.close()

    # 3. Create or update PullRequest in SQLite
    db_pr = await get_pull_request_by_number(db, repo.id, payload.pr_number)
    if not db_pr:
        pr_create = PullRequestCreate(
            repository_id=repo.id,
            number=payload.pr_number,
            title=pr_data["title"],
            state="open",
            head_sha=pr_data["head"]["sha"],
            base_sha=pr_data["base"]["sha"],
            html_url=pr_data["html_url"],
            user_username=pr_data["user"]["login"]
        )
        db_pr = await create_pull_request(db, pr_create)
    else:
        db_pr.head_sha = pr_data["head"]["sha"]
        db_pr.title = pr_data["title"]
        db_pr.state = "open"
        await db.commit()

    # 4. Create Review entry
    review_create = ReviewCreate(
        pull_request_id=db_pr.id,
        status="pending",
        bug_count=0,
        security_count=0,
        performance_count=0,
        clean_code_count=0,
        score=100
    )
    db_review = await create_review(db, review_create)
    
    # 5. Dispatch background task
    background_tasks.add_task(
        trigger_review_pipeline_task,
        review_id=db_review.id,
        repo_id=repo.id,
        pr_id=db_pr.id,
        pr_number=payload.pr_number,
        head_sha=db_pr.head_sha,
        base_sha=db_pr.base_sha,
        access_token=user.access_token,
        db=db
    )
    
    return db_review

@router.get("/pr/{pr_id}", response_model=list[ReviewResponse])
async def list_reviews_for_pr(pr_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns the history of all reviews executed on a specific pull request.
    """
    return await get_reviews_by_pr(db, pr_id)

@router.get("/analytics")
async def get_dashboard_analytics(user_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Aggregates historical review data to feed dashboard analytics and charts.
    """
    return await get_review_analytics(db, user_id)

@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review_details(review_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieves complete results of a specific review run, including all inline comments.
    """
    review = await get_review_with_comments(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review run not found")
    return review
