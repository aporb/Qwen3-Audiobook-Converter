"""Audio file serving endpoint."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/audio", tags=["audio"])


@router.get("/files/{file_id}")
async def serve_audio(file_id: str, request: Request):
    # Sanitize file_id to prevent path traversal
    if "/" in file_id or "\\" in file_id or ".." in file_id:
        raise HTTPException(status_code=400, detail="Invalid file ID")

    path = request.state.audio_dir / f"{file_id}.wav"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(path, media_type="audio/wav")
