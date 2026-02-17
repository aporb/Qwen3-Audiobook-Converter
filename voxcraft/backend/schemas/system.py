from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class DeviceInfo(BaseModel):
    device: str
    memory_available_gb: float
    memory_total_gb: float
    accelerator: str | None


class EngineStatus(BaseModel):
    mlx_loaded: bool
    mlx_model_id: str | None
    openai_available: bool


class ModeResponse(BaseModel):
    mode: str
    mlx_available: bool
    license_required: bool


class ValidateKeyResponse(BaseModel):
    valid: bool
    error: str | None = None


class ModelCacheStatus(BaseModel):
    cached: bool
    model_id: str
    size_gb: float


class PreloadRequest(BaseModel):
    voice_mode: str = "custom_voice"
