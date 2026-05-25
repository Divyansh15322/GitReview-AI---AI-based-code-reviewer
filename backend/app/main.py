from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown lifecycles.
    Automatically initializes SQLite database schemas on startup.
    """
    from backend.app.core.database import engine
    from backend.app.models import Base
    
    # Establish async connections and run DDL migrations
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database tables initialized successfully. Ready to receive requests.")
    yield
    # Shutdown operations (if any)
    await engine.dispose()
    print("Database connections disposed.")

# Initialize FastAPI App
app = FastAPI(
    title="GitReview AI Backend",
    description="Asynchronous multi-agent codebase review manager leveraging LangGraph, SQLAlchemy, and ChromaDB.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS)
# Allows the Streamlit application to query endpoints directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain e.g. ["http://localhost:8501"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount central api router
app.include_router(api_router)

@app.get("/", tags=["Root"])
async def root():
    return {
        "status": "healthy",
        "service": "GitReview AI Core Service",
        "demo_mode": settings.DEMO_MODE,
        "llm_configured": settings.GROQ_API_KEY is not None or settings.DEMO_MODE
    }
