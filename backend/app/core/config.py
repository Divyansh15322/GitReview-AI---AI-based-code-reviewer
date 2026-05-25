import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Core Application Settings
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:8501"
    DEMO_MODE: bool = True
    
    # FastAPI Backend Configuration
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    DATABASE_URL: str = "sqlite+aiosqlite:///./gitreview.db"
    
    # ChromaDB Vector Storage Settings
    CHROMA_DB_PATH: str = "./chroma_db"
    EMBEDDINGS_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Groq LLM API Configuration
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # GitHub OAuth & Integration Configuration
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_PAT: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None

# Get absolute path to the backend project root
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
# Base workspace path
WORKSPACE_ROOT = BACKEND_ROOT.parent

# Instantiated settings object
settings = Settings()
