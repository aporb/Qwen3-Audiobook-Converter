"""User management service for cross-session job sharing."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from backend.models.queue import get_session
from backend.models.user import User, UserSession, SharedSession, SharedSessionMember

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users and cross-session sharing."""
    
    def get_or_create_user(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> User:
        """Get existing user or create new one."""
        with get_session() as session:
            # Try to find by email
            if email:
                user = session.query(User).filter(User.email == email).first()
                if user:
                    user.last_active_at = datetime.utcnow()
                    session.commit()
                    return user
            
            # Create new user
            user = User(email=email, name=name)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Created new user: {user.id}")
            return user
    
    def get_user_by_token(self, api_token: str) -> Optional[User]:
        """Get user by API token."""
        with get_session() as session:
            user = session.query(User).filter(User.api_token == api_token).first()
            if user:
                user.last_active_at = datetime.utcnow()
                session.commit()
            return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        with get_session() as session:
            return session.query(User).filter(User.id == user_id).first()
    
    def link_session_to_user(
        self,
        browser_session_id: str,
        user_id: str,
        device_info: Optional[str] = None,
    ) -> UserSession:
        """Link a browser session to a user."""
        with get_session() as session:
            # Check if already linked
            existing = (
                session.query(UserSession)
                .filter(
                    and_(
                        UserSession.browser_session_id == browser_session_id,
                        UserSession.user_id == user_id,
                    )
                )
                .first()
            )
            
            if existing:
                # Update expiration
                existing.expires_at = datetime.utcnow() + timedelta(days=90)
                session.commit()
                return existing
            
            # Create new link
            user_session = UserSession(
                user_id=user_id,
                browser_session_id=browser_session_id,
                device_info=device_info,
            )
            session.add(user_session)
            session.commit()
            session.refresh(user_session)
            logger.info(f"Linked session {browser_session_id[:8]}... to user {user_id}")
            return user_session
    
    def get_user_for_session(self, browser_session_id: str) -> Optional[User]:
        """Get user associated with a browser session."""
        with get_session() as session:
            user_session = (
                session.query(UserSession)
                .filter(UserSession.browser_session_id == browser_session_id)
                .options(joinedload(UserSession.user))
                .first()
            )
            
            if user_session and not user_session.is_expired():
                return user_session.user
            return None
    
    def get_user_sessions(self, user_id: str) -> list[UserSession]:
        """Get all active sessions for a user."""
        with get_session() as session:
            return (
                session.query(UserSession)
                .filter(
                    and_(
                        UserSession.user_id == user_id,
                        UserSession.expires_at > datetime.utcnow(),
                    )
                )
                .all()
            )
    
    def unlink_session(self, browser_session_id: str) -> bool:
        """Unlink a browser session from its user."""
        with get_session() as session:
            user_session = (
                session.query(UserSession)
                .filter(UserSession.browser_session_id == browser_session_id)
                .first()
            )
            
            if user_session:
                session.delete(user_session)
                session.commit()
                return True
            return False
    
    # ========== Shared Sessions ==========
    
    def create_shared_session(
        self,
        owner_user_id: str,
        name: str = "Shared Queue",
        expires_days: Optional[int] = None,
    ) -> SharedSession:
        """Create a new shared session."""
        with get_session() as session:
            shared = SharedSession(
                owner_user_id=owner_user_id,
                name=name,
                expires_at=datetime.utcnow() + timedelta(days=expires_days) if expires_days else None,
            )
            session.add(shared)
            session.commit()
            session.refresh(shared)
            
            # Owner is automatically a member
            member = SharedSessionMember(
                shared_session_id=shared.id,
                user_id=owner_user_id,
                can_modify=True,
            )
            session.add(member)
            session.commit()
            
            logger.info(f"Created shared session {shared.id} for user {owner_user_id}")
            return shared
    
    def join_shared_session(
        self,
        share_token: str,
        user_id: str,
    ) -> Optional[SharedSession]:
        """Join a shared session using a share token."""
        with get_session() as session:
            shared = (
                session.query(SharedSession)
                .filter(SharedSession.share_token == share_token)
                .first()
            )
            
            if not shared or not shared.is_valid():
                return None
            
            # Check if already a member
            existing = (
                session.query(SharedSessionMember)
                .filter(
                    and_(
                        SharedSessionMember.shared_session_id == shared.id,
                        SharedSessionMember.user_id == user_id,
                    )
                )
                .first()
            )
            
            if existing:
                return shared
            
            # Add as member
            member = SharedSessionMember(
                shared_session_id=shared.id,
                user_id=user_id,
                can_modify=False,  # New members can't modify by default
            )
            session.add(member)
            session.commit()
            
            logger.info(f"User {user_id} joined shared session {shared.id}")
            return shared
    
    def get_shared_sessions_for_user(self, user_id: str) -> list[SharedSession]:
        """Get all shared sessions a user is a member of."""
        with get_session() as session:
            members = (
                session.query(SharedSessionMember)
                .filter(SharedSessionMember.user_id == user_id)
                .options(joinedload(SharedSessionMember.shared_session))
                .all()
            )
            return [m.shared_session for m in members if m.shared_session.is_valid()]
    
    def can_modify_shared_session(self, shared_session_id: str, user_id: str) -> bool:
        """Check if user can modify jobs in a shared session."""
        with get_session() as session:
            member = (
                session.query(SharedSessionMember)
                .filter(
                    and_(
                        SharedSessionMember.shared_session_id == shared_session_id,
                        SharedSessionMember.user_id == user_id,
                    )
                )
                .first()
            )
            return member.can_modify if member else False
    
    def get_shared_session_members(self, shared_session_id: str) -> list[SharedSessionMember]:
        """Get all members of a shared session."""
        with get_session() as session:
            return (
                session.query(SharedSessionMember)
                .filter(SharedSessionMember.shared_session_id == shared_session_id)
                .options(joinedload(SharedSessionMember.user))
                .all()
            )


# Global user service instance
user_service = UserService()