"""Cloud backend configuration module."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Configuration object sourced from environment variables."""

    app_name: str = os.getenv("CLOUD_APP_NAME", "Classroom Interaction Cloud Backend")
    host: str = os.getenv("CLOUD_HOST", "0.0.0.0")
    port: int = int(os.getenv("CLOUD_PORT", "8010"))
    debug: bool = _to_bool(os.getenv("CLOUD_DEBUG"), False)
    log_level: str = os.getenv("CLOUD_LOG_LEVEL", "INFO")

    data_dir: Path = Path(os.getenv("CLOUD_DATA_DIR", str(BASE_DIR / "data")))
    raw_dir: Path = Path(os.getenv("CLOUD_RAW_DIR", str(BASE_DIR / "data" / "raw")))
    sample_data_dir: Path = Path(os.getenv("CLOUD_SAMPLE_DATA_DIR", str(BASE_DIR / "sample_data")))

    require_api_key: bool = _to_bool(os.getenv("CLOUD_REQUIRE_API_KEY"), False)
    api_key: str = os.getenv("CLOUD_API_KEY", "")
    api_key_header: str = os.getenv("CLOUD_API_KEY_HEADER", "X-API-Key")

    classroom_id_required: bool = _to_bool(os.getenv("CLOUD_REQUIRE_CLASSROOM_ID"), False)
    source_host_required: bool = _to_bool(os.getenv("CLOUD_REQUIRE_SOURCE_HOST"), False)

    db_backend: str = os.getenv("CLOUD_DB_BACKEND", "file")
    database_url: str = os.getenv("CLOUD_DATABASE_URL", os.getenv("POSTGRES_URL", ""))
    video_upload_dir: Path = Path(os.getenv("CLOUD_VIDEO_UPLOAD_DIR", "/root/video_project/uploads"))

    jwt_secret: str = os.getenv("CLOUD_JWT_SECRET", os.getenv("JWT_SECRET", "please-change-this-dev-secret"))
    jwt_algorithm: str = os.getenv("CLOUD_JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("CLOUD_JWT_EXPIRE_MINUTES", "120"))

    def ensure_directories(self) -> None:
        """Create the runtime directories required by the service."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
