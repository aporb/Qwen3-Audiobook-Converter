"""URL fetch and summarize task handlers."""

from __future__ import annotations

import logging

from backend.models.queue import Job, JobType
from backend.services.url_service import url_fetcher, content_processor
from backend.services.queue_service import queue_service
from backend.utils.job_runner import register_task_handler

logger = logging.getLogger(__name__)


@register_task_handler(JobType.URL_FETCH)
async def handle_url_fetch_job(job: Job) -> dict:
    """Handle URL content fetching job."""
    payload = job.payload
    url = payload.get("url", "")
    
    if not url:
        raise ValueError("No URL provided")
    
    queue_service.update_progress(job.id, 0.1, "Fetching URL content...")
    
    # Fetch content
    content = await url_fetcher.fetch(url)
    
    queue_service.update_progress(job.id, 1.0, "Content fetched successfully")
    
    return {
        "title": content.title,
        "content": content.content,
        "author": content.author,
        "published_date": content.published_date,
        "word_count": content.word_count,
        "url": content.url,
    }


@register_task_handler(JobType.SUMMARIZE)
async def handle_summarize_job(job: Job) -> dict:
    """Handle content summarization job."""
    payload = job.payload
    title = payload.get("title", "Untitled")
    text = payload.get("text", "")
    
    if not text:
        raise ValueError("No text provided for summarization")
    
    queue_service.update_progress(job.id, 0.1, "Generating summary and insights...")
    
    # Generate summary
    result = content_processor.summarize_with_insights(title, text)
    
    queue_service.update_progress(job.id, 1.0, "Summary generated successfully")
    
    return {
        "summary": result.summary,
        "insights": result.insights,
        "takeaways": result.takeaways,
        "formatted_text": result.formatted_text,
    }