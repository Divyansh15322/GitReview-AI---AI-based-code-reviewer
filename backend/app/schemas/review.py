from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.pull_request import PullRequestResponse

class ReviewCommentBase(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    diff_hunk: Optional[str] = None
    category: str  # bug, security, performance, style
    severity: str  # info, warning, critical
    title: str
    body: str  # markdown explanation
    suggestion: Optional[str] = None  # markdown suggested code

class ReviewCommentCreate(ReviewCommentBase):
    review_id: int

class ReviewCommentResponse(ReviewCommentBase):
    id: int
    review_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReviewBase(BaseModel):
    pull_request_id: int
    status: str  # pending, running, completed, failed
    bug_count: int = 0
    security_count: int = 0
    performance_count: int = 0
    clean_code_count: int = 0
    score: int = 100
    duration_seconds: Optional[float] = None
    summary: Optional[str] = None  # markdown aggregate report

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReviewDetailResponse(ReviewResponse):
    comments: List[ReviewCommentResponse] = []
    
    # We will use this to serialize detailed reviews including the PR info
    model_config = ConfigDict(from_attributes=True)

class ReviewTrigger(BaseModel):
    repository_full_name: str  # e.g., "owner/repo"
    pr_number: int
