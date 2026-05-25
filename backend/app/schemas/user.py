from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class UserBase(BaseModel):
    github_id: int
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    access_token: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
