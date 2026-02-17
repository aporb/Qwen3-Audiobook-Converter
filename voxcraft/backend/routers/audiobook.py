"""Audiobook conversion endpoints."""

import asyncio
import os
import tempfile
import uuid

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from backend.engine import (
    mlx_engine, mlx_lock, openai_lock,
    get_openai_engine,
    apply_text_cleaning, extract_text_from_file,
)
from backend.schemas.audiobook import ConvertRequest, ConvertResponse
from backend.routers.books import get_book_path
from backend.routers.casting import get_assignments
from backend.routers.voices import resolve_voice_audio_path
from backend.services.chapter_service import extract_chapter_text
from backend.utils.sse import sse_manager

router = APIRouter(prefix="/api/audiobook", tags=["audiobook"])


@router.post("/convert", response_model=ConvertResponse)
async def convert(req: ConvertRequest, request: Request):
    task_id = uuid.uuid4().hex[:12]
    book_path = get_book_path(req.book_id)
    audio_dir = request.state.audio_dir
    output_path = str(audio_dir / f"{task_id}.wav")
    api_key: str | None = request.headers.get("X-OpenAI-Key")

    async def _run():
        source_path = book_path
        tmp_file = None
        try:
            progress_cb = sse_manager.make_progress_callback(task_id)

            # If specific chapters selected, extract only those to a temp file
            if req.chapter_ids:
                text = extract_chapter_text(book_path, req.chapter_ids)
                text = apply_text_cleaning(
                    text,
                    fix_capitals=req.fix_capitals,
                    remove_footnotes=req.remove_footnotes,
                    normalize_chars=req.normalize_chars,
                )

                # AI cleaning (server-side only — browser cleaning excluded by frontend)
                if req.ai_cleaning_enabled and req.cleaning_backend != "browser":
                    from backend.services.cleaning_service import (
                        get_cleaning_client, clean_text_chunked,
                        _resolve_model, _resolve_system_prompt,
                    )
                    client = get_cleaning_client(
                        req.cleaning_backend,
                        api_key=api_key,
                        custom_base_url=req.cleaning_custom_base_url,
                        custom_api_key=req.cleaning_custom_api_key,
                    )
                    model = _resolve_model(req.cleaning_backend, req.cleaning_custom_model)
                    system_prompt = _resolve_system_prompt(req.cleaning_preset, req.cleaning_custom_prompt)
                    text = clean_text_chunked(client, model, system_prompt, text, progress_cb=progress_cb)

                fd, tmp_path = tempfile.mkstemp(suffix=".txt")
                os.write(fd, text.encode("utf-8"))
                os.close(fd)
                source_path = tmp_path
                tmp_file = tmp_path

            # Apply voice assignment overrides (narrator = first assignment)
            speaker = req.speaker
            openai_voice = req.openai_voice
            assignments = get_assignments(req.book_id)
            if assignments:
                first = assignments[0]
                if req.engine == "mlx" and first.get("voice"):
                    speaker = first["voice"]
                elif req.engine == "openai" and first.get("voice"):
                    openai_voice = first["voice"]

            if req.engine == "mlx":
                async with mlx_lock:
                    result = await asyncio.to_thread(
                        mlx_engine.generate_audiobook,
                        file_path=source_path,
                        output_path=output_path,
                        voice_mode=req.voice_mode,
                        speaker=speaker,
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
                    result = await asyncio.to_thread(
                        oai.generate_audiobook,
                        file_path=source_path,
                        output_path=output_path,
                        voice=openai_voice,
                        model=req.openai_model,
                        instructions=req.openai_instructions,
                        progress_callback=progress_cb,
                    )

            file_id = task_id
            sse_manager.publish(task_id, "complete", {
                "audio_url": f"/api/audio/files/{file_id}",
            })
        except Exception as e:
            sse_manager.publish(task_id, "error", {"message": str(e)})
        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.unlink(tmp_file)

    asyncio.create_task(_run())
    return ConvertResponse(task_id=task_id)


@router.get("/stream/{task_id}")
async def stream(task_id: str):
    return EventSourceResponse(sse_manager.subscribe(task_id), ping=15)
