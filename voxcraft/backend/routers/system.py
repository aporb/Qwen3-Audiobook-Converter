"""System endpoints: health, device info, engine status, deployment mode, key validation, model preload."""

import asyncio
import logging
import uuid

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from backend.config import settings
from backend.engine import mlx_engine, mlx_lock, openai_engine, get_device_info, is_openai_key_valid, MLX_MODEL_IDS
from backend.schemas.system import (
    HealthResponse, DeviceInfo, EngineStatus, ModeResponse, ValidateKeyResponse,
    ModelCacheStatus, PreloadRequest,
)
from backend.utils.sse import sse_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.get("/device-info", response_model=DeviceInfo)
async def device_info():
    info = get_device_info()
    return DeviceInfo(**info)


@router.get("/engine-status", response_model=EngineStatus)
async def engine_status():
    return EngineStatus(
        mlx_loaded=mlx_engine.is_loaded,
        mlx_model_id=mlx_engine.current_model_id,
        openai_available=openai_engine.api_key_available(),
    )


@router.get("/mode", response_model=ModeResponse)
async def mode():
    mlx_available = True
    try:
        import mlx  # noqa: F401
    except ImportError:
        mlx_available = False
    return ModeResponse(
        mode=settings.deployment_mode,
        mlx_available=mlx_available,
        license_required=settings.license_required,
    )


@router.post("/validate-openai-key", response_model=ValidateKeyResponse)
async def validate_openai_key(request: Request):
    api_key = request.headers.get("X-OpenAI-Key")
    if not api_key:
        return ValidateKeyResponse(valid=False, error="No API key provided")
    valid, error = await asyncio.to_thread(is_openai_key_valid, api_key)
    return ValidateKeyResponse(valid=valid, error=error)


# Model size estimates (approximate download sizes in GB)
_MODEL_SIZES: dict[str, float] = {
    "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit": 2.0,
    "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16": 3.5,
    "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16": 3.5,
}


def _is_model_cached(model_id: str) -> bool:
    """Check if a HuggingFace model is already cached locally."""
    try:
        from huggingface_hub import scan_cache_dir
        cache_info = scan_cache_dir()
        for repo in cache_info.repos:
            if repo.repo_id == model_id:
                # Has at least one revision with files
                return any(rev.nb_files > 0 for rev in repo.revisions)
    except Exception:
        pass
    return False


@router.get("/model-cached/{voice_mode}", response_model=ModelCacheStatus)
async def model_cached(voice_mode: str):
    model_id = MLX_MODEL_IDS.get(voice_mode)
    if not model_id:
        return ModelCacheStatus(cached=False, model_id="unknown", size_gb=0)
    cached = await asyncio.to_thread(_is_model_cached, model_id)
    return ModelCacheStatus(
        cached=cached,
        model_id=model_id,
        size_gb=_MODEL_SIZES.get(model_id, 4.0),
    )


def _download_and_load(task_id: str, voice_mode: str):
    """Blocking function: download model (if needed) then load into memory."""
    model_id = MLX_MODEL_IDS.get(voice_mode)
    if not model_id:
        sse_manager.publish(task_id, "error", {"message": f"Unknown voice mode: {voice_mode}"})
        return

    if not _is_model_cached(model_id):
        sse_manager.publish(task_id, "downloading", {"fraction": 0, "message": "Starting download..."})
        try:
            from huggingface_hub import snapshot_download
            # snapshot_download handles its own progress internally
            # We publish coarse-grained progress events
            sse_manager.publish(task_id, "downloading", {"fraction": 0.05, "message": f"Downloading {model_id}..."})
            snapshot_download(model_id)
            sse_manager.publish(task_id, "downloading", {"fraction": 1.0, "message": "Download complete"})
        except Exception as e:
            logger.error(f"Model download failed: {e}")
            sse_manager.publish(task_id, "error", {"message": str(e)})
            return
    else:
        sse_manager.publish(task_id, "downloading", {"fraction": 1.0, "message": "Model already cached"})

    sse_manager.publish(task_id, "loading", {"message": "Loading model into memory..."})
    try:
        mlx_engine.load_model(voice_mode)
        sse_manager.publish(task_id, "complete", {"message": "Model ready"})
    except Exception as e:
        logger.error(f"Model load failed: {e}")
        sse_manager.publish(task_id, "error", {"message": str(e)})


@router.post("/preload-model")
async def preload_model(req: PreloadRequest):
    task_id = f"preload-{uuid.uuid4().hex[:8]}"

    async def run_in_background():
        async with mlx_lock:
            await asyncio.to_thread(_download_and_load, task_id, req.voice_mode)

    asyncio.create_task(run_in_background())

    return EventSourceResponse(sse_manager.subscribe(task_id))
