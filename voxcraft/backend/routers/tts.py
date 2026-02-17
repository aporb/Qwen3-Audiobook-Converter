"""TTS generation endpoints."""

import asyncio
import uuid

import numpy as np
import soundfile as sf
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from backend.engine import (
    mlx_engine, mlx_lock, openai_lock,
    get_openai_engine,
    apply_text_cleaning, estimate_openai_cost, SAMPLE_RATE,
)
from backend.schemas.tts import (
    TTSRequest, TTSTaskResponse, CostEstimateRequest, CostEstimateResponse,
)
from backend.routers.voices import resolve_voice_audio_path
from backend.utils.sse import sse_manager

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.post("/generate", response_model=TTSTaskResponse)
async def generate(req: TTSRequest, request: Request):
    task_id = uuid.uuid4().hex[:12]
    api_key: str | None = request.headers.get("X-OpenAI-Key")
    audio_dir = request.state.audio_dir

    # Clean text
    text = apply_text_cleaning(
        req.text,
        fix_capitals=req.fix_capitals,
        remove_footnotes=req.remove_footnotes,
        normalize_chars=req.normalize_chars,
    )

    async def _run():
        try:
            progress_cb = sse_manager.make_progress_callback(task_id)

            if req.engine == "mlx":
                async with mlx_lock:
                    audio, sr = await asyncio.to_thread(
                        mlx_engine.generate_speech,
                        text=text,
                        voice_mode=req.voice_mode,
                        speaker=req.speaker,
                        language=req.language,
                        instruct=req.instruct,
                        ref_audio=resolve_voice_audio_path(req.ref_audio),
                        ref_text=req.ref_text,
                        voice_description=req.voice_description,
                        progress_callback=progress_cb,
                    )
            else:
                oai = get_openai_engine(api_key)
                async with openai_lock:
                    audio, sr = await asyncio.to_thread(
                        oai.generate_speech,
                        text=text,
                        voice=req.openai_voice,
                        model=req.openai_model,
                        instructions=req.openai_instructions,
                        progress_callback=progress_cb,
                    )

            # Save audio file
            file_id = uuid.uuid4().hex[:12]
            out_path = audio_dir / f"{file_id}.wav"
            sf.write(str(out_path), audio, sr)

            sse_manager.publish(task_id, "complete", {
                "audio_url": f"/api/audio/files/{file_id}",
                "duration": round(len(audio) / sr, 2),
                "sample_rate": sr,
            })
        except Exception as e:
            sse_manager.publish(task_id, "error", {"message": str(e)})

    asyncio.create_task(_run())
    return TTSTaskResponse(task_id=task_id)


@router.get("/stream/{task_id}")
async def stream(task_id: str):
    return EventSourceResponse(sse_manager.subscribe(task_id), ping=15)


@router.post("/estimate-cost", response_model=CostEstimateResponse)
async def cost_estimate(req: CostEstimateRequest):
    result = estimate_openai_cost(req.text, req.model)
    return CostEstimateResponse(**result)
