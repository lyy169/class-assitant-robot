"""Storage and repository implementations for classroom feedback results."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import Settings
from .repository_interface import ResultRepository


class FileResultRepository:
    """Raw JSON storage and fallback file-based query implementation."""

    backend_name = "file"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def save(
        self,
        payload: dict[str, Any],
        source_path: Optional[Path] = None,
        source_kind: str = "raw",
    ) -> Path:
        """Persist a full payload as raw JSON."""
        if source_path is not None:
            return source_path

        now = datetime.utcnow()
        day_dir = self.settings.raw_dir / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)

        analysis_id = str(payload.get("analysis_id", "unknown-analysis")).strip() or "unknown-analysis"
        safe_analysis_id = analysis_id.replace("/", "_").replace("\\", "_").replace(" ", "_")
        file_path = day_dir / f"{safe_analysis_id}.json"

        with file_path.open("w", encoding="utf-8") as file_obj:
            json.dump(payload, file_obj, ensure_ascii=False, indent=2)

        return file_path

    def latest_result(
        self,
        classroom_id: Optional[str] = None,
    ) -> Optional[tuple[dict[str, Any], Path, str]]:
        recent_results = self.recent_results(limit=1, classroom_id=classroom_id)
        if not recent_results:
            return None

        latest = recent_results[0]
        return latest["payload"], latest["source_path"], latest["source_kind"]

    def recent_results(
        self,
        limit: int = 5,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        normalized_limit = max(1, min(limit, 50))
        normalized_classroom_id = self._normalize_classroom_id(classroom_id)

        raw_results = self._load_recent_results_from_dir(
            self.settings.raw_dir,
            "raw",
            normalized_classroom_id,
        )
        if raw_results:
            return raw_results[:normalized_limit]

        sample_results = self._load_recent_results_from_dir(
            self.settings.sample_data_dir,
            "sample",
            normalized_classroom_id,
        )
        return sample_results[:normalized_limit]

    def detail_result(
        self,
        analysis_id: str,
    ) -> Optional[tuple[dict[str, Any], Path, str]]:
        normalized_analysis_id = str(analysis_id).strip()
        if not normalized_analysis_id:
            return None

        for root_dir, source_kind in (
            (self.settings.raw_dir, "raw"),
            (self.settings.sample_data_dir, "sample"),
        ):
            if not root_dir.exists():
                continue
            for file_path in root_dir.rglob("*.json"):
                if file_path.is_file() and file_path.stem == normalized_analysis_id:
                    payload = self._read_json(file_path)
                    return payload, file_path, source_kind
        return None

    def get_teacher_sessions(self, user_id: int) -> list[dict[str, Any]]:
        """File mode has no teacher ownership table yet."""
        return []

    def summarize_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        source = payload.get("source") or {}
        time_info = payload.get("time") or {}
        summary = payload.get("summary") or {}
        teacher = payload.get("teacher") or {}
        students = payload.get("students") or {}
        timeline = payload.get("timeline") or {}
        zones = students.get("zones") or {}
        return {
            "schema_version": payload.get("schema_version"),
            "analysis_id": payload.get("analysis_id"),
            "video_id": payload.get("video_id"),
            "classroom_id": payload.get("classroom_id"),
            "source_kind": source.get("source_kind"),
            "source_path": source.get("source_path"),
            "source_host": source.get("source_host"),
            "recorded_at": time_info.get("recorded_at"),
            "generated_at": time_info.get("generated_at"),
            "duration_seconds": time_info.get("duration_seconds"),
            "feedback_score": summary.get("feedback_score"),
            "attention_score": summary.get("attention_score"),
            "response_score": summary.get("response_score"),
            "teacher_question_count": summary.get("teacher_question_count"),
            "avg_attention_ratio": summary.get("avg_attention_ratio"),
            "response_success_rate": summary.get("response_success_rate"),
            "summary_text": summary.get("summary_text"),
            "question_events": teacher.get("question_events") or [],
            "stage_distribution": teacher.get("stage_distribution") or {},
            "estimated_student_count": students.get("estimated_student_count"),
            "hand_raise_event_count": students.get("hand_raise_event_count"),
            "zones": zones,
            "window_size_seconds": timeline.get("window_size_seconds"),
            "attention_curve": timeline.get("attention_curve") or [],
            "heat_curve": timeline.get("heat_curve") or [],
            "activity_curve": timeline.get("activity_curve") or [],
        }

    def _read_json(self, file_path: Path) -> dict[str, Any]:
        with file_path.open("r", encoding="utf-8") as file_obj:
            return json.load(file_obj)

    def _load_recent_results_from_dir(
        self,
        root_dir: Path,
        source_kind: str,
        classroom_id: Optional[str],
    ) -> list[dict[str, Any]]:
        if not root_dir.exists():
            return []

        candidates = [path for path in root_dir.rglob("*.json") if path.is_file()]
        if not candidates:
            return []

        sorted_candidates = sorted(
            candidates,
            key=lambda path: self._candidate_sort_key(path),
            reverse=True,
        )

        results: list[dict[str, Any]] = []
        for file_path in sorted_candidates:
            payload = self._read_json(file_path)
            summary = self.summarize_result(payload)
            payload_classroom_id = self._normalize_classroom_id(summary.get("classroom_id"))
            if classroom_id and payload_classroom_id != classroom_id:
                continue

            results.append(
                {
                    "source_kind": source_kind,
                    "source_path": file_path,
                    "payload": payload,
                    "summary": summary,
                }
            )
        return results

    def _candidate_sort_key(self, file_path: Path) -> tuple[str, float]:
        payload = self._read_json(file_path)
        time_info = payload.get("time") or {}
        generated_at = time_info.get("generated_at")
        if isinstance(generated_at, str) and generated_at.strip():
            return generated_at.strip(), file_path.stat().st_mtime
        return "", file_path.stat().st_mtime

    def _normalize_classroom_id(self, classroom_id: Optional[str]) -> Optional[str]:
        if classroom_id is None:
            return None
        normalized = str(classroom_id).strip()
        return normalized or None


class SQLiteResultRepository:
    """SQLite-backed query/index repository with file fallback."""

    backend_name = "sqlite"

    def __init__(self, settings: Settings, fallback_repository: FileResultRepository) -> None:
        self.settings = settings
        self.fallback_repository = fallback_repository
        self.db_path = self._resolve_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_database()

    def save(
        self,
        payload: dict[str, Any],
        source_path: Optional[Path] = None,
        source_kind: str = "raw",
    ) -> Path:
        stored_path = source_path or self.fallback_repository.save(payload)
        summary = self.fallback_repository.summarize_result(payload)

        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS classroom_results (
                    analysis_id TEXT PRIMARY KEY,
                    classroom_id TEXT NOT NULL,
                    video_id TEXT,
                    schema_version TEXT,
                    source_kind TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    source_host TEXT,
                    recorded_at TEXT,
                    generated_at TEXT,
                    duration_seconds REAL,
                    feedback_score REAL,
                    attention_score REAL,
                    response_score REAL,
                    teacher_question_count INTEGER,
                    avg_attention_ratio REAL,
                    response_success_rate REAL,
                    summary_text TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO classroom_results (
                    analysis_id,
                    classroom_id,
                    video_id,
                    schema_version,
                    source_kind,
                    source_path,
                    source_host,
                    recorded_at,
                    generated_at,
                    duration_seconds,
                    feedback_score,
                    attention_score,
                    response_score,
                    teacher_question_count,
                    avg_attention_ratio,
                    response_success_rate,
                    summary_text,
                    payload_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.get("analysis_id"),
                    summary.get("classroom_id"),
                    summary.get("video_id"),
                    summary.get("schema_version"),
                    source_kind,
                    str(stored_path),
                    summary.get("source_host"),
                    self._as_text(summary.get("recorded_at")),
                    self._as_text(summary.get("generated_at")),
                    summary.get("duration_seconds"),
                    summary.get("feedback_score"),
                    summary.get("attention_score"),
                    summary.get("response_score"),
                    summary.get("teacher_question_count"),
                    summary.get("avg_attention_ratio"),
                    summary.get("response_success_rate"),
                    summary.get("summary_text"),
                    json.dumps(payload, ensure_ascii=False),
                    datetime.utcnow().isoformat(),
                ),
            )
        return stored_path

    def latest_result(
        self,
        classroom_id: Optional[str] = None,
    ) -> Optional[tuple[dict[str, Any], Path, str]]:
        recent_results = self.recent_results(limit=1, classroom_id=classroom_id)
        if recent_results:
            latest = recent_results[0]
            return latest["payload"], latest["source_path"], latest["source_kind"]
        return None

    def recent_results(
        self,
        limit: int = 5,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        normalized_limit = max(1, min(limit, 50))
        try:
            with sqlite3.connect(self.db_path) as connection:
                connection.row_factory = sqlite3.Row
                if classroom_id:
                    rows = connection.execute(
                        """
                        SELECT * FROM classroom_results
                        WHERE classroom_id = ?
                        ORDER BY generated_at DESC, created_at DESC
                        LIMIT ?
                        """,
                        (classroom_id, normalized_limit),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        """
                        SELECT * FROM classroom_results
                        ORDER BY generated_at DESC, created_at DESC
                        LIMIT ?
                        """,
                        (normalized_limit,),
                    ).fetchall()
        except sqlite3.Error:
            return self.fallback_repository.recent_results(limit=normalized_limit, classroom_id=classroom_id)

        if not rows:
            return self.fallback_repository.recent_results(limit=normalized_limit, classroom_id=classroom_id)

        records = [self._row_to_record(row) for row in rows]
        if status:
            normalized_status = str(status).strip()
            records = [record for record in records if record.get("status", "raw") == normalized_status]
        return records

    def detail_result(
        self,
        analysis_id: str,
    ) -> Optional[tuple[dict[str, Any], Path, str]]:
        normalized_analysis_id = str(analysis_id).strip()
        if not normalized_analysis_id:
            return None

        try:
            with sqlite3.connect(self.db_path) as connection:
                connection.row_factory = sqlite3.Row
                row = connection.execute(
                    "SELECT * FROM classroom_results WHERE analysis_id = ?",
                    (normalized_analysis_id,),
                ).fetchone()
        except sqlite3.Error:
            row = None

        if row is None:
            return self.fallback_repository.detail_result(normalized_analysis_id)

        record = self._row_to_record(row)
        return record["payload"], record["source_path"], record["source_kind"]

    def get_teacher_sessions(self, user_id: int) -> list[dict[str, Any]]:
        """SQLite mode is a query index and does not own teacher mappings yet."""
        return []

    def _ensure_database(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS classroom_results (
                    analysis_id TEXT PRIMARY KEY,
                    classroom_id TEXT NOT NULL,
                    video_id TEXT,
                    schema_version TEXT,
                    source_kind TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    source_host TEXT,
                    recorded_at TEXT,
                    generated_at TEXT,
                    duration_seconds REAL,
                    feedback_score REAL,
                    attention_score REAL,
                    response_score REAL,
                    teacher_question_count INTEGER,
                    avg_attention_ratio REAL,
                    response_success_rate REAL,
                    summary_text TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _resolve_db_path(self) -> Path:
        database_url = self.settings.database_url.strip()
        if not database_url:
            return self.settings.data_dir / "cloud_results.sqlite3"
        if database_url.startswith("sqlite:///"):
            return Path(database_url.removeprefix("sqlite:///"))
        return Path(database_url)

    def _row_to_record(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["payload_json"])
        summary = self.fallback_repository.summarize_result(payload)
        return {
            "source_kind": row["source_kind"],
            "source_path": Path(row["source_path"]),
            "payload": payload,
            "summary": summary,
            "status": "raw",
        }

    def _as_text(self, value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        return str(value)


def build_query_repository(settings: Settings, raw_repository: FileResultRepository) -> ResultRepository:
    """Select the active query repository without changing API handlers."""
    backend_name = settings.db_backend.strip().lower()
    if backend_name == "sqlite":
        return SQLiteResultRepository(settings, raw_repository)
    if backend_name == "postgres":
        from .postgres_repository import PostgreSQLResultRepository

        return PostgreSQLResultRepository(settings, raw_repository)
    return raw_repository
