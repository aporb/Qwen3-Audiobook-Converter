"""Export endpoints — format conversion and subtitle generation."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from backend.schemas.export import (
    ConvertFormatRequest, ConvertFormatResponse,
    SubtitleRequest, SubtitleResponse,
)
from backend.services.export_service import (
    convert_audio_format, generate_srt, generate_vtt,
)

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/convert-format", response_model=ConvertFormatResponse)
async def convert_format(req: ConvertFormatRequest, request: Request):
    source = request.state.audio_dir / f"{req.file_id}.wav"
    if not source.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    if req.output_format not in ("mp3", "m4b", "wav"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {req.output_format}")

    if req.output_format == "wav":
        return ConvertFormatResponse(
            download_url=f"/api/export/download/{req.file_id}.wav",
            format="wav",
        )

    try:
        convert_audio_format(str(source), req.output_format)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {e}")

    filename = f"{req.file_id}.{req.output_format}"
    return ConvertFormatResponse(
        download_url=f"/api/export/download/{filename}",
        format=req.output_format,
    )


@router.post("/subtitles", response_model=SubtitleResponse)
async def create_subtitles(req: SubtitleRequest, request: Request):
    if req.format not in ("srt", "vtt"):
        raise HTTPException(status_code=400, detail=f"Unsupported subtitle format: {req.format}")

    output_path = str(request.state.audio_dir / f"{req.file_id}.{req.format}")

    try:
        if req.format == "srt":
            generate_srt(req.text, req.duration_seconds, output_path)
        else:
            generate_vtt(req.text, req.duration_seconds, output_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subtitle generation failed: {e}")

    filename = f"{req.file_id}.{req.format}"
    return SubtitleResponse(
        download_url=f"/api/export/download/{filename}",
        format=req.format,
    )


@router.get("/download/{file_name}")
async def download(file_name: str, request: Request):
    file_path = request.state.audio_dir / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Map extensions to MIME types
    mime_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4b": "audio/mp4",
        ".srt": "text/plain",
        ".vtt": "text/vtt",
    }
    ext = Path(file_name).suffix.lower()
    media_type = mime_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_name,
    )
