from pydantic import BaseModel


class AICleanRequest(BaseModel):
    text: str
    backend: str = "openai"  # "openai" or "custom"
    preset: str = "ocr_cleanup"  # "ocr_cleanup", "tts_optimization", "light_touch", "custom"
    custom_prompt: str | None = None
    custom_base_url: str | None = None
    custom_model: str | None = None
    custom_api_key: str | None = None
    chunk_size: int = 1500


class AICleanResponse(BaseModel):
    task_id: str


class CleanPreviewRequest(BaseModel):
    text: str
    backend: str = "openai"
    preset: str = "ocr_cleanup"
    custom_prompt: str | None = None
    custom_base_url: str | None = None
    custom_model: str | None = None
    custom_api_key: str | None = None


class CleanPreviewResponse(BaseModel):
    original: str
    cleaned: str
