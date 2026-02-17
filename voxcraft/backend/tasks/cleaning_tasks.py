"""Text cleaning task handlers."""

from __future__ import annotations

import logging

from backend.models.queue import Job, JobType
from backend.services.queue_service import queue_service
from backend.utils.job_runner import register_task_handler

logger = logging.getLogger(__name__)


@register_task_handler(JobType.CLEANING)
async def handle_cleaning_job(job: Job) -> dict:
    """Handle text cleaning job."""
    payload = job.payload
    text = payload.get("text", "")
    cleaning_mode = payload.get("mode", "standard")
    
    if not text:
        raise ValueError("No text provided for cleaning")
    
    queue_service.update_progress(job.id, 0.1, "Analyzing text...")
    
    # Simulate cleaning process
    # In real implementation, this would call the cleaning service
    queue_service.update_progress(job.id, 0.5, "Cleaning text...")
    
    # Simple cleaning for now
    cleaned_text = text.strip()
    
    queue_service.update_progress(job.id, 1.0, "Text cleaning complete")
    
    return {
        "original_length": len(text),
        "cleaned_length": len(cleaned_text),
        "cleaned_text": cleaned_text,
        "mode": cleaning_mode,
    }