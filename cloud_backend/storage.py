"""结果存储逻辑。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Settings


class FileResultRepository:
    """基于 JSON 文件的结果仓库。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def save(self, payload: dict[str, Any]) -> Path:
        """将完整 payload 保存为原始 JSON 文件。"""
        now = datetime.utcnow()
        day_dir = self.settings.raw_dir / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)

        window_id = str(payload.get("window_id", "unknown-window")).strip() or "unknown-window"
        safe_window_id = window_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
        file_path = day_dir / f"{safe_window_id}.json"

        with file_path.open("w", encoding="utf-8") as file_obj:
            json.dump(payload, file_obj, ensure_ascii=False, indent=2)

        return file_path
