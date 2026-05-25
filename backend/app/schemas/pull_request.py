from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class PullRequestBase(BaseModel):
    repository_id: int
    number: int
    title: str
    state: str  # open, closed, merged
    head_sha: str
    base_sha: str
    html_url: str
    user_username: str

class PullRequestCreate(PullRequestBase):
    pass

class PullRequestResponse(PullRequestBase):
    id: int
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
