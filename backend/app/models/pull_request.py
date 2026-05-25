from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.core.database import Base

class PullRequest(Base):
    __tablename__ = "pull_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    
    number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)  # PR number on GitHub
    title: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, default="open")  # open, closed, merged
    
    head_sha: Mapped[str] = mapped_column(String, nullable=False)  # target branch commit sha
    base_sha: Mapped[str] = mapped_column(String, nullable=False)  # source branch commit sha
    html_url: Mapped[str] = mapped_column(String, nullable=False)
    user_username: Mapped[str] = mapped_column(String, nullable=False)  # PR creator username
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    merged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    repository = relationship("Repository", back_populates="pull_requests")
    reviews = relationship("Review", back_populates="pull_request", cascade="all, delete-orphan")
