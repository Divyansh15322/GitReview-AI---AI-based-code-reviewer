import hmac
import hashlib
import json
from fastapi import APIRouter, Request, Depends, HTTPException, Header, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.crud import (
    get_repository_by_github_id, create_pull_request, get_pull_request_by_number,
    create_review, update_pull_request_state, get_user
)
from backend.app.schemas.pull_request import PullRequestCreate
from backend.app.schemas.review import ReviewCreate

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Helper to verify HMAC SHA-256 signature
async def verify_signature(request: Request, x_hub_signature_256: str = Header(None)):
    if settings.DEMO_MODE:
        return True # Bypass in Demo Mode
        
    secret = settings.GITHUB_WEBHOOK_SECRET
    if not secret:
        return True # Proceed if webhook signing not configured
        
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="X-Hub-Signature-256 header missing")
        
    body = await request.body()
    signature = "sha256=" + hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Cryptographic webhook signature verification failed")

@router.post("/github")
async def github_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _ = Depends(verify_signature)
):
    """
    Receives incoming webhook notifications from GitHub.
    When a Pull Request is opened or updated (synchronized), 
    spawns a parallel multi-agent code review in a background worker task.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    # Standard ping event sent by GitHub upon hook registration
    if "zen" in payload:
        return {"message": "Webhook successfully registered. Zen: " + payload["zen"]}
        
    event = request.headers.get("X-GitHub-Event")
    if event != "pull_request":
        return {"message": f"Event '{event}' ignored. Action restricted to pull_request."}
        
    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened"}:
        return {"message": f"Action '{action}' ignored. Only opened/synchronize/reopened events trigger reviews."}
        
    pr_data = payload["pull_request"]
    repo_data = payload["repository"]
    
    # 1. Fetch Repository record from SQLite
    repo = await get_repository_by_github_id(db, repo_data["id"])
    if not repo:
        raise HTTPException(status_code=404, detail="Triggering repository not onboarded in database")
        
    if not repo.is_active:
        return {"message": "Repository is connected but currently set to inactive."}

    user = await get_user(db, repo.user_id)
    if not user:
         raise HTTPException(status_code=404, detail="Owner credentials not found")
         
    # 2. Register or update PullRequest state in SQLite
    pr_number = pr_data["number"]
    db_pr = await get_pull_request_by_number(db, repo.id, pr_number)
    
    if not db_pr:
        pr_create = PullRequestCreate(
            repository_id=repo.id,
            number=pr_number,
            title=pr_data["title"],
            state="open",
            head_sha=pr_data["head"]["sha"],
            base_sha=pr_data["base"]["sha"],
            html_url=pr_data["html_url"],
            user_username=pr_data["user"]["login"]
        )
        db_pr = await create_pull_request(db, pr_create)
    else:
        # Update head branch commit SHA and title on new sync updates
        db_pr.head_sha = pr_data["head"]["sha"]
        db_pr.title = pr_data["title"]
        db_pr.state = "open"
        await db.commit()

    # 3. Create a pending Review instance
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
    
    # Import the worker centrally to prevent circular dependencies
    from backend.app.api.reviews import trigger_review_pipeline_task
    
    # 4. Schedule background review workflow execution
    background_tasks.add_task(
        trigger_review_pipeline_task,
        review_id=db_review.id,
        repo_id=repo.id,
        pr_id=db_pr.id,
        pr_number=pr_number,
        head_sha=db_pr.head_sha,
        base_sha=db_pr.base_sha,
        access_token=user.access_token,
        db=db
    )
    
    return {
        "message": "Review workflow triggered.",
        "review_id": db_review.id,
        "pull_request_id": db_pr.id,
        "status": "pending"
    }
