"""Repository abstraction for cloud result storage and queries."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple


class ResultRepository(Protocol):
    """Abstract query/index repository used by the cloud backend."""

    backend_name: str

    def save(
        self,
        payload: Dict[str, Any],
        source_path: Optional[Path] = None,
        source_kind: str = "raw",
    ) -> Optional[Path]:
        ...

    def latest_result(
        self,
        classroom_id: Optional[str] = None,
    ) -> Optional[Tuple[Dict[str, Any], Path, str]]:
        ...

    def recent_results(
        self,
        limit: int = 5,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ...

    def detail_result(
        self,
        analysis_id: str,
    ) -> Optional[Tuple[Dict[str, Any], Path, str]]:
        ...

    def get_teacher_sessions(
        self,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        ...
