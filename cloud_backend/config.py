"""云端服务配置模块。"""
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
    """配置对象，统一从环境变量读取。"""

    app_name: str = os.getenv("CLOUD_APP_NAME", "课堂交互分析系统云端接收服务")
    host: str = os.getenv("CLOUD_HOST", "0.0.0.0")
    port: int = int(os.getenv("CLOUD_PORT", "8010"))
    debug: bool = _to_bool(os.getenv("CLOUD_DEBUG"), False)
    log_level: str = os.getenv("CLOUD_LOG_LEVEL", "INFO")

    data_dir: Path = Path(os.getenv("CLOUD_DATA_DIR", str(BASE_DIR / "data")))
    raw_dir: Path = Path(os.getenv("CLOUD_RAW_DIR", str(BASE_DIR / "data" / "raw")))

    require_api_key: bool = _to_bool(os.getenv("CLOUD_REQUIRE_API_KEY"), False)
    api_key: str = os.getenv("CLOUD_API_KEY", "")
    api_key_header: str = os.getenv("CLOUD_API_KEY_HEADER", "X-API-Key")

    classroom_id_required: bool = _to_bool(os.getenv("CLOUD_REQUIRE_CLASSROOM_ID"), False)
    source_host_required: bool = _to_bool(os.getenv("CLOUD_REQUIRE_SOURCE_HOST"), False)

    db_backend: str = os.getenv("CLOUD_DB_BACKEND", "file")
    database_url: str = os.getenv("CLOUD_DATABASE_URL", "")

    def ensure_directories(self) -> None:
        """创建运行所需目录。"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
