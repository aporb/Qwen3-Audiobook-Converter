"""VoxCraft FastAPI application."""

import asyncio
import shutil
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.middleware.session import SessionMiddleware
from backend.routers import system, tts, books, audiobook, casting, audio, export, license, cleaning, voices, url_reader


async def _cleanup_expired_sessions():
    """Periodically remove session directories older than the configured TTL."""
    while True:
        await asyncio.sleep(3600)  # Check every hour
        if settings.deployment_mode != "cloud":
            continue
        cutoff = time.time() - settings.session_ttl_hours * 3600
        for base in (settings.uploads_dir, settings.audio_dir):
            if not base.exists():
                continue
            for child in base.iterdir():
                if child.is_dir() and child.stat().st_mtime < cutoff:
                    shutil.rmtree(child, ignore_errors=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    cleanup_task = asyncio.create_task(_cleanup_expired_sessions())
    yield
    cleanup_task.cancel()


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(tts.router)
app.include_router(books.router)
app.include_router(audiobook.router)
app.include_router(casting.router)
app.include_router(audio.router)
app.include_router(export.router)
app.include_router(license.router)
app.include_router(cleaning.router)
app.include_router(voices.router)
app.include_router(url_reader.router)

# In cloud mode, serve the built frontend as static files.
# html=True enables SPA fallback (returns index.html for unmatched routes).
_static_dir = Path(__file__).resolve().parent.parent / "static"
if settings.deployment_mode == "cloud" and _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
