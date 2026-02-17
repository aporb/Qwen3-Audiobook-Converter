from pydantic import BaseModel


class ConvertRequest(BaseModel):
    book_id: str
    engine: str = "mlx"

    # MLX options
    voice_mode: str = "custom_voice"
    speaker: str = "Ryan"
    language: str = "english"
    instruct: str | None = None
    ref_audio: str | None = None
    ref_text: str | None = None
    voice_description: str | None = None

    # OpenAI options
    openai_voice: str = "coral"
    openai_model: str = "gpt-4o-mini-tts"
    openai_instructions: str | None = None

    # Chapters to include (empty = all)
    chapter_ids: list[str] = []

    # Text cleaning
    fix_capitals: bool = True
    remove_footnotes: bool = True
    normalize_chars: bool = True

    # AI cleaning
    ai_cleaning_enabled: bool = False
    cleaning_backend: str = "openai"
    cleaning_preset: str = "ocr_cleanup"
    cleaning_custom_prompt: str | None = None
    cleaning_custom_base_url: str | None = None
    cleaning_custom_model: str | None = None
    cleaning_custom_api_key: str | None = None


class ConvertResponse(BaseModel):
    task_id: str
