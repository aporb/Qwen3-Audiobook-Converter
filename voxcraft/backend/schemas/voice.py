"""Voice library schemas."""

from pydantic import BaseModel


class VoiceProfile(BaseModel):
    id: str
    name: str
    audio_filename: str  # filename in voices dir
    ref_text: str = ""  # transcript of reference audio
    created_at: str  # ISO 8601


class VoiceUploadResponse(BaseModel):
    id: str
    name: str
    audio_filename: str
    audio_url: str  # /api/voices/audio/{id}


class VoiceListResponse(BaseModel):
    voices: list[VoiceProfile]
