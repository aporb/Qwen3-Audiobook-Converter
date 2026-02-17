"""URL Reader schemas."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class ProcessingMode(str, Enum):
    """Content processing modes."""

    FULL_ARTICLE = "full_article"
    SUMMARY_INSIGHTS = "summary_insights"


class URLFetchRequest(BaseModel):
    """Request to fetch content from a URL."""

    url: HttpUrl = Field(..., description="URL to fetch")


class URLFetchResponse(BaseModel):
    """Response with fetched content."""

    title: str
    content: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    word_count: int
    estimated_duration_min: float
    url: str


class URLConvertRequest(BaseModel):
    """Request to convert URL content to audio."""

    url: HttpUrl
    mode: ProcessingMode = ProcessingMode.FULL_ARTICLE
    content: Optional[str] = Field(
        None,
        description="Optional edited content overriding fetched content",
    )

    # Engine
    engine: Literal["mlx", "openai"] = "mlx"

    # MLX options
    voice_mode: Literal["custom_voice", "voice_clone", "voice_design"] = "custom_voice"
    voice: str = "Ryan"  # speaker name for custom_voice
    language: str = "english"
    instruct: Optional[str] = None
    ref_audio: Optional[str] = None
    ref_text: Optional[str] = None
    voice_description: Optional[str] = None

    # OpenAI options
    openai_model: str = "gpt-4o-mini-tts"
    openai_voice: str = "coral"
    instructions: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Text cleaning
    fix_capitals: bool = True
    remove_footnotes: bool = True
    normalize_chars: bool = True


class URLConvertResponse(BaseModel):
    """Response with conversion task info."""

    task_id: str


class URLSummaryRequest(BaseModel):
    """Request to generate summary+insights preview."""

    title: Optional[str] = None
    content: str


class URLSummaryResponse(BaseModel):
    """Response with generated summary."""

    summary: str
    insights: list[str]
    takeaways: str
    formatted_text: str
    word_count: int
