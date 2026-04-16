"""日志工具。"""
from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> logging.Logger:
    """初始化日志格式。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger("cloud_backend")
