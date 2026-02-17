"""Server-Sent Events manager for progress streaming."""

import asyncio
import json
from collections import defaultdict
from typing import Any


class SSEManager:
    """Publish / subscribe hub for SSE progress events."""

    def __init__(self):
        self._channels: dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue())

    def publish(self, task_id: str, event: str, data: dict[str, Any]):
        """Push an event onto the task's channel (non-blocking)."""
        msg = {"event": event, "data": json.dumps(data)}
        q = self._channels[task_id]
        q.put_nowait(msg)

    async def subscribe(self, task_id: str):
        """Async generator that yields dicts for sse_starlette to encode."""
        q = self._channels[task_id]
        while True:
            msg = await q.get()
            yield msg
            if msg["event"] in ("complete", "error"):
                break
        # Clean up after stream ends
        self._channels.pop(task_id, None)

    def make_progress_callback(self, task_id: str):
        """Return a sync callback(fraction, message) that publishes SSE events."""
        def callback(fraction: float, message: str):
            self.publish(task_id, "progress", {
                "fraction": round(fraction, 4),
                "message": message,
            })
        return callback


sse_manager = SSEManager()
