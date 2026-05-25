import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
import git
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.services.github import GitHubService
from backend.app.services.vector_db import VectorDBService
from backend.app.crud import (
    get_repository_by_full_name, create_repository, get_repositories_by_user,
    get_repository, update_repository_indexing_status, get_user
)
from backend.app.schemas.repository import RepositoryConnect, RepositoryResponse, RepositoryCreate

router = APIRouter(prefix="/repositories", tags=["Repositories"])

async def background_index_repo(repo_id: int, repo_full_name: str, access_token: str, db: AsyncSession):
    """
    Background worker that clones a connected GitHub repository locally, 
    generates vector embeddings for all code files, updates ChromaDB, and cleans up.
    """
    temp_dir = f"./temp_repos/{repo_full_name.replace('/', '_')}"
    
    # 1. Clean workspace if directory already exists
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 2. Clone the repository asynchronously
        # Configure auth clone URL
        if settings.DEMO_MODE:
            # Skip actual cloning in Demo Mode, index directly
            pass
        else:
            token = access_token or settings.GITHUB_PAT
            clone_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
            # Execute clone
            git.Repo.clone_from(clone_url, temp_dir, depth=1) # shallow clone for maximum performance
            
        # 3. Index using Vector DB service
        vector_service = VectorDBService()
        success = await vector_service.index_repository(repo_full_name, temp_dir)
        
        if success:
            # Update index flag in relational SQLite
            await update_repository_indexing_status(db, repo_id, is_indexed=True)
            print(f"ChromaDB indexing completed successfully for {repo_full_name}")
            
    except Exception as e:
        print(f"Failed to perform background codebase RAG indexing on {repo_full_name}: {e}")
    finally:
        # 4. Storage cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@router.post("/connect", response_model=RepositoryResponse)
async def connect_repository(
    payload: RepositoryConnect,
    user_id: int = Query(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Onboards a GitHub repository:
    - Fetches metadata from GitHub API.
    - Registers in SQLite database.
    - Setup Webhook on GitHub (if in live mode).
    - Queues background indexing for codebase semantic search (RAG).
    """
    # Verify user exists
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    # Check if already connected
    existing_repo = await get_repository_by_full_name(db, payload.full_name)
    if existing_repo:
        raise HTTPException(status_code=400, detail="Repository is already connected to this workspace")

    # Fetch metadata from GitHub
    github_service = GitHubService(access_token=user.access_token)
    try:
        # Extract owner and repo names
        parts = payload.full_name.split("/")
        if len(parts) != 2:
            raise ValueError("Repository format must be 'owner/repo'")
            
        owner, repo_name = parts[0], parts[1]
        
        # Verify repository exists on GitHub
        if settings.DEMO_MODE:
            # Returns simulated repository metadata
            repo_data = {
                "id": 123456789,
                "name": repo_name,
                "owner": {"login": owner},
                "html_url": f"https://github.com/{payload.full_name}",
                "full_name": payload.full_name
            }
        else:
            url = f"https://api.github.com/repos/{payload.full_name}"
            resp = await github_service.client.get(url)
            resp.raise_for_status()
            repo_data = resp.json()

        # Webhook registration (Skipped in Demo Mode or if APP_URL is localhost)
        webhook_id = None
        webhook_secret = None
        
        if not settings.DEMO_MODE and "localhost" not in settings.APP_URL:
            try:
                # Post webhook to GitHub
                webhook_url = f"https://api.github.com/repos/{payload.full_name}/hooks"
                webhook_secret = settings.GITHUB_WEBHOOK_SECRET or "gitreview_sec_token"
                hook_payload = {
                    "name": "web",
                    "active": True,
                    "events": ["pull_request"],
                    "config": {
                        "url": f"{settings.APP_URL}/api/v1/webhooks/github",
                        "content_type": "json",
                        "secret": webhook_secret
                    }
                }
                hook_resp = await github_service.client.post(webhook_url, json=hook_payload)
                if hook_resp.status_code == 201:
                    webhook_data = hook_resp.json()
                    webhook_id = webhook_data.get("id")
                    webhook_secret = webhook_secret
            except Exception as hook_err:
                # Log and proceed, allowing webhook configuration to be completed manually if needed
                print(f"Failed to register webhook on GitHub: {hook_err}")

        # Create database entry
        repo_create = RepositoryCreate(
            github_id=repo_data["id"],
            name=repo_data["name"],
            owner_name=repo_data["owner"]["login"],
            full_name=repo_data["full_name"],
            html_url=repo_data["html_url"],
            user_id=user_id,
            webhook_id=webhook_id,
            webhook_secret=webhook_secret
        )
        
        db_repo = await create_repository(db, repo_create)
        
        # Queue asynchronous ChromaDB RAG index pipeline
        background_tasks.add_task(
            background_index_repo,
            repo_id=db_repo.id,
            repo_full_name=db_repo.full_name,
            access_token=user.access_token,
            db=db
        )
        
        return db_repo
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect repository: {str(e)}"
        )
    finally:
        await github_service.close()

@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(user_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Returns all repositories connected by the authenticated user.
    """
    return await get_repositories_by_user(db, user_id)

@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository_details(repo_id: int, db: AsyncSession = Depends(get_db)):
    """
    Fetches details of a specific repository.
    """
    repo = await get_repository(db, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

@router.post("/{repo_id}/sync", response_model=RepositoryResponse)
async def sync_repository(
    repo_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually triggers codebase crawl, updates file structures, and rebuilds ChromaDB embeddings.
    """
    repo = await get_repository(db, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
        
    user = await get_user(db, repo.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Repository owner profile missing")

    # Update state to unindexed during sync process
    await update_repository_indexing_status(db, repo.id, is_indexed=False)
    
    # Queue RAG crawling
    background_tasks.add_task(
        background_index_repo,
        repo_id=repo.id,
        repo_full_name=repo.full_name,
        access_token=user.access_token,
        db=db
    )
    
    # Reload and return
    db_repo = await get_repository(db, repo_id)
    return db_repo

@router.get("/{repo_id}/search")
async def search_repository_codebase(
    repo_id: int,
    query: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes semantic search against the indexed codebase using ChromaDB vector RAG.
    """
    repo = await get_repository(db, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
        
    vector_service = VectorDBService()
    results = await vector_service.search_codebase(repo.full_name, query, k=4)
    return results

