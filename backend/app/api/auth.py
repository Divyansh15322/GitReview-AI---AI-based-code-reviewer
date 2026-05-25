from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
import httpx
import os
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.crud import get_user_by_github_id, create_user, update_user_token
from backend.app.schemas.user import UserCreate

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/login")
async def github_login():
    """
    Redirects the user to GitHub's OAuth login screen.
    If running in DEMO_MODE or without client secrets, bypasses with high-fidelity mock redirects.
    """
    github_client_id = settings.GITHUB_CLIENT_ID or os.getenv("GITHUB_CLIENT_ID")
    if github_client_id == "your_github_oauth_client_id":
        github_client_id = None

    if settings.DEMO_MODE or not github_client_id:
        # Seamlessly redirect straight to the callback with simulated parameters
        redirect_url = f"{settings.APP_URL}/api/v1/auth/callback?code=mock_oauth_code"
        return RedirectResponse(url=redirect_url)

    github_oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={github_client_id}"
        f"&scope=repo,admin:repo_hook,user"
    )
    return RedirectResponse(url=github_oauth_url)

@router.get("/callback")
async def github_callback(code: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Processes the GitHub callback, exchanges authorization code for an access token,
    registers or updates the user profile in our database, and redirects back to Streamlit.
    """
    frontend_target_url = "http://localhost:8501"  # Streamlit default port

    # 1. Bypassed Callback Flow for offline Demo Mode
    if settings.DEMO_MODE or code == "mock_oauth_code" or not settings.GITHUB_CLIENT_ID:
        mock_user = {
            "github_id": 99999,
            "username": "hackathon-judge",
            "email": "judge@hackathon.ai",
            "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
            "access_token": "mock_github_access_token_token"
        }
        
        # Check if dummy user exists, otherwise create
        db_user = await get_user_by_github_id(db, mock_user["github_id"])
        if not db_user:
            user_in = UserCreate(**mock_user)
            db_user = await create_user(db, user_in)
        else:
            await update_user_token(db, db_user.id, mock_user["access_token"])
            
        # Redirect user back to Streamlit dashboard, passing session attributes as queries
        return RedirectResponse(
            url=f"{frontend_target_url}/?username={db_user.username}&access_token={db_user.access_token}&user_id={db_user.id}"
        )

    # 2. Production Live Exchange flow
    try:
        # Exchange code for token
        token_url = "https://github.com/login/oauth/access_token"
        token_payload = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code
        }
        token_headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(token_url, json=token_payload, headers=token_headers)
            token_resp.raise_for_status()
            token_data = token_resp.json()
            
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Failed to obtain access token from GitHub")
                
            # Fetch user profile using access token
            user_url = "https://api.github.com/user"
            user_headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/json"
            }
            user_resp = await client.get(user_url, headers=user_headers)
            user_resp.raise_for_status()
            user_data = user_resp.json()
            
        # Parse payload
        github_id = user_data["id"]
        username = user_data["login"]
        email = user_data.get("email")
        avatar_url = user_data.get("avatar_url")
        
        db_user = await get_user_by_github_id(db, github_id)
        if not db_user:
            user_in = UserCreate(
                github_id=github_id,
                username=username,
                email=email,
                avatar_url=avatar_url,
                access_token=access_token
            )
            db_user = await create_user(db, user_in)
        else:
            await update_user_token(db, db_user.id, access_token)
            
        # Redirect user back to Streamlit dashboard
        return RedirectResponse(
            url=f"{frontend_target_url}/?username={db_user.username}&access_token={db_user.access_token}&user_id={db_user.id}"
        )
    except Exception as e:
        # Fallback redirect to Streamlit with error code
        return RedirectResponse(url=f"{frontend_target_url}/?error={str(e)}")
