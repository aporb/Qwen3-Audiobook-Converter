"""Job runner for executing queued tasks with dependency resolution."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Callable, Optional

from backend.models.queue import Job, JobStatus, JobType
from backend.services.queue_service import queue_service

logger = logging.getLogger(__name__)

# Registry of task handlers
_task_handlers: dict[JobType, Callable[[Job], Any]] = {}


def register_task_handler(job_type: JobType):
    """Decorator to register a task handler."""
    def decorator(func: Callable[[Job], Any]):
        _task_handlers[job_type] = func
        return func
    return decorator


def get_task_handler(job_type: JobType) -> Optional[Callable[[Job], Any]]:
    """Get the handler for a job type."""
    return _task_handlers.get(job_type)


class JobRunner:
    """Runner for executing jobs with dependency resolution."""

    def __init__(self) -> None:
        """Initialize the job runner."""
        self._running = False
        self._current_jobs: dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        """Start the job runner loop."""
        self._running = True
        logger.info("Job runner started")

        while self._running:
            try:
                await self._process_pending_jobs()
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                logger.error(f"Error in job runner loop: {e}")
                await asyncio.sleep(5)

    def stop(self) -> None:
        """Stop the job runner."""
        self._running = False
        logger.info("Job runner stopping...")

    async def _process_pending_jobs(self) -> None:
        """Process pending jobs that have satisfied dependencies."""
        # Get all sessions with pending jobs
        # Note: In a real implementation, you'd want to track sessions more efficiently
        # For now, we'll process jobs as they come in via explicit execution
        pass

    async def execute_job(self, job_id: str) -> None:
        """Execute a specific job."""
        job = queue_service.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        if not job.can_run():
            logger.warning(f"Job {job_id} cannot run (status: {job.status.value})")
            return

        # Check dependencies
        if job.dependencies:
            deps_satisfied = await self._check_dependencies(job.dependencies)
            if not deps_satisfied:
                logger.info(f"Job {job_id} waiting for dependencies")
                return

        # Mark as running
        if not queue_service.mark_running(job_id):
            logger.error(f"Failed to mark job {job_id} as running")
            return

        # Get the handler
        handler = get_task_handler(job.job_type)
        if not handler:
            queue_service.mark_failed(job_id, f"No handler for job type: {job.job_type.value}")
            return

        # Resolve payload templates (e.g., {{job_id.result}})
        try:
            resolved_payload = await self._resolve_payload(job)
        except Exception as e:
            queue_service.mark_failed(job_id, f"Failed to resolve payload: {str(e)}")
            return

        # Execute the job
        task = asyncio.create_task(self._run_job_wrapper(job_id, handler, resolved_payload))
        self._current_jobs[job_id] = task

        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            queue_service.mark_cancelled(job_id)
        except Exception as e:
            logger.exception(f"Job {job_id} failed with exception")
            queue_service.mark_failed(job_id, str(e))
        finally:
            self._current_jobs.pop(job_id, None)

    async def _run_job_wrapper(
        self,
        job_id: str,
        handler: Callable[[Job], Any],
        payload: dict[str, Any],
    ) -> None:
        """Wrapper to run a job with progress tracking."""
        job = queue_service.get_job(job_id)
        if not job:
            return

        # Update payload with resolved values
        job.payload = payload

        try:
            result = await handler(job)
            queue_service.mark_completed(job_id, result)
        except Exception as e:
            logger.exception(f"Job handler failed for {job_id}")
            queue_service.mark_failed(job_id, str(e))

    async def _check_dependencies(self, dependency_ids: list[str]) -> bool:
        """Check if all dependencies are satisfied (completed successfully)."""
        for dep_id in dependency_ids:
            dep_job = queue_service.get_job(dep_id)
            if not dep_job:
                logger.error(f"Dependency {dep_id} not found")
                return False
            if dep_job.status != JobStatus.COMPLETED:
                return False
        return True

    async def _resolve_payload(self, job: Job) -> dict[str, Any]:
        """Resolve payload templates like {{job_id.result.field}}."""
        payload = dict(job.payload)
        
        # Find all template patterns: {{job_id.result}} or {{job_id.result.field}}
        template_pattern = r'\{\{(\w+)\.result(?:\.(\w+))?\}\}'
        
        def resolve_value(match: re.Match) -> str:
            dep_id = match.group(1)
            field = match.group(2)
            
            dep_job = queue_service.get_job(dep_id)
            if not dep_job or dep_job.status != JobStatus.COMPLETED:
                raise ValueError(f"Dependency {dep_id} not completed")
            
            result = dep_job.result or {}
            if field:
                return str(result.get(field, ""))
            return str(result.get("output", result))
        
        # Resolve templates in string values
        for key, value in payload.items():
            if isinstance(value, str):
                payload[key] = re.sub(template_pattern, resolve_value, value)
            elif isinstance(value, dict):
                payload[key] = await self._resolve_nested_dict(value)
            elif isinstance(value, list):
                payload[key] = await self._resolve_nested_list(value)
        
        return payload

    async def _resolve_nested_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Resolve templates in nested dictionaries."""
        result = {}
        template_pattern = r'\{\{(\w+)\.result(?:\.(\w+))?\}\}'
        
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = re.sub(template_pattern, self._resolve_template, value)
            elif isinstance(value, dict):
                result[key] = await self._resolve_nested_dict(value)
            elif isinstance(value, list):
                result[key] = await self._resolve_nested_list(value)
            else:
                result[key] = value
        return result

    async def _resolve_nested_list(self, data: list[Any]) -> list[Any]:
        """Resolve templates in nested lists."""
        result = []
        template_pattern = r'\{\{(\w+)\.result(?:\.(\w+))?\}\}'
        
        for item in data:
            if isinstance(item, str):
                result.append(re.sub(template_pattern, self._resolve_template, item))
            elif isinstance(item, dict):
                result.append(await self._resolve_nested_dict(item))
            elif isinstance(item, list):
                result.append(await self._resolve_nested_list(item))
            else:
                result.append(item)
        return result

    def _resolve_template(self, match: re.Match) -> str:
        """Helper to resolve a single template match."""
        dep_id = match.group(1)
        field = match.group(2)
        
        dep_job = queue_service.get_job(dep_id)
        if not dep_job or dep_job.status != JobStatus.COMPLETED:
            raise ValueError(f"Dependency {dep_id} not completed")
        
        result = dep_job.result or {}
        if field:
            return str(result.get(field, ""))
        return str(result.get("output", result))

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        task = self._current_jobs.get(job_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False


# Global job runner instance
job_runner = JobRunner()


async def start_job_runner() -> None:
    """Start the global job runner."""
    await job_runner.start()


def stop_job_runner() -> None:
    """Stop the global job runner."""
    job_runner.stop()