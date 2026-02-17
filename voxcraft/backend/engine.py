"""
Singleton wrappers around MLXTTSEngine and OpenAITTSEngine.

The real engine code lives at ../../src/mlx_tts_engine.py.
We add the project src/ directory to sys.path so `import mlx_tts_engine` resolves correctly.

Phase 5: Added per-request OpenAI client support via get_openai_engine().
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project src/ directory to the path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Try to import MLX-dependent classes, but make them optional
try:
    from mlx_tts_engine import (
        MLXTTSEngine,
        MLX_SPEAKERS,
        MLX_LANGUAGES,
        MLX_MODEL_IDS,
    )
    _MLX_AVAILABLE = True
except ImportError as e:
    print(f"MLX not available: {e}")
    _MLX_AVAILABLE = False
    # Create dummy classes/values for when MLX is not available
    class MLXTTSEngine:
        def __init__(self):
            self.is_loaded = False
            self.current_model_id = None
        
        def load_model(self, *args, **kwargs):
            raise RuntimeError("MLX TTS is not available. Install mlx-audio or use OpenAI engine.")
        
        def generate_speech(self, *args, **kwargs):
            raise RuntimeError("MLX TTS is not available. Install mlx-audio or use OpenAI engine.")
        
        def generate_audiobook(self, *args, **kwargs):
            raise RuntimeError("MLX TTS is not available. Install mlx-audio or use OpenAI engine.")
    
    MLX_SPEAKERS = []
    MLX_LANGUAGES = []
    MLX_MODEL_IDS = {}

# Always import OpenAI engine (should work without MLX)
from mlx_tts_engine import (  # noqa: E402
    OpenAITTSEngine,
    OPENAI_VOICES,
    OPENAI_MODELS,
    SAMPLE_RATE,
    extract_text_from_file,
    extract_book_metadata,
    split_into_chunks,
    apply_text_cleaning,
    estimate_openai_cost,
    get_device_info,
    ConversionProgress,
    BookMetadata,
)

# Singletons
mlx_engine = MLXTTSEngine()
openai_engine = OpenAITTSEngine()

# Async locks — MLX is not thread-safe
mlx_lock = asyncio.Lock()
openai_lock = asyncio.Lock()


def get_openai_engine(api_key: str | None = None) -> OpenAITTSEngine:
    """Get an OpenAI engine configured with the given API key.

    If api_key is provided, creates a fresh engine with that key injected.
    Otherwise falls back to the singleton (uses OPENAI_API_KEY env var).
    """
    if api_key:
        engine = OpenAITTSEngine()
        # Directly inject a pre-configured client
        from openai import OpenAI
        engine._client = OpenAI(api_key=api_key)
        return engine
    return openai_engine


def is_openai_key_valid(api_key: str) -> tuple[bool, str | None]:
    """Validate an OpenAI API key by calling models.list()."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        client.models.list()
        return True, None
    except Exception as e:
        return False, str(e)
