from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class RepositoryBase(BaseModel):
    github_id: int
    name: str
    owner_name: str
    full_name: str
    html_url: str

class RepositoryCreate(RepositoryBase):
    user_id: int
    webhook_id: Optional[int] = None
    webhook_secret: Optional[str] = None

class RepositoryConnect(BaseModel):
    full_name: str  # e.g., "owner/repo"
    github_pat: Optional[str] = None  # User can supply custom PAT

class RepositoryResponse(RepositoryBase):
    id: int
    user_id: int
    is_active: bool
    is_indexed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
