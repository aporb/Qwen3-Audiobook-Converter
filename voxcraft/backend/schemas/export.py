from pydantic import BaseModel


class ConvertFormatRequest(BaseModel):
    file_id: str
    output_format: str = "mp3"  # mp3, m4b


class ConvertFormatResponse(BaseModel):
    download_url: str
    format: str


class SubtitleRequest(BaseModel):
    file_id: str
    text: str
    duration_seconds: float
    format: str = "srt"  # srt, vtt


class SubtitleResponse(BaseModel):
    download_url: str
    format: str
