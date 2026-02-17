"""Server-Sent Events manager for job queue updates."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, Callable

from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)


class QueueSSEManager:
    """Manages SSE streams for job queue updates."""
    
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._global_subscribers: list[asyncio.Queue] = []
    
    def subscribe(self, session_id: str) -> asyncio.Queue:
        """Subscribe to updates for a specific session."""
        queue = asyncio.Queue()
        if session_id not in self._subscribers:
            self._subscribers[session_id] = []
        self._subscribers[session_id].append(queue)
        logger.debug(f"New subscriber for session {session_id[:8]}...")
        return queue
    
    def subscribe_global(self) -> asyncio.Queue:
        """Subscribe to all updates (for admin/monitoring)."""
        queue = asyncio.Queue()
        self._global_subscribers.append(queue)
        logger.debug("New global subscriber")
        return queue
    
    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from updates."""
        if session_id in self._subscribers:
            try:
                self._subscribers[session_id].remove(queue)
                if not self._subscribers[session_id]:
                    del self._subscribers[session_id]
            except ValueError:
                pass
    
    def unsubscribe_global(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from global updates."""
        try:
            self._global_subscribers.remove(queue)
        except ValueError:
            pass
    
    async def publish(self, session_id: str, event_type: str, data: dict) -> None:
        """Publish an event to subscribers."""
        message = {
            "event": event_type,
            "data": data,
            "session_id": session_id,
        }
        
        # Send to session subscribers
        if session_id in self._subscribers:
            dead_queues = []
            for queue in self._subscribers[session_id]:
                try:
                    await queue.put(message)
                except Exception:
                    dead_queues.append(queue)
            
            # Clean up dead queues
            for queue in dead_queues:
                self.unsubscribe(session_id, queue)
        
        # Send to global subscribers
        dead_globals = []
        for queue in self._global_subscribers:
            try:
                await queue.put(message)
            except Exception:
                dead_globals.append(queue)
        
        for queue in dead_globals:
            self.unsubscribe_global(queue)
    
    async def publish_job_update(self, session_id: str, job: dict) -> None:
        """Publish a job update event."""
        await self.publish(session_id, "job_update", job)
    
    async def publish_job_created(self, session_id: str, job: dict) -> None:
        """Publish a job created event."""
        await self.publish(session_id, "job_created", job)
    
    async def publish_job_completed(self, session_id: str, job: dict) -> None:
        """Publish a job completed event."""
        await self.publish(session_id, "job_completed", job)
    
    async def publish_job_failed(self, session_id: str, job_id: str, error: str) -> None:
        """Publish a job failed event."""
        await self.publish(session_id, "job_failed", {"job_id": job_id, "error": error})
    
    async def publish_stats_update(self, session_id: str, stats: dict) -> None:
        """Publish a stats update event."""
        await self.publish(session_id, "stats_update", stats)


# Global SSE manager instance
queue_sse_manager = QueueSSEManager()


async def event_generator(
    queue: asyncio.Queue,
    session_id: str,
    unsubscribe_fn: Callable,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from queue."""
    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield json.dumps(message)
            except asyncio.TimeoutError:
                # Send keepalive
                yield json.dumps({"event": "ping", "data": {}})
    except asyncio.CancelledError:
        logger.debug(f"SSE stream cancelled for session {session_id[:8]}...")
        raise
    finally:
        unsubscribe_fn()


def create_sse_response(session_id: str) -> EventSourceResponse:
    """Create an SSE response for a session."""
    queue = queue_sse_manager.subscribe(session_id)
    
    async def generator():
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield json.dumps(message)
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ":keepalive\n\n"
        except asyncio.CancelledError:
            logger.debug(f"SSE stream cancelled for session {session_id[:8]}...")
            raise
        finally:
            queue_sse_manager.unsubscribe(session_id, queue)
    
    return EventSourceResponse(generator(), ping=15)