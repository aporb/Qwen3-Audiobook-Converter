"""URL Reader router - fetch web content and convert to speech."""

from __future__ import annotations

import asyncio
import uuid

import soundfile as sf
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from backend.engine import (
    apply_text_cleaning,
    get_openai_engine,
    mlx_engine,
    mlx_lock,
    openai_lock,
)
from backend.routers.voices import resolve_voice_audio_path
from backend.schemas.url_reader import (
    ProcessingMode,
    URLConvertRequest,
    URLConvertResponse,
    URLFetchRequest,
    URLFetchResponse,
    URLSummaryRequest,
    URLSummaryResponse,
)
from backend.services.url_service import content_processor, url_fetcher
from backend.utils.sse import sse_manager

router = APIRouter(prefix="/api/url-reader", tags=["url-reader"])


@router.post("/fetch", response_model=URLFetchResponse)
async def fetch_url(request: URLFetchRequest):
    """Fetch and extract readable content from URL."""
    try:
        content = await url_fetcher.fetch(str(request.url))
        return URLFetchResponse(
            title=content.title,
            content=content.content,
            author=content.author,
            published_date=content.published_date,
            word_count=content.word_count,
            estimated_duration_min=round(content.estimate_duration(), 2),
            url=content.url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL: {e}") from e


@router.post("/summarize", response_model=URLSummaryResponse)
async def summarize_content(request: URLSummaryRequest):
    """Generate summary and insights from provided content."""
    try:
        result = content_processor.summarize_with_insights(
            title=request.title or "Article",
            text=request.content,
        )
        return URLSummaryResponse(
            summary=result.summary,
            insights=result.insights,
            takeaways=result.takeaways,
            formatted_text=result.formatted_text,
            word_count=len(result.formatted_text.split()),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize content: {e}") from e


@router.post("/convert", response_model=URLConvertResponse)
async def convert_url(req: URLConvertRequest, request: Request):
    """Start URL-to-audio conversion task."""
    task_id = uuid.uuid4().hex[:12]
    audio_dir = request.state.audio_dir
    api_key = req.openai_api_key or request.headers.get("X-OpenAI-Key")

    async def _run():
        try:
            progress_cb = sse_manager.make_progress_callback(task_id)
            progress_cb(0.02, "Fetching web content...")

            fetched = await url_fetcher.fetch(str(req.url))

            if req.content and req.content.strip():
                text = req.content.strip()
            elif req.mode == ProcessingMode.SUMMARY_INSIGHTS:
                progress_cb(0.12, "Creating summary and insights...")
                summary = content_processor.summarize_with_insights(
                    title=fetched.title,
                    text=fetched.content,
                )
                text = summary.formatted_text
            else:
                text = content_processor.create_full_reading(fetched)

            text = content_processor.format_for_audio(text)
            text = apply_text_cleaning(
                text,
                fix_capitals=req.fix_capitals,
                remove_footnotes=req.remove_footnotes,
                normalize_chars=req.normalize_chars,
            )

            if not text.strip():
                raise RuntimeError("No text available for conversion after extraction/cleaning")

            if req.engine == "mlx":
                progress_cb(0.22, "Generating audio with MLX...")
                async with mlx_lock:
                    audio, sr = await asyncio.to_thread(
                        mlx_engine.generate_speech,
                        text=text,
                        voice_mode=req.voice_mode,
                        speaker=req.voice,
                        language=(req.language or "english").lower(),
                        instruct=req.instruct,
                        ref_audio=resolve_voice_audio_path(req.ref_audio),
                        ref_text=req.ref_text,
                        voice_description=req.voice_description,
                        progress_callback=progress_cb,
                    )
            else:
                progress_cb(0.22, "Generating audio with OpenAI...")
                oai = get_openai_engine(api_key)
                async with openai_lock:
                    audio, sr = await asyncio.to_thread(
                        oai.generate_speech,
                        text=text,
                        voice=req.openai_voice,
                        model=req.openai_model,
                        instructions=req.instructions,
                        progress_callback=progress_cb,
                    )

            out_path = audio_dir / f"{task_id}.wav"
            sf.write(str(out_path), audio, sr)

            sse_manager.publish(
                task_id,
                "complete",
                {
                    "audio_url": f"/api/audio/files/{task_id}",
                    "duration": round(len(audio) / sr, 2),
                    "sample_rate": sr,
                },
            )
        except Exception as e:
            sse_manager.publish(task_id, "error", {"message": str(e)})

    asyncio.create_task(_run())
    return URLConvertResponse(task_id=task_id)


@router.get("/stream/{task_id}")
async def stream(task_id: str):
    """SSE stream for URL conversion progress."""
    return EventSourceResponse(sse_manager.subscribe(task_id), ping=15)
