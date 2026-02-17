"""Session middleware for cloud mode — per-user file isolation."""

import re
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.config import settings


class SessionMiddleware(BaseHTTPMiddleware):
    """Reads X-Session-Id header and scopes file storage per session in cloud mode."""

    _VALID_SESSION = re.compile(r"^[a-zA-Z0-9\-]{12,36}$")

    async def dispatch(self, request: Request, call_next):
        session_id = request.headers.get("X-Session-Id", "")

        if settings.deployment_mode == "cloud" and session_id and self._VALID_SESSION.match(session_id):
            # Create session-scoped directories
            upload_dir = settings.uploads_dir / session_id
            audio_dir = settings.audio_dir / session_id
            upload_dir.mkdir(parents=True, exist_ok=True)
            audio_dir.mkdir(parents=True, exist_ok=True)

            request.state.session_id = session_id
            request.state.uploads_dir = upload_dir
            request.state.audio_dir = audio_dir
        else:
            # Local mode or no session — use shared directories
            request.state.session_id = None
            request.state.uploads_dir = settings.uploads_dir
            request.state.audio_dir = settings.audio_dir

        return await call_next(request)
