"""Backend configuration via environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings


def _detect_default_engine() -> str:
    """Detect if MLX is available and set default engine accordingly."""
    try:
        import mlx.core as mx  # noqa: F401
        import mlx_audio  # noqa: F401
        return "mlx"
    except ImportError:
        return "openai"


class Settings(BaseSettings):
    app_name: str = "VoxCraft"
    debug: bool = False

    # Paths (relative to voxcraft/)
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    uploads_dir: Path = data_dir / "uploads"
    audio_dir: Path = data_dir / "audio"
    projects_dir: Path = data_dir / "projects"
    voices_dir: Path = data_dir / "voices"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Engine - auto-detect MLX availability
    default_engine: str = _detect_default_engine()  # "mlx" or "openai"

    # Deployment
    deployment_mode: str = "local"  # "local" or "cloud"
    license_required: bool = False

    # LemonSqueezy
    lemonsqueezy_api_key: str = ""

    # Sessions (cloud mode)
    session_ttl_hours: int = 24

    model_config = {"env_prefix": "VOXCRAFT_"}

    def ensure_dirs(self):
        for d in [self.uploads_dir, self.audio_dir, self.projects_dir, self.voices_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
