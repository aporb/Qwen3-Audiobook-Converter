"""AI text cleaning endpoints."""

import asyncio
import uuid

from fastapi import APIRouter, Request, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.schemas.cleaning import (
    AICleanRequest, AICleanResponse,
    CleanPreviewRequest, CleanPreviewResponse,
)
from backend.services.cleaning_service import (
    get_cleaning_client, clean_text_chunked, clean_chunk,
    _resolve_model, _resolve_system_prompt,
)
from backend.utils.sse import sse_manager

router = APIRouter(prefix="/api/cleaning", tags=["cleaning"])


@router.post("/process", response_model=AICleanResponse)
async def process_cleaning(req: AICleanRequest, request: Request):
    if req.backend == "browser":
        raise HTTPException(
            status_code=400,
            detail="Browser cleaning runs client-side. This endpoint does not support backend='browser'.",
        )
    task_id = uuid.uuid4().hex[:12]
    api_key: str | None = request.headers.get("X-OpenAI-Key")

    model = _resolve_model(req.backend, req.custom_model)
    system_prompt = _resolve_system_prompt(req.preset, req.custom_prompt)

    async def _run():
        try:
            client = get_cleaning_client(
                req.backend,
                api_key=api_key,
                custom_base_url=req.custom_base_url,
                custom_api_key=req.custom_api_key,
            )
            progress_cb = sse_manager.make_progress_callback(task_id)

            cleaned = await asyncio.to_thread(
                clean_text_chunked,
                client, model, system_prompt,
                req.text, req.chunk_size, progress_cb,
            )

            sse_manager.publish(task_id, "complete", {"cleaned_text": cleaned})
        except Exception as e:
            sse_manager.publish(task_id, "error", {"message": str(e)})

    asyncio.create_task(_run())
    return AICleanResponse(task_id=task_id)


@router.get("/stream/{task_id}")
async def stream(task_id: str):
    return EventSourceResponse(sse_manager.subscribe(task_id), ping=15)


@router.post("/preview", response_model=CleanPreviewResponse)
async def preview_cleaning(req: CleanPreviewRequest, request: Request):
    if req.backend == "browser":
        raise HTTPException(
            status_code=400,
            detail="Browser cleaning runs client-side. This endpoint does not support backend='browser'.",
        )
    if len(req.text) > 500:
        raise HTTPException(status_code=400, detail="Preview text must be 500 characters or fewer")

    api_key: str | None = request.headers.get("X-OpenAI-Key")
    model = _resolve_model(req.backend, req.custom_model)
    system_prompt = _resolve_system_prompt(req.preset, req.custom_prompt)

    try:
        client = get_cleaning_client(
            req.backend,
            api_key=api_key,
            custom_base_url=req.custom_base_url,
            custom_api_key=req.custom_api_key,
        )
        cleaned = await asyncio.to_thread(
            clean_chunk, client, model, system_prompt, req.text,
        )
        return CleanPreviewResponse(original=req.text, cleaned=cleaned)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
