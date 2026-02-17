from pydantic import BaseModel


class TTSRequest(BaseModel):
    text: str
    engine: str = "mlx"  # "mlx" or "openai"

    # MLX options
    voice_mode: str = "custom_voice"
    speaker: str = "Ryan"
    language: str = "english"
    instruct: str | None = None
    ref_audio: str | None = None  # path to reference audio
    ref_text: str | None = None
    voice_description: str | None = None

    # OpenAI options
    openai_voice: str = "coral"
    openai_model: str = "gpt-4o-mini-tts"
    openai_instructions: str | None = None

    # Text cleaning
    fix_capitals: bool = True
    remove_footnotes: bool = True
    normalize_chars: bool = True


class TTSTaskResponse(BaseModel):
    task_id: str


class CostEstimateRequest(BaseModel):
    text: str
    model: str = "gpt-4o-mini-tts"


class CostEstimateResponse(BaseModel):
    characters: int
    model: str
    price_per_million_chars: float
    estimated_cost_usd: float
    estimated_duration_min: float
