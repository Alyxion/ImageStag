"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    PLUGINS_DIR: Path = BASE_DIR / "plugins"

    # API settings
    MAX_IMAGE_SIZE: int = 4096 * 4096 * 4  # Max raw image bytes (4K x 4K RGBA)
    FILTER_TIMEOUT: float = 30.0  # Seconds

    model_config = {"env_prefix": "SLOPSTAG_"}


settings = Settings()
