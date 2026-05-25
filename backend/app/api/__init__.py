from fastapi import APIRouter
from backend.app.api.auth import router as auth_router
from backend.app.api.repositories import router as repos_router
from backend.app.api.webhooks import router as webhooks_router
from backend.app.api.reviews import router as reviews_router

# Central API Router v1
api_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_router.include_router(auth_router)
api_router.include_router(repos_router)
api_router.include_router(webhooks_router)
api_router.include_router(reviews_router)

__all__ = ["api_router"]
