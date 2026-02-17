"""Queue job models using SQLAlchemy."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    """Job type enumeration."""

    TTS = "tts"
    URL_FETCH = "url_fetch"
    SUMMARIZE = "summarize"
    AUDIOBOOK = "audiobook"
    CLEANING = "cleaning"
    BATCH = "batch"


class Job(Base):
    """Job model for queue system."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    shared_session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("shared_sessions.id"), nullable=True, index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.PENDING, index=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False, index=True)
    
    # Job configuration
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Job chains and dependencies
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    parent_job_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    
    # Priority and progress
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10, lower = higher priority
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0-1.0
    progress_message: Mapped[str] = mapped_column(String(255), default="")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow() + timedelta(days=30)
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "shared_session_id": self.shared_session_id,
            "status": self.status.value,
            "job_type": self.job_type.value,
            "payload": self.payload,
            "result": self.result,
            "error_message": self.error_message,
            "dependencies": self.dependencies,
            "parent_job_id": self.parent_job_id,
            "priority": self.priority,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    def can_run(self) -> bool:
        """Check if job can be executed (pending and not paused)."""
        return self.status == JobStatus.PENDING

    def can_cancel(self) -> bool:
        """Check if job can be cancelled."""
        return self.status in (JobStatus.PENDING, JobStatus.RUNNING, JobStatus.PAUSED)


# Database setup
_engine = None
_session_maker = None


def init_database(db_path: str = "data/queue.db") -> None:
    """Initialize the database with tables."""
    global _engine, _session_maker
    
    import os
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    _engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(_engine)
    _session_maker = sessionmaker(bind=_engine)


def get_session():
    """Get a database session."""
    global _session_maker
    if _session_maker is None:
        init_database()
    return _session_maker()