"""Voice library: upload, list, delete, and serve reference audio files."""

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse

from backend.config import settings
from backend.schemas.voice import VoiceProfile, VoiceUploadResponse, VoiceListResponse

router = APIRouter(prefix="/api/voices", tags=["voices"])

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".webm"}


def _convert_to_wav(src: Path, dest: Path) -> None:
    """Convert any audio file to 24kHz mono 16-bit PCM WAV using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-acodec", "pcm_s16le",
        "-ar", "24000",
        "-ac", "1",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Audio conversion failed: {result.stderr[:500]}")


def _library_path() -> Path:
    return settings.voices_dir / "library.json"


def _load_library() -> list[dict]:
    path = _library_path()
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _save_library(entries: list[dict]) -> None:
    path = _library_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2))


def resolve_voice_audio_path(ref_audio: str | None) -> str | None:
    """Resolve a voice library URL (e.g. /api/voices/audio/abc123) to a filesystem path.

    Returns the original string unchanged if it's not a voice library URL.
    """
    if not ref_audio:
        return ref_audio

    prefix = "/api/voices/audio/"
    if not ref_audio.startswith(prefix):
        return ref_audio

    voice_id = ref_audio[len(prefix):]
    library = _load_library()
    entry = next((e for e in library if e["id"] == voice_id), None)
    if not entry:
        return ref_audio

    audio_path = settings.voices_dir / entry["audio_filename"]
    return str(audio_path) if audio_path.exists() else ref_audio


@router.post("/upload", response_model=VoiceUploadResponse)
async def upload_voice(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    ref_text: str = Form(""),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    voice_id = uuid.uuid4().hex[:12]
    audio_filename = f"{voice_id}{ext}"
    dest = settings.voices_dir / audio_filename

    settings.voices_dir.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    dest.write_bytes(content)

    if ext != ".wav":
        wav_filename = f"{voice_id}.wav"
        wav_dest = settings.voices_dir / wav_filename
        try:
            _convert_to_wav(dest, wav_dest)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            dest.unlink(missing_ok=True)
            wav_dest.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail=str(exc))
        dest.unlink()
        audio_filename = wav_filename

    entry = VoiceProfile(
        id=voice_id,
        name=name,
        audio_filename=audio_filename,
        ref_text=ref_text,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    library = _load_library()
    library.append(entry.model_dump())
    _save_library(library)

    return VoiceUploadResponse(
        id=voice_id,
        name=name,
        audio_filename=audio_filename,
        audio_url=f"/api/voices/audio/{voice_id}",
    )


@router.get("", response_model=VoiceListResponse)
async def list_voices():
    entries = _load_library()
    return VoiceListResponse(voices=[VoiceProfile(**e) for e in entries])


@router.delete("/{voice_id}")
async def delete_voice(voice_id: str):
    if "/" in voice_id or "\\" in voice_id or ".." in voice_id:
        raise HTTPException(status_code=400, detail="Invalid voice ID")

    library = _load_library()
    entry = next((e for e in library if e["id"] == voice_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Voice not found")

    # Remove audio file
    audio_path = settings.voices_dir / entry["audio_filename"]
    if audio_path.exists():
        audio_path.unlink()

    library = [e for e in library if e["id"] != voice_id]
    _save_library(library)
    return {"status": "ok"}


@router.get("/audio/{voice_id}")
async def serve_voice_audio(voice_id: str):
    if "/" in voice_id or "\\" in voice_id or ".." in voice_id:
        raise HTTPException(status_code=400, detail="Invalid voice ID")

    library = _load_library()
    entry = next((e for e in library if e["id"] == voice_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Voice not found")

    audio_path = settings.voices_dir / entry["audio_filename"]
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = audio_path.suffix.lower()
    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
    }
    return FileResponse(audio_path, media_type=media_types.get(ext, "application/octet-stream"))
