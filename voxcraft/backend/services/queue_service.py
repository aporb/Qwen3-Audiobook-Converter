"""Queue service for job management with SSE and user support."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from backend.models.queue import Job, JobStatus, JobType, get_session, init_database
from backend.utils.queue_sse import queue_sse_manager

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing job queue operations."""

    def __init__(self, db_path: str = "data/queue.db") -> None:
        """Initialize the queue service."""
        init_database(db_path)
        self._db_path = db_path

    # ========== Job Creation ==========

    def enqueue(
        self,
        session_id: str,
        job_type: JobType,
        payload: dict[str, Any],
        priority: int = 5,
        dependencies: Optional[list[str]] = None,
        parent_job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        shared_session_id: Optional[str] = None,
    ) -> Job:
        """Add a new job to the queue."""
        with get_session() as session:
            job = Job(
                session_id=session_id,
                user_id=user_id,
                shared_session_id=shared_session_id,
                job_type=job_type,
                payload=payload,
                priority=max(1, min(10, priority)),  # Clamp to 1-10
                dependencies=dependencies or [],
                parent_job_id=parent_job_id,
                status=JobStatus.PENDING,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            logger.info(f"Enqueued job {job.id} of type {job_type.value}")
            
            # Publish SSE event
            asyncio.create_task(
                queue_sse_manager.publish_job_created(session_id, job.to_dict())
            )
            
            return job

    def enqueue_chain(
        self,
        session_id: str,
        steps: list[dict[str, Any]],
        user_id: Optional[str] = None,
        shared_session_id: Optional[str] = None,
    ) -> list[Job]:
        """Enqueue a chain of dependent jobs.
        
        Each step should have: type, payload, priority (optional)
        Returns list of created jobs in execution order.
        """
        jobs: list[Job] = []
        prev_job_id: Optional[str] = None

        with get_session() as session:
            for i, step in enumerate(steps):
                job = Job(
                    session_id=session_id,
                    user_id=user_id,
                    shared_session_id=shared_session_id,
                    job_type=JobType(step["type"]),
                    payload=step.get("payload", {}),
                    priority=step.get("priority", 5),
                    dependencies=[prev_job_id] if prev_job_id else [],
                    parent_job_id=jobs[0].id if jobs else None,
                    status=JobStatus.PENDING,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=30),
                )
                session.add(job)
                session.flush()  # Get ID without committing
                jobs.append(job)
                prev_job_id = job.id

            session.commit()
            # Refresh all jobs to get their IDs
            for job in jobs:
                session.refresh(job)

        logger.info(f"Enqueued job chain with {len(jobs)} steps")
        
        # Publish SSE events for all jobs
        for job in jobs:
            asyncio.create_task(
                queue_sse_manager.publish_job_created(session_id, job.to_dict())
            )
        
        return jobs

    # ========== Job Retrieval ==========

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        with get_session() as session:
            return session.query(Job).filter(Job.id == job_id).first()

    def get_jobs_by_session(
        self,
        session_id: str,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        """Get jobs for a session with optional filtering."""
        with get_session() as session:
            query = session.query(Job).filter(Job.session_id == session_id)

            if status:
                query = query.filter(Job.status == status)
            if job_type:
                query = query.filter(Job.job_type == job_type)

            return (
                query.order_by(desc(Job.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

    def get_jobs_by_user(
        self,
        user_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        """Get jobs for a user across all sessions."""
        with get_session() as session:
            query = session.query(Job).filter(Job.user_id == user_id)

            if status:
                query = query.filter(Job.status == status)

            return (
                query.order_by(desc(Job.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

    def get_jobs_by_shared_session(
        self,
        shared_session_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        """Get jobs in a shared session."""
        with get_session() as session:
            query = session.query(Job).filter(Job.shared_session_id == shared_session_id)

            if status:
                query = query.filter(Job.status == status)

            return (
                query.order_by(desc(Job.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

    def get_pending_jobs(self, session_id: str, limit: int = 10) -> list[Job]:
        """Get pending jobs for execution, ordered by priority."""
        with get_session() as session:
            return (
                session.query(Job)
                .filter(
                    and_(
                        Job.session_id == session_id,
                        Job.status == JobStatus.PENDING,
                    )
                )
                .order_by(Job.priority, Job.created_at)
                .limit(limit)
                .all()
            )

    def get_active_jobs(self, session_id: str) -> list[Job]:
        """Get currently running or paused jobs."""
        with get_session() as session:
            return (
                session.query(Job)
                .filter(
                    and_(
                        Job.session_id == session_id,
                        Job.status.in_([JobStatus.RUNNING, JobStatus.PAUSED]),
                    )
                )
                .all()
            )

    # ========== Job Status Updates ==========

    def mark_running(self, job_id: str) -> bool:
        """Mark a job as running."""
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job or job.status != JobStatus.PENDING:
                return False

            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Job {job_id} started")
            
            # Publish SSE event
            asyncio.create_task(
                queue_sse_manager.publish_job_update(job.session_id, job.to_dict())
            )
            
            return True

    def update_progress(
        self,
        job_id: str,
        progress: float,
        message: str = "",
    ) -> bool:
        """Update job progress."""
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job or job.status != JobStatus.RUNNING:
                return False

            job.progress = max(0.0, min(1.0, progress))
            job.progress_message = message
            job.updated_at = datetime.utcnow()
            session.commit()
            
            # Publish SSE event (throttle to avoid spam)
            # Only publish every 5% or on significant message changes
            if int(progress * 100) % 5 == 0:
                asyncio.create_task(
                    queue_sse_manager.publish_job_update(job.session_id, job.to_dict())
                )
            
            return True

    def mark_completed(
        self,
        job_id: str,
        result: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Mark a job as completed."""
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return False

            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.result = result or {}
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Job {job_id} completed")
            
            # Publish SSE event
            asyncio.create_task(
                queue_sse_manager.publish_job_completed(job.session_id, job.to_dict())
            )
            
            return True

    def mark_failed(self, job_id: str, error_message: str) -> bool:
        """Mark a job as failed."""
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                return False

            job.status = JobStatus.FAILED
            job.error_message = error_message
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            session.commit()
            logger.error(f"Job {job_id} failed: {error_message}")
            
            # Publish SSE event
            asyncio.create_task(
                queue_sse_manager.publish_job_failed(job.session_id, job_id, error_message)
            )
            
            return True

    def mark_cancelled(self, job_id: str) -> bool:
        """Mark a job as cancelled."""
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job or job.is_terminal():
                return False

            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Job {job_id} cancelled")
            
            # Publish SSE event
            asyncio.create_task(
                queue_sse_manager.publish_job_update(job.session_id, job.to_dict())
            )
            
            return True

    def pause_job(self, job_id: str) -> bool:
        """Pause a running job."""
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job or job.status != JobStatus.RUNNING:
                return False

            job.status = JobStatus.PAUSED
            job.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Job {job_id} paused")
            
            # Publish SSE event
            asyncio.create_task(
                queue_sse_manager.publish_job_update(job.session_id, job.to_dict())
            )
            
            return True

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job or job.status != JobStatus.PAUSED:
                return False

            job.status = JobStatus.PENDING
            job.updated_at = datetime.utcnow()
            session.commit()
            logger.info(f"Job {job_id} resumed")
            
            # Publish SSE event
            asyncio.create_task(
                queue_sse_manager.publish_job_update(job.session_id, job.to_dict())
            )
            
            return True

    def update_priority(self, job_id: str, priority: int) -> bool:
        """Update job priority."""
        with get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job or job.is_terminal():
                return False

            job.priority = max(1, min(10, priority))
            job.updated_at = datetime.utcnow()
            session.commit()
            
            # Publish SSE event
            asyncio.create_task(
                queue_sse_manager.publish_job_update(job.session_id, job.to_dict())
            )
            
            return True

    # ========== Cleanup ==========

    def cleanup_expired(self, days: int = 30) -> int:
        """Remove jobs older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        with get_session() as session:
            result = (
                session.query(Job)
                .filter(Job.created_at < cutoff)
                .delete(synchronize_session=False)
            )
            session.commit()
            if result:
                logger.info(f"Cleaned up {result} expired jobs")
            return result

    def clear_completed(self, session_id: str) -> int:
        """Clear all completed/failed/cancelled jobs for a session."""
        with get_session() as session:
            result = (
                session.query(Job)
                .filter(
                    and_(
                        Job.session_id == session_id,
                        Job.status.in_([
                            JobStatus.COMPLETED,
                            JobStatus.FAILED,
                            JobStatus.CANCELLED,
                        ]),
                    )
                )
                .delete(synchronize_session=False)
            )
            session.commit()
            return result

    def get_stats(self, session_id: str) -> dict[str, int]:
        """Get job statistics for a session."""
        with get_session() as session:
            stats = {
                "pending": session.query(Job).filter(
                    and_(Job.session_id == session_id, Job.status == JobStatus.PENDING)
                ).count(),
                "running": session.query(Job).filter(
                    and_(Job.session_id == session_id, Job.status == JobStatus.RUNNING)
                ).count(),
                "paused": session.query(Job).filter(
                    and_(Job.session_id == session_id, Job.status == JobStatus.PAUSED)
                ).count(),
                "completed": session.query(Job).filter(
                    and_(Job.session_id == session_id, Job.status == JobStatus.COMPLETED)
                ).count(),
                "failed": session.query(Job).filter(
                    and_(Job.session_id == session_id, Job.status == JobStatus.FAILED)
                ).count(),
                "cancelled": session.query(Job).filter(
                    and_(Job.session_id == session_id, Job.status == JobStatus.CANCELLED)
                ).count(),
            }
            stats["total_active"] = stats["pending"] + stats["running"] + stats["paused"]
            return stats

    def get_stats_for_user(self, user_id: str) -> dict[str, int]:
        """Get job statistics for a user across all sessions."""
        with get_session() as session:
            stats = {
                "pending": session.query(Job).filter(
                    and_(Job.user_id == user_id, Job.status == JobStatus.PENDING)
                ).count(),
                "running": session.query(Job).filter(
                    and_(Job.user_id == user_id, Job.status == JobStatus.RUNNING)
                ).count(),
                "paused": session.query(Job).filter(
                    and_(Job.user_id == user_id, Job.status == JobStatus.PAUSED)
                ).count(),
                "completed": session.query(Job).filter(
                    and_(Job.user_id == user_id, Job.status == JobStatus.COMPLETED)
                ).count(),
                "failed": session.query(Job).filter(
                    and_(Job.user_id == user_id, Job.status == JobStatus.FAILED)
                ).count(),
                "cancelled": session.query(Job).filter(
                    and_(Job.user_id == user_id, Job.status == JobStatus.CANCELLED)
                ).count(),
            }
            stats["total_active"] = stats["pending"] + stats["running"] + stats["paused"]
            return stats


# Global queue service instance
queue_service = QueueService()