from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "TreasuryX"
    environment: str = "development"
    database_url: str = f"sqlite:///{BASE_DIR / 'treasuryx.db'}"
    # Comma-separated list of allowed frontend origins, e.g.
    # "http://localhost:5173,https://treasuryx-frontend.onrender.com". Set via the
    # TREASURYX_CORS_ORIGINS env var in production deployments.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    data_mode: str = "demo"  # "demo" is the only mode implemented in this build
    max_upload_size_bytes: int = 8 * 1024 * 1024  # 8 MB
    allowed_upload_extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp")
    default_var_confidence: float = 0.95
    default_var_lookback_days: int = 250

    class Config:
        env_file = ".env"
        env_prefix = "TREASURYX_"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
