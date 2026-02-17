"""TTS task handlers."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from backend.engine import get_openai_engine, mlx_engine, openai_lock, mlx_lock
from backend.models.queue import Job, JobType
from backend.services.queue_service import queue_service
from backend.utils.job_runner import register_task_handler

logger = logging.getLogger(__name__)


@register_task_handler(JobType.TTS)
async def handle_tts_job(job: Job) -> dict:
    """Handle TTS generation job."""
    payload = job.payload
    
    # Extract parameters
    text = payload.get("text", "")
    engine = payload.get("engine", "openai")
    voice = payload.get("voice", "alloy")
    voice_mode = payload.get("voice_mode", "default")
    instructions = payload.get("instructions", "")
    openai_api_key = payload.get("openai_api_key")
    
    if not text:
        raise ValueError("No text provided for TTS")
    
    # Generate output path
    output_dir = Path("data/audio")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{job.id}.wav"
    
    try:
        if engine == "openai":
            result = await _generate_openai_tts(
                text=text,
                voice=voice,
                instructions=instructions,
                output_path=output_path,
                openai_api_key=openai_api_key,
                job_id=job.id,
            )
        elif engine == "mlx":
            result = await _generate_mlx_tts(
                text=text,
                voice=voice,
                voice_mode=voice_mode,
                output_path=output_path,
                job_id=job.id,
            )
        else:
            raise ValueError(f"Unknown engine: {engine}")
        
        return {
            "output_path": str(result),
            "audio_url": f"/api/audio/files/{job.id}.wav",
            "engine": engine,
        }
    except Exception as e:
        # Clean up partial file
        if output_path.exists():
            output_path.unlink()
        raise


async def _generate_openai_tts(
    text: str,
    voice: str,
    instructions: str,
    output_path: Path,
    openai_api_key: str | None,
    job_id: str,
) -> Path:
    """Generate TTS using OpenAI."""
    async with openai_lock:
        engine = get_openai_engine(api_key=openai_api_key)
        
        # Update progress
        queue_service.update_progress(job_id, 0.1, "Generating audio with OpenAI...")
        
        # Generate speech
        response = await engine.audio.speech.create(
            model="tts-1-hd" if not instructions else "gpt-4o-mini-tts",
            voice=voice,
            input=text,
            instructions=instructions if instructions else None,
        )
        
        # Save to file
        response.stream_to_file(str(output_path))
        
        queue_service.update_progress(job_id, 1.0, "Audio generated successfully")
        
    return output_path


async def _generate_mlx_tts(
    text: str,
    voice: str,
    voice_mode: str,
    output_path: Path,
    job_id: str,
) -> Path:
    """Generate TTS using MLX."""
    async with mlx_lock:
        if not mlx_engine.is_loaded:
            queue_service.update_progress(job_id, 0.05, "Loading MLX model...")
            mlx_engine.load_model()
        
        queue_service.update_progress(job_id, 0.1, "Generating audio with MLX...")
        
        # Generate speech
        mlx_engine.generate_speech(
            text=text,
            speaker=voice,
            output_path=str(output_path),
        )
        
        queue_service.update_progress(job_id, 1.0, "Audio generated successfully")
        
    return output_path