"""User and shared session models."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.queue import Base


class User(Base):
    """User model for cross-session job sharing."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: secrets.token_urlsafe(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions: Mapped[list["UserSession"]] = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Convert user to dictionary (excludes sensitive data)."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }
    
    def refresh_token(self) -> str:
        """Generate new API token."""
        self.api_token = secrets.token_urlsafe(32)
        return self.api_token


class UserSession(Base):
    """Links browser sessions to users for job sharing."""
    
    __tablename__ = "user_sessions"
    
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    browser_session_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    device_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.utcnow() + timedelta(days=90)
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        UniqueConstraint("user_id", "browser_session_id", name="uix_user_browser_session"),
    )
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "browser_session_id": self.browser_session_id[:8] + "...",
            "device_info": self.device_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
        }


class SharedSession(Base):
    """Allows sharing jobs across multiple users/sessions."""
    
    __tablename__ = "shared_sessions"
    
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    share_token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: secrets.token_urlsafe(32))
    name: Mapped[str] = mapped_column(String(100), default="Shared Queue")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def is_valid(self) -> bool:
        """Check if share is still valid."""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def to_dict(self) -> dict:
        """Convert shared session to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid(),
        }


class SharedSessionMember(Base):
    """Links users to shared sessions."""
    
    __tablename__ = "shared_session_members"
    
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    shared_session_id: Mapped[str] = mapped_column(ForeignKey("shared_sessions.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    can_modify: Mapped[bool] = mapped_column(default=False)  # Can they cancel/reorder jobs?
    
    __table_args__ = (
        UniqueConstraint("shared_session_id", "user_id", name="uix_shared_session_member"),
    )