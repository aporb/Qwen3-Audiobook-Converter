"""Queue management router."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from sse_starlette.sse import EventSourceResponse

from backend.models.queue import Job, JobStatus, JobType
from backend.services.queue_service import queue_service
from backend.services.user_service import user_service
from backend.utils.job_runner import job_runner
from backend.utils.queue_sse import queue_sse_manager, create_sse_response

router = APIRouter(prefix="/api/queue", tags=["Queue"])


# ========== Request/Response Models ==========

class SubmitJobRequest(BaseModel):
    """Request to submit a new job."""
    job_type: str = Field(..., description="Type of job: tts, url_fetch, summarize, audiobook, cleaning, batch")
    payload: dict[str, Any] = Field(default_factory=dict, description="Job-specific parameters")
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1-10, lower = higher priority)")
    dependencies: list[str] = Field(default_factory=list, description="List of job IDs this job depends on")


class SubmitChainRequest(BaseModel):
    """Request to submit a chain of jobs."""
    steps: list[dict[str, Any]] = Field(..., description="List of job steps, each with type, payload, and optional priority")


class JobResponse(BaseModel):
    """Job response model."""
    id: str
    session_id: str
    status: str
    job_type: str
    payload: dict[str, Any]
    result: Optional[dict[str, Any]]
    error_message: Optional[str]
    dependencies: list[str]
    parent_job_id: Optional[str]
    priority: int
    progress: float
    progress_message: str
    created_at: Optional[str]
    updated_at: Optional[str]
    expires_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response for job list."""
    jobs: list[JobResponse]
    total: int


class JobStatsResponse(BaseModel):
    """Job statistics response."""
    pending: int
    running: int
    paused: int
    completed: int
    failed: int
    cancelled: int
    total_active: int


class UpdatePriorityRequest(BaseModel):
    """Request to update job priority."""
    priority: int = Field(..., ge=1, le=10)


# ========== Helper Functions ==========

def get_session_id(request: Request) -> str:
    """Extract session ID from request."""
    # Try header first
    session_id = request.headers.get("X-Session-Id")
    if session_id:
        return session_id
    
    # Try to get from state (set by SessionMiddleware in cloud mode)
    if hasattr(request.state, "session_id"):
        return request.state.session_id
    
    # Fallback: generate from IP + user agent hash (not perfect but works for local)
    import hashlib
    client_info = f"{request.client.host}:{request.headers.get('user-agent', 'unknown')}"
    return hashlib.md5(client_info.encode()).hexdigest()[:16]


# ========== API Endpoints ==========

@router.post("/submit", response_model=JobResponse)
async def submit_job(request: Request, req: SubmitJobRequest) -> Job:
    """Submit a new job to the queue."""
    session_id = get_session_id(request)
    
    try:
        job_type = JobType(req.job_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid job type: {req.job_type}")
    
    job = queue_service.enqueue(
        session_id=session_id,
        job_type=job_type,
        payload=req.payload,
        priority=req.priority,
        dependencies=req.dependencies,
    )
    
    # Start execution if no dependencies
    if not req.dependencies:
        await job_runner.execute_job(job.id)
    
    return job


@router.post("/submit-chain", response_model=list[JobResponse])
async def submit_chain(request: Request, req: SubmitChainRequest) -> list[Job]:
    """Submit a chain of dependent jobs."""
    session_id = get_session_id(request)
    
    # Validate steps
    for i, step in enumerate(req.steps):
        if "type" not in step:
            raise HTTPException(status_code=400, detail=f"Step {i} missing 'type'")
        try:
            JobType(step["type"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Step {i} has invalid job type: {step['type']}")
    
    jobs = queue_service.enqueue_chain(session_id, req.steps)
    
    # Start first job
    if jobs:
        await job_runner.execute_job(jobs[0].id)
    
    return jobs


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    request: Request,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """List jobs for the current session."""
    session_id = get_session_id(request)
    
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Parse job type filter
    type_filter = None
    if job_type:
        try:
            type_filter = JobType(job_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid job type: {job_type}")
    
    jobs = queue_service.get_jobs_by_session(
        session_id=session_id,
        status=status_filter,
        job_type=type_filter,
        limit=limit,
        offset=offset,
    )
    
    return {
        "jobs": [job.to_dict() for job in jobs],
        "total": len(jobs),
    }


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(request: Request, job_id: str) -> Job:
    """Get details of a specific job."""
    session_id = get_session_id(request)
    
    job = queue_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Security check: only allow access to own session's jobs
    if job.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(request: Request, job_id: str) -> dict:
    """Cancel a pending or running job."""
    session_id = get_session_id(request)
    
    job = queue_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Cancel running job first
    if job.status == JobStatus.RUNNING:
        await job_runner.cancel_job(job_id)
    
    # Mark as cancelled
    if queue_service.mark_cancelled(job_id):
        return {"success": True, "message": "Job cancelled"}
    else:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")


@router.post("/jobs/{job_id}/pause")
async def pause_job(request: Request, job_id: str) -> dict:
    """Pause a running job."""
    session_id = get_session_id(request)
    
    job = queue_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if queue_service.pause_job(job_id):
        return {"success": True, "message": "Job paused"}
    else:
        raise HTTPException(status_code=400, detail="Job cannot be paused")


@router.post("/jobs/{job_id}/resume")
async def resume_job(request: Request, job_id: str) -> dict:
    """Resume a paused job."""
    session_id = get_session_id(request)
    
    job = queue_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if queue_service.resume_job(job_id):
        # Start execution
        await job_runner.execute_job(job_id)
        return {"success": True, "message": "Job resumed"}
    else:
        raise HTTPException(status_code=400, detail="Job cannot be resumed")


@router.post("/jobs/{job_id}/priority")
async def update_priority(
    request: Request,
    job_id: str,
    req: UpdatePriorityRequest,
) -> dict:
    """Update job priority."""
    session_id = get_session_id(request)
    
    job = queue_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if queue_service.update_priority(job_id, req.priority):
        return {"success": True, "priority": req.priority}
    else:
        raise HTTPException(status_code=400, detail="Cannot update priority")


@router.post("/reorder")
async def reorder_jobs(request: Request, job_ids: list[str]) -> dict:
    """Reorder jobs by priority (earlier in list = higher priority)."""
    session_id = get_session_id(request)
    
    # Verify all jobs belong to this session
    for job_id in job_ids:
        job = queue_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        if job.session_id != session_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if job.is_terminal():
            raise HTTPException(status_code=400, detail=f"Job {job_id} is already complete")
    
    # Update priorities (earlier = higher priority = lower number)
    for i, job_id in enumerate(job_ids):
        queue_service.update_priority(job_id, i + 1)
    
    return {"success": True, "message": f"Reordered {len(job_ids)} jobs"}


@router.get("/stats", response_model=JobStatsResponse)
async def get_stats(request: Request) -> dict:
    """Get job statistics for the current session."""
    session_id = get_session_id(request)
    return queue_service.get_stats(session_id)


@router.post("/clear-completed")
async def clear_completed(request: Request) -> dict:
    """Clear all completed, failed, and cancelled jobs."""
    session_id = get_session_id(request)
    count = queue_service.clear_completed(session_id)
    return {"success": True, "cleared": count}


@router.delete("/jobs/{job_id}")
async def delete_job(request: Request, job_id: str) -> dict:
    """Delete a job (only allowed for completed/failed/cancelled jobs)."""
    session_id = get_session_id(request)
    
    job = queue_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not job.is_terminal():
        raise HTTPException(status_code=400, detail="Cannot delete active jobs")
    
    # Mark as cancelled (effectively deletes it from active view)
    queue_service.mark_cancelled(job_id)
    return {"success": True, "message": "Job deleted"}


# ========== SSE Endpoints ==========

@router.get("/stream")
async def stream_updates(request: Request):
    """SSE endpoint for real-time job updates."""
    session_id = get_session_id(request)
    return create_sse_response(session_id)


# ========== User Management Endpoints ==========

@router.post("/user/register")
async def register_user(request: Request, name: Optional[str] = None, email: Optional[str] = None) -> dict:
    """Register a new user or get existing user for this session."""
    session_id = get_session_id(request)
    
    # Create or get user
    user = user_service.get_or_create_user(email=email, name=name)
    
    # Link session to user
    device_info = request.headers.get("User-Agent", "Unknown")
    user_service.link_session_to_user(session_id, user.id, device_info)
    
    return {
        "success": True,
        "user": user.to_dict(),
        "api_token": user.api_token,
    }


@router.get("/user/me")
async def get_current_user(request: Request) -> dict:
    """Get current user info."""
    session_id = get_session_id(request)
    
    user = user_service.get_user_for_session(session_id)
    if not user:
        raise HTTPException(status_code=404, detail="No user associated with this session")
    
    return {
        "user": user.to_dict(),
        "sessions": [s.to_dict() for s in user_service.get_user_sessions(user.id)],
    }


@router.post("/user/jobs")
async def get_user_jobs(
    request: Request,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Get all jobs for the current user across all sessions."""
    session_id = get_session_id(request)
    
    user = user_service.get_user_for_session(session_id)
    if not user:
        raise HTTPException(status_code=404, detail="No user associated with this session")
    
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    jobs = queue_service.get_jobs_by_user(
        user_id=user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    
    return {
        "jobs": [job.to_dict() for job in jobs],
        "total": len(jobs),
    }


# ========== Shared Session Endpoints ==========

@router.post("/share/create")
async def create_shared_session(request: Request, name: str = "Shared Queue") -> dict:
    """Create a new shared session."""
    session_id = get_session_id(request)
    
    user = user_service.get_user_for_session(session_id)
    if not user:
        raise HTTPException(status_code=400, detail="Must be logged in to create shared sessions")
    
    shared = user_service.create_shared_session(user.id, name)
    
    return {
        "success": True,
        "shared_session": shared.to_dict(),
        "share_token": shared.share_token,
    }


@router.post("/share/join/{share_token}")
async def join_shared_session(request: Request, share_token: str) -> dict:
    """Join a shared session using a share token."""
    session_id = get_session_id(request)
    
    user = user_service.get_user_for_session(session_id)
    if not user:
        raise HTTPException(status_code=400, detail="Must be logged in to join shared sessions")
    
    shared = user_service.join_shared_session(share_token, user.id)
    if not shared:
        raise HTTPException(status_code=404, detail="Invalid or expired share token")
    
    return {
        "success": True,
        "shared_session": shared.to_dict(),
    }


@router.get("/share/list")
async def list_shared_sessions(request: Request) -> dict:
    """List all shared sessions the user is a member of."""
    session_id = get_session_id(request)
    
    user = user_service.get_user_for_session(session_id)
    if not user:
        return {"shared_sessions": []}
    
    shared_sessions = user_service.get_shared_sessions_for_user(user.id)
    
    return {
        "shared_sessions": [s.to_dict() for s in shared_sessions],
    }