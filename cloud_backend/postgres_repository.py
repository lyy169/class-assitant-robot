"""PostgreSQL repository for V2 Phase 1 query and indexing support."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras

from .config import Settings
from .reporting import build_rule_report
from .storage import FileResultRepository


FINAL_COMPETITION_ANALYSIS_ID = "phase314_asr_full_classroom_sav_20200908_17"
SAV_FULL_CLASSROOM_HISTORY_IDS = {
    "phase37_full_classroom_sav_20200908_17",
}
SMOKE_TEST_ANALYSIS_IDS = {
    "phase35_local_imported_sav_full_classroom_20200908_17",
}
LEGACY_TEST_ANALYSIS_IDS = {
    "cls_20260417_101_001",
    "cls_20260430_classroom_101_d4b91cf9c0bf4e68bfcb5e12933d30ee",
    "cls_20260429_classroom_101_c993e071203b44e1bef1db1586181503",
}
LEGACY_TEST_VIDEO_IDS = {
    "video_20260417_001",
}


class PostgreSQLResultRepository:
    """PostgreSQL-backed repository that keeps raw JSON as the write floor."""

    backend_name = "postgres"

    def __init__(self, settings: Settings, fallback_repository: FileResultRepository) -> None:
        self.settings = settings
        self.fallback_repository = fallback_repository
        self.database_url = settings.database_url.strip()
        self._phase2_schema_checked = False
        if not self.database_url:
            raise ValueError("CLOUD_DATABASE_URL is required when CLOUD_DB_BACKEND=postgres")

    def save(
        self,
        payload: Dict[str, Any],
        source_path: Optional[Path] = None,
        source_kind: str = "raw",
    ) -> Path:
        return self.save_result(payload, source_path=source_path, source_kind=source_kind)

    def save_result(
        self,
        payload: Dict[str, Any],
        source_path: Optional[Path] = None,
        source_kind: str = "raw",
    ) -> Path:
        stored_path = source_path or self.fallback_repository.save(payload)
        summary = self.fallback_repository.summarize_result(payload)
        classroom_name, lesson_title = self._extract_workbench_metadata(payload, summary)
        self.ensure_phase2_schema()

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sessions (
                        classroom_id,
                        analysis_id,
                        video_id,
                        recorded_at,
                        generated_at,
                        duration_seconds,
                        raw_json_path
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (analysis_id) DO UPDATE SET
                        classroom_id = EXCLUDED.classroom_id,
                        video_id = EXCLUDED.video_id,
                        recorded_at = EXCLUDED.recorded_at,
                        generated_at = EXCLUDED.generated_at,
                        duration_seconds = EXCLUDED.duration_seconds,
                        raw_json_path = EXCLUDED.raw_json_path
                    RETURNING id
                    """,
                    (
                        summary.get("classroom_id"),
                        summary.get("analysis_id"),
                        summary.get("video_id"),
                        self._as_datetime(summary.get("recorded_at")),
                        self._as_datetime(summary.get("generated_at")),
                        summary.get("duration_seconds"),
                        str(stored_path),
                    ),
                )
                session_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO analysis_results (
                        analysis_id,
                        session_id,
                        classroom_id,
                        schema_version,
                        source_kind,
                        source_path,
                        source_host,
                        generated_at,
                        feedback_score,
                        attention_score,
                        response_score,
                        classroom_name,
                        lesson_title,
                        status,
                        updated_at,
                        payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'raw', now(), %s::jsonb)
                    ON CONFLICT (analysis_id) DO UPDATE SET
                        session_id = EXCLUDED.session_id,
                        classroom_id = EXCLUDED.classroom_id,
                        schema_version = EXCLUDED.schema_version,
                        source_kind = EXCLUDED.source_kind,
                        source_path = EXCLUDED.source_path,
                        source_host = EXCLUDED.source_host,
                        generated_at = EXCLUDED.generated_at,
                        feedback_score = EXCLUDED.feedback_score,
                        attention_score = EXCLUDED.attention_score,
                        response_score = EXCLUDED.response_score,
                        classroom_name = EXCLUDED.classroom_name,
                        lesson_title = EXCLUDED.lesson_title,
                        updated_at = now(),
                        payload_json = EXCLUDED.payload_json
                    """,
                    (
                        summary.get("analysis_id"),
                        session_id,
                        summary.get("classroom_id"),
                        summary.get("schema_version"),
                        source_kind,
                        str(stored_path),
                        summary.get("source_host"),
                        self._as_datetime(summary.get("generated_at")),
                        summary.get("feedback_score"),
                        summary.get("attention_score"),
                        summary.get("response_score"),
                        classroom_name,
                        lesson_title,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
        return stored_path

    def latest_result(
        self,
        classroom_id: Optional[str] = None,
    ) -> Optional[Tuple[Dict[str, Any], Path, str]]:
        recent = self.recent_results(limit=100, classroom_id=classroom_id)
        if recent:
            latest = next((item for item in recent if self._record_frontstage_visible(item)), recent[0])
            return latest["payload"], latest["source_path"], latest["source_kind"]
        return self.fallback_repository.latest_result(classroom_id=classroom_id)

    def get_latest(
        self,
        classroom_id: Optional[str] = None,
    ) -> Optional[Tuple[Dict[str, Any], Path, str]]:
        return self.latest_result(classroom_id=classroom_id)

    def recent_results(
        self,
        limit: int = 5,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.get_recent(limit=limit, classroom_id=classroom_id, status=status)

    def get_recent(
        self,
        limit: int = 5,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized_limit = max(1, min(limit, 100))
        normalized_status = self._normalize_status(status, allow_empty=True)
        self.ensure_phase2_schema()
        try:
            with self._connect() as connection:
                with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    filters = []
                    params: List[Any] = []
                    if classroom_id:
                        filters.append("classroom_id = %s")
                        params.append(classroom_id)
                    if normalized_status:
                        filters.append("status = %s")
                        params.append(normalized_status)
                    where_clause = "WHERE " + " AND ".join(filters) if filters else ""
                    params.append(normalized_limit)
                    cursor.execute(
                        f"""
                        SELECT *
                        FROM analysis_results
                        {where_clause}
                        ORDER BY created_at DESC, generated_at DESC NULLS LAST
                        LIMIT %s
                        """,
                        tuple(params),
                    )
                    rows = cursor.fetchall()
        except psycopg2.Error:
            return self.fallback_repository.recent_results(
                limit=normalized_limit,
                classroom_id=classroom_id,
                status=normalized_status,
            )

        if not rows and (normalized_status or classroom_id):
            return []
        if not rows:
            return self.fallback_repository.recent_results(limit=normalized_limit, classroom_id=classroom_id)
        return [self._row_to_record(row) for row in rows]

    def detail_result(
        self,
        analysis_id: str,
    ) -> Optional[Tuple[Dict[str, Any], Path, str]]:
        normalized_analysis_id = str(analysis_id).strip()
        if not normalized_analysis_id:
            return None

        try:
            self.ensure_phase2_schema()
            with self._connect() as connection:
                with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM analysis_results WHERE analysis_id = %s",
                        (normalized_analysis_id,),
                    )
                    row = cursor.fetchone()
        except psycopg2.Error:
            row = None

        if not row:
            return self.fallback_repository.detail_result(normalized_analysis_id)

        record = self._row_to_record(row)
        return record["payload"], record["source_path"], record["source_kind"]

    def get_teacher_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        self.ensure_phase2_schema()
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        s.analysis_id,
                        s.classroom_id,
                        s.video_id,
                        s.recorded_at,
                        s.generated_at,
                        s.duration_seconds,
                        s.raw_json_path,
                        ar.source_kind,
                        ar.source_path,
                        ar.feedback_score,
                        ar.attention_score,
                        ar.response_score,
                        ar.status,
                        ar.updated_at
                    FROM sessions s
                    JOIN teacher_classrooms tc ON tc.classroom_id = s.classroom_id
                    LEFT JOIN analysis_results ar ON ar.analysis_id = s.analysis_id
                    WHERE tc.user_id::text = %s
                    ORDER BY s.generated_at DESC NULLS LAST, s.created_at DESC
                    LIMIT 50
                    """,
                        (str(user_id),),
                )
                return [dict(row) for row in cursor.fetchall()]

    def get_teacher_session_detail(self, user_id: str, analysis_id: str, is_admin: bool = False) -> Optional[Dict[str, Any]]:
        self.ensure_phase2_schema()
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                if is_admin:
                    cursor.execute(
                        """
                        SELECT
                            s.analysis_id,
                            s.classroom_id,
                            s.video_id,
                            s.recorded_at,
                            s.generated_at,
                            s.duration_seconds,
                            s.raw_json_path,
                            ar.source_kind,
                            ar.source_path,
                            ar.feedback_score,
                            ar.attention_score,
                            ar.response_score,
                            ar.status,
                            ar.updated_at,
                            ar.payload_json
                        FROM sessions s
                        LEFT JOIN analysis_results ar ON ar.analysis_id = s.analysis_id
                        WHERE s.analysis_id = %s
                        """,
                        (analysis_id,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT
                            s.analysis_id,
                            s.classroom_id,
                            s.video_id,
                            s.recorded_at,
                            s.generated_at,
                            s.duration_seconds,
                            s.raw_json_path,
                            ar.source_kind,
                            ar.source_path,
                            ar.feedback_score,
                            ar.attention_score,
                            ar.response_score,
                            ar.status,
                            ar.updated_at,
                            ar.payload_json
                        FROM sessions s
                        JOIN teacher_classrooms tc ON tc.classroom_id = s.classroom_id
                        LEFT JOIN analysis_results ar ON ar.analysis_id = s.analysis_id
                        WHERE s.analysis_id = %s
                          AND tc.user_id::text = %s
                        """,
                        (analysis_id, str(user_id)),
                    )
                row = cursor.fetchone()
                if not row:
                    return None
                result = dict(row)
                payload = result.get("payload_json")
                if isinstance(payload, str):
                    result["payload_json"] = json.loads(payload)
                return result

    def get_teacher_trends(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        normalized_limit = max(1, min(limit, 50))
        self.ensure_phase2_schema()
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        ar.analysis_id,
                        ar.classroom_id,
                        ar.generated_at,
                        ar.feedback_score,
                        ar.attention_score,
                        ar.response_score,
                        ar.source_kind,
                        ar.status
                    FROM analysis_results ar
                    JOIN teacher_classrooms tc ON tc.classroom_id = ar.classroom_id
                    WHERE tc.user_id::text = %s
                    ORDER BY ar.generated_at DESC NULLS LAST, ar.created_at DESC
                    LIMIT %s
                    """,
                    (str(user_id), normalized_limit),
                )
                return [dict(row) for row in cursor.fetchall()]

    def get_workbench_recent(
        self,
        limit: int = 10,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        normalized_limit = max(1, min(int(limit or 10), 100))
        query_limit = min(max(normalized_limit * 5, 100), 500)
        if user_id is None:
            records = self.get_recent(query_limit, classroom_id, status)
            visible_records = [record for record in records if self._record_frontstage_visible(record)]
            return [self._workbench_recent_item_from_record(record) for record in visible_records[:normalized_limit]]
        rows = self._teacher_result_rows(
            user_id=str(user_id),
            classroom_id=classroom_id,
            status=self._normalize_status(status, allow_empty=True),
            limit=query_limit,
            offset=0,
        )
        visible = self._frontstage_items([self._row_to_teacher_result_item(row) for row in rows])
        return [self._workbench_recent_item_from_list_item(item) for item in visible[:normalized_limit]]

    def _workbench_recent_item_from_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        item = self._row_to_workbench_item(record)
        summary = record.get("summary") or {}
        item.update(
            {
                "source_kind": record.get("source_kind") or "raw",
                "source_path": str(record.get("source_path") or ""),
                "summary": summary,
            }
        )
        return item

    def _workbench_recent_item_from_list_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        summary = {
            "analysis_id": item.get("analysis_id"),
            "classroom_id": item.get("classroom_id"),
            "lesson_title": item.get("lesson_title"),
            "created_at": item.get("created_at"),
            "generated_at": item.get("generated_at"),
            "feedback_score": item.get("feedback_score"),
            "status": item.get("status"),
        }
        return {
            **item,
            "source_kind": item.get("source_kind") or "raw",
            "source_path": str(item.get("raw_path") or ""),
            "summary": summary,
        }

    def get_workbench_classrooms(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        self.ensure_phase2_schema()
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                filters = []
                params: List[Any] = []
                join_clause = ""
                if user_id is not None:
                    join_clause = "JOIN teacher_classrooms tc ON tc.classroom_id = ar.classroom_id"
                    filters.append("tc.user_id::text = %s")
                    params.append(str(user_id))
                where_clause = "WHERE " + " AND ".join(filters) if filters else ""
                cursor.execute(
                    f"""
                    SELECT
                        COALESCE(NULLIF(ar.classroom_id, ''), 'unknown') AS classroom_id,
                        COALESCE(MAX(NULLIF(ar.classroom_name, '')), MAX(c.name), 'Unknown Classroom') AS classroom_name,
                        COUNT(*) AS result_count,
                        MAX(ar.created_at) AS latest_result_at
                    FROM analysis_results ar
                    {join_clause}
                    LEFT JOIN classrooms c ON c.classroom_id = ar.classroom_id
                    {where_clause}
                    GROUP BY COALESCE(NULLIF(ar.classroom_id, ''), 'unknown')
                    ORDER BY MAX(ar.created_at) DESC NULLS LAST
                    """,
                    tuple(params),
                )
                return [dict(row) for row in cursor.fetchall()]

    def get_workbench_result_detail(self, result_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        normalized_result_id = str(result_id).strip()
        if not normalized_result_id:
            return None
        self.ensure_phase2_schema()
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                join_clause = ""
                filters = ["ar.analysis_id = %s"]
                params: List[Any] = [normalized_result_id]
                if user_id is not None:
                    join_clause = "JOIN teacher_classrooms tc ON tc.classroom_id = ar.classroom_id"
                    filters.append("tc.user_id::text = %s")
                    params.append(str(user_id))
                cursor.execute(
                    f"""
                    SELECT ar.*, c.name AS mapped_classroom_name
                    FROM analysis_results ar
                    {join_clause}
                    LEFT JOIN classrooms c ON c.classroom_id = ar.classroom_id
                    WHERE {" AND ".join(filters)}
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_workbench_detail(dict(row))

    def update_workbench_status(self, result_id: str, status: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        normalized_result_id = str(result_id).strip()
        normalized_status = self._normalize_status(status, allow_empty=False)
        self.ensure_phase2_schema()
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                permission_clause = ""
                params: List[Any] = [normalized_status, normalized_result_id]
                if user_id is not None:
                    permission_clause = """
                    AND EXISTS (
                        SELECT 1
                        FROM teacher_classrooms tc
                        WHERE tc.classroom_id = analysis_results.classroom_id
                          AND tc.user_id::text = %s
                    )
                    """
                    params.append(str(user_id))
                cursor.execute(
                    f"""
                    UPDATE analysis_results
                    SET status = %s, updated_at = now()
                    WHERE analysis_id = %s
                    {permission_clause}
                    RETURNING *
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_workbench_item(self._row_to_record(dict(row)))

    def get_teacher_overview(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        rows = self._teacher_result_rows(user_id=user_id, limit=500, offset=0)
        items = self._frontstage_items([self._row_to_teacher_result_item(row) for row in rows])
        classrooms: Dict[str, Dict[str, Any]] = {}
        for item in items:
            classroom_id = item.get("classroom_id") or "unknown"
            classroom = classrooms.setdefault(
                classroom_id,
                {
                    "classroom_id": classroom_id,
                    "classroom_name": item.get("classroom_name") or classroom_id,
                    "result_count": 0,
                    "latest_result_at": None,
                    "avg_feedback_score": 0.0,
                    "_feedback_values": [],
                },
            )
            classroom["result_count"] += 1
            latest_at = item.get("created_at") or item.get("generated_at")
            if latest_at and (not classroom["latest_result_at"] or str(latest_at) > str(classroom["latest_result_at"])):
                classroom["latest_result_at"] = latest_at
            if item.get("feedback_score") is not None:
                classroom["_feedback_values"].append(float(item.get("feedback_score") or 0))

        classroom_summaries = []
        for classroom in classrooms.values():
            values = classroom.pop("_feedback_values")
            classroom["avg_feedback_score"] = round(sum(values) / len(values), 2) if values else None
            classroom["records_url"] = f"/teacher/results?classroom_id={classroom['classroom_id']}"
            classroom_summaries.append(classroom)
        classroom_summaries.sort(key=lambda item: str(item.get("latest_result_at") or ""), reverse=True)

        metrics = self._teacher_metrics(items, classroom_summaries)
        latest_results = items[:5]
        return {
            "success": True,
            "teacher": self._teacher_context(user_id),
            "metrics": metrics,
            "latest_results": latest_results,
            "classroom_summaries": classroom_summaries,
            "todo_items": self._teacher_todo_items(metrics, latest_results),
        }

    def get_teacher_results(
        self,
        user_id: Optional[str] = None,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
        days: Optional[int] = 30,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        normalized_status = self._normalize_status(status, allow_empty=True)
        normalized_limit = max(1, min(int(limit or 20), 100))
        normalized_offset = max(0, int(offset or 0))
        normalized_days = self._normalize_days_value(days)
        rows = self._teacher_result_rows(
            user_id=user_id,
            classroom_id=classroom_id,
            status=normalized_status,
            days=normalized_days,
            limit=min(max(normalized_limit * 5, 100), 500),
            offset=normalized_offset,
        )
        total = self._teacher_result_count(
            user_id=user_id,
            classroom_id=classroom_id,
            status=normalized_status,
            days=normalized_days,
        )
        items = self._frontstage_items([self._row_to_teacher_result_item(row) for row in rows])[:normalized_limit]
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "status": normalized_status or "",
                "days": normalized_days,
                "limit": normalized_limit,
                "offset": normalized_offset,
            },
            "items": items,
            "total": len(items),
            "raw_total": total,
        }

    def get_phase3_teacher_trends(
        self,
        user_id: Optional[str] = None,
        classroom_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        data_source: str = "real",
        limit: int = 20,
    ) -> Dict[str, Any]:
        normalized_source = self._normalize_data_source(data_source)
        normalized_limit = max(1, min(int(limit or 20), 100))
        rows = self._phase3_result_rows(
            user_id=user_id,
            classroom_id=classroom_id,
            date_from=date_from,
            date_to=date_to,
            data_source=normalized_source,
            limit=min(max(normalized_limit * 5, 100), 1000),
        )
        lessons = self._trend_items([self._row_to_phase3_lesson(row) for row in rows])
        lessons.sort(key=lambda item: str(item.get("created_at") or ""), reverse=False)
        overview = self._phase3_overview(lessons)
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "data_source": normalized_source,
                "limit": normalized_limit,
            },
            "overview": overview,
            "series": self._phase3_series(lessons),
            "stage_distribution": self._phase3_stage_average(lessons),
            "risk_lessons": [item for item in reversed(lessons) if item.get("risk_level") in {"medium", "high"}][:8],
            "recommendations": self._phase3_recommendations(lessons),
            "data_quality": self._phase3_data_quality(lessons, normalized_source),
        }

    def get_phase3_teacher_reports(
        self,
        user_id: Optional[str] = None,
        classroom_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        data_source: str = "real",
        limit: int = 20,
    ) -> Dict[str, Any]:
        normalized_source = self._normalize_data_source(data_source)
        normalized_limit = max(1, min(int(limit or 20), 100))
        rows = self._phase3_result_rows(
            user_id=user_id,
            classroom_id=classroom_id,
            date_from=date_from,
            date_to=date_to,
            data_source=normalized_source,
            limit=min(max(normalized_limit * 5, 100), 1000),
        )
        raw_items = [self._row_to_phase3_report_item(row) for row in rows]
        items = self._report_items(raw_items)[:normalized_limit]
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "data_source": normalized_source,
                "limit": normalized_limit,
            },
            "items": items,
            "total": len(items),
            "raw_total": len(raw_items),
        }

    def get_phase3_teacher_report_detail(
        self,
        result_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        rows = self._phase3_result_rows(user_id=user_id, result_id=result_id, data_source="all", limit=1)
        if not rows:
            return None
        return self._row_to_phase3_report_detail(rows[0])

    def get_phase3_admin_trends(
        self,
        classroom_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        data_source: str = "real",
        limit: int = 30,
    ) -> Dict[str, Any]:
        normalized_source = self._normalize_data_source(data_source)
        normalized_limit = max(1, min(int(limit or 30), 100))
        rows = self._phase3_result_rows(
            classroom_id=classroom_id,
            teacher_id=teacher_id,
            date_from=date_from,
            date_to=date_to,
            data_source=normalized_source,
            limit=min(max(normalized_limit * 5, 100), 1000),
        )
        lessons = self._trend_items([self._row_to_phase3_lesson(row) for row in rows])
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "teacher_id": teacher_id or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "data_source": normalized_source,
                "limit": normalized_limit,
            },
            "overview": self._phase3_overview(lessons),
            "classroom_rankings": self._phase3_classroom_rankings(lessons),
            "teacher_activity": self._phase3_teacher_activity(lessons),
            "risk_lessons": [item for item in lessons if item.get("risk_level") in {"medium", "high"}][:10],
            "recent_reports": [self._phase3_lesson_to_report_summary(item) for item in lessons[:10]],
            "data_quality": self._phase3_data_quality(lessons, normalized_source),
        }

    def get_admin_overview(self) -> Dict[str, Any]:
        rows = self._admin_result_rows(limit=500, offset=0)
        items = self._frontstage_items([self._row_to_admin_result_item(row) for row in rows])
        status_distribution = self._status_distribution(items)
        return {
            "success": True,
            "admin": self._admin_context(),
            "metrics": self._admin_metrics(items),
            "system_status": self._admin_system_status(items),
            "status_distribution": status_distribution,
            "latest_results": items[:8],
            "quick_links": [
                {"label": "Classrooms", "url": "/admin/classrooms", "description": "Review classroom coverage and activity."},
                {"label": "Teachers", "url": "/admin/teachers", "description": "Review teacher coverage and score rankings."},
                {"label": "Classroom Data", "url": "/admin/results", "description": "Search all platform classroom analyses."},
                {"label": "Teacher Console", "url": "/teacher", "description": "Open the teacher-facing workflow."},
            ],
        }

    def get_admin_classrooms(
        self,
        q: Optional[str] = None,
        teacher_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        rows = self._admin_result_rows(limit=1000, offset=0)
        items = self._frontstage_items([self._row_to_admin_result_item(row) for row in rows])
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in items:
            classroom_id = item.get("classroom_id") or "unknown"
            group = grouped.setdefault(
                classroom_id,
                {
                    "classroom_id": classroom_id,
                    "classroom_name": item.get("classroom_name") or classroom_id,
                    "teacher_id": item.get("teacher_id") or "",
                    "teacher_name": item.get("teacher_name") or "Demo Teacher",
                    "result_count": 0,
                    "avg_feedback_score": None,
                    "avg_attention_score": None,
                    "avg_response_score": None,
                    "raw_count": 0,
                    "reviewed_count": 0,
                    "archived_count": 0,
                    "latest_result_at": None,
                    "results_url": f"/admin/results?classroom_id={classroom_id}",
                    "_feedback_values": [],
                    "_attention_values": [],
                    "_response_values": [],
                },
            )
            group["result_count"] += 1
            status = item.get("status") or "raw"
            if status in {"raw", "reviewed", "archived"}:
                group[f"{status}_count"] += 1
            latest_at = item.get("created_at") or item.get("generated_at")
            if latest_at and (not group["latest_result_at"] or str(latest_at) > str(group["latest_result_at"])):
                group["latest_result_at"] = latest_at
            self._append_metric_value(group["_feedback_values"], item.get("feedback_score"))
            self._append_metric_value(group["_attention_values"], item.get("attention_score"))
            self._append_metric_value(group["_response_values"], item.get("response_score"))

        filtered = list(grouped.values())
        if q:
            needle = str(q).strip().lower()
            filtered = [
                item for item in filtered
                if needle in str(item.get("classroom_id") or "").lower()
                or needle in str(item.get("classroom_name") or "").lower()
                or needle in str(item.get("teacher_name") or "").lower()
            ]
        if teacher_id:
            filtered = [item for item in filtered if str(item.get("teacher_id") or "") == str(teacher_id)]
        for item in filtered:
            item["avg_feedback_score"] = self._average_values(item.pop("_feedback_values"))
            item["avg_attention_score"] = self._average_values(item.pop("_attention_values"))
            item["avg_response_score"] = self._average_values(item.pop("_response_values"))
        filtered.sort(key=lambda item: str(item.get("latest_result_at") or ""), reverse=True)
        total = len(filtered)
        start = max(0, int(offset or 0))
        end = start + max(1, min(int(limit or 50), 100))
        page_items = filtered[start:end]
        return {
            "success": True,
            "overview": {
                "classroom_count": len(grouped),
                "active_classroom_count": len([item for item in grouped.values() if item.get("result_count", 0) > 0]),
                "avg_feedback_score": self._average_metric(items, "feedback_score"),
                "latest_result_at": items[0].get("created_at") if items else None,
            },
            "items": page_items,
            "total": total,
        }

    def get_admin_teachers(
        self,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        rows = self._admin_result_rows(limit=1000, offset=0)
        items = self._frontstage_items([self._row_to_admin_result_item(row) for row in rows])
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in items:
            teacher_id = item.get("teacher_id") or "demo"
            group = grouped.setdefault(
                teacher_id,
                {
                    "teacher_id": teacher_id,
                    "teacher_name": item.get("teacher_name") or "Demo Teacher",
                    "username": item.get("teacher_username") or "demo_teacher",
                    "classroom_count": 0,
                    "result_count": 0,
                    "avg_feedback_score": None,
                    "avg_attention_score": None,
                    "avg_response_score": None,
                    "latest_result_at": None,
                    "results_url": f"/admin/results?teacher_id={teacher_id}",
                    "_classrooms": set(),
                    "_feedback_values": [],
                    "_attention_values": [],
                    "_response_values": [],
                },
            )
            group["result_count"] += 1
            if item.get("classroom_id"):
                group["_classrooms"].add(item["classroom_id"])
            latest_at = item.get("created_at") or item.get("generated_at")
            if latest_at and (not group["latest_result_at"] or str(latest_at) > str(group["latest_result_at"])):
                group["latest_result_at"] = latest_at
            self._append_metric_value(group["_feedback_values"], item.get("feedback_score"))
            self._append_metric_value(group["_attention_values"], item.get("attention_score"))
            self._append_metric_value(group["_response_values"], item.get("response_score"))

        filtered = list(grouped.values())
        if q:
            needle = str(q).strip().lower()
            filtered = [
                item for item in filtered
                if needle in str(item.get("teacher_id") or "").lower()
                or needle in str(item.get("teacher_name") or "").lower()
                or needle in str(item.get("username") or "").lower()
            ]
        for item in filtered:
            item["classroom_count"] = len(item.pop("_classrooms"))
            item["avg_feedback_score"] = self._average_values(item.pop("_feedback_values"))
            item["avg_attention_score"] = self._average_values(item.pop("_attention_values"))
            item["avg_response_score"] = self._average_values(item.pop("_response_values"))
        filtered.sort(key=lambda item: (item.get("result_count") or 0, str(item.get("latest_result_at") or "")), reverse=True)
        total = len(filtered)
        start = max(0, int(offset or 0))
        end = start + max(1, min(int(limit or 50), 100))
        return {
            "success": True,
            "overview": {
                "teacher_count": len(grouped),
                "teachers_with_classrooms": len([item for item in filtered if item.get("classroom_count", 0) > 0]),
                "teachers_with_results": len([item for item in filtered if item.get("result_count", 0) > 0]),
                "avg_feedback_score": self._average_metric(items, "feedback_score"),
            },
            "items": filtered[start:end],
            "total": total,
        }

    def get_admin_results(
        self,
        classroom_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        status: Optional[str] = None,
        days: Optional[int] = 30,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        normalized_status = self._normalize_status(status, allow_empty=True)
        normalized_limit = max(1, min(int(limit or 20), 100))
        normalized_offset = max(0, int(offset or 0))
        normalized_days = self._normalize_days_value(days)
        rows = self._admin_result_rows(
            classroom_id=classroom_id,
            teacher_id=teacher_id,
            status=normalized_status,
            days=normalized_days,
            limit=min(max(normalized_limit * 5, 100), 500),
            offset=normalized_offset,
        )
        total = self._admin_result_count(
            classroom_id=classroom_id,
            teacher_id=teacher_id,
            status=normalized_status,
            days=normalized_days,
        )
        items = self._frontstage_items([self._row_to_admin_result_item(row) for row in rows])[:normalized_limit]
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "teacher_id": teacher_id or "",
                "status": normalized_status or "",
                "days": normalized_days,
                "limit": normalized_limit,
                "offset": normalized_offset,
            },
            "overview": self._admin_results_overview(items, len(items)),
            "items": items,
            "total": len(items),
            "raw_total": total,
        }

    def get_admin_ingestion(
        self,
        classroom_id: Optional[str] = None,
        device_id: Optional[str] = None,
        source_host: Optional[str] = None,
        days: Optional[int] = 30,
        limit: int = 20,
    ) -> Dict[str, Any]:
        normalized_days = self._normalize_days_value(days)
        normalized_limit = max(1, min(int(limit or 20), 100))
        rows = self._admin_result_rows(
            classroom_id=classroom_id,
            days=normalized_days,
            limit=500,
            offset=0,
        )
        ingestions = [self._row_to_ingestion_item(row) for row in rows]
        if device_id:
            ingestions = [item for item in ingestions if item.get("device_id") == device_id]
        if source_host:
            ingestions = [item for item in ingestions if item.get("source_host") == source_host]

        devices = self._ingestion_devices(ingestions)
        video_summary = self._ingestion_video_summary(ingestions)
        overview = self._ingestion_overview(ingestions, devices, video_summary)
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "device_id": device_id or "",
                "source_host": source_host or "",
                "days": normalized_days,
                "limit": normalized_limit,
            },
            "overview": overview,
            "pipeline": self._ingestion_pipeline(overview),
            "devices": devices,
            "recent_ingestions": ingestions[:normalized_limit],
            "video_summary": video_summary,
            "validation_hints": self._ingestion_validation_hints(ingestions, devices),
        }

    def _admin_result_rows(
        self,
        classroom_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        status: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        self.ensure_phase2_schema()
        filters = []
        params: List[Any] = []
        if classroom_id:
            filters.append("ar.classroom_id = %s")
            params.append(classroom_id)
        if teacher_id:
            if str(teacher_id) == "demo":
                filters.append("tc.user_id IS NULL")
            else:
                filters.append("tc.user_id::text = %s")
                params.append(str(teacher_id))
        if status:
            filters.append("ar.status = %s")
            params.append(status)
        if days is not None:
            filters.append("COALESCE(ar.created_at, ar.generated_at, s.generated_at) >= now() - (%s * interval '1 day')")
            params.append(days)
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        params.extend([max(1, min(int(limit or 20), 1000)), max(0, int(offset or 0))])
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        ar.*,
                        c.name AS mapped_classroom_name,
                        tc.user_id::text AS teacher_user_id,
                        u.username AS teacher_username,
                        s.recorded_at AS session_recorded_at,
                        s.generated_at AS session_generated_at,
                        s.duration_seconds AS session_duration_seconds,
                        s.video_id AS session_video_id
                    FROM analysis_results ar
                    LEFT JOIN sessions s ON s.analysis_id = ar.analysis_id
                    LEFT JOIN classrooms c ON c.classroom_id = ar.classroom_id
                    LEFT JOIN teacher_classrooms tc ON tc.classroom_id = ar.classroom_id
                    LEFT JOIN users u ON u.user_id = tc.user_id
                    {where_clause}
                    ORDER BY COALESCE(ar.created_at, ar.generated_at, s.generated_at) DESC NULLS LAST
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [dict(row) for row in cursor.fetchall()]

    def _phase3_result_rows(
        self,
        user_id: Optional[str] = None,
        classroom_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        result_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        data_source: str = "real",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        self.ensure_phase2_schema()
        normalized_source = self._normalize_data_source(data_source)
        filters = ["COALESCE(ar.status, 'raw') IN ('raw', 'reviewed')"]
        params: List[Any] = []
        if user_id is not None:
            filters.append("tc.user_id::text = %s")
            params.append(str(user_id))
        if classroom_id:
            filters.append("ar.classroom_id = %s")
            params.append(classroom_id)
        if teacher_id:
            filters.append("tc.user_id::text = %s")
            params.append(str(teacher_id))
        if result_id:
            filters.append("ar.analysis_id = %s")
            params.append(str(result_id))
        if date_from:
            filters.append("COALESCE(ar.created_at, ar.generated_at, s.generated_at)::date >= %s::date")
            params.append(date_from)
        if date_to:
            filters.append("COALESCE(ar.created_at, ar.generated_at, s.generated_at)::date <= %s::date")
            params.append(date_to)
        if normalized_source == "real":
            filters.append("COALESCE(NULLIF(ar.payload_json->'dataset'->>'source', ''), 'real') = 'real'")
        elif normalized_source == "demo":
            filters.append("ar.payload_json->'dataset'->>'source' = 'demo'")
        elif normalized_source == "all":
            filters.append("COALESCE(NULLIF(ar.payload_json->'dataset'->>'source', ''), 'real') IN ('real', 'demo')")
        where_clause = "WHERE " + " AND ".join(filters)
        params.append(max(1, min(int(limit or 20), 1000)))
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        ar.*,
                        c.name AS mapped_classroom_name,
                        tc.user_id::text AS teacher_user_id,
                        u.username AS teacher_username,
                        u.display_name AS teacher_display_name,
                        s.recorded_at AS session_recorded_at,
                        s.generated_at AS session_generated_at,
                        s.duration_seconds AS session_duration_seconds,
                        s.video_id AS session_video_id
                    FROM analysis_results ar
                    LEFT JOIN sessions s ON s.analysis_id = ar.analysis_id
                    LEFT JOIN classrooms c ON c.classroom_id = ar.classroom_id
                    LEFT JOIN teacher_classrooms tc ON tc.classroom_id = ar.classroom_id
                    LEFT JOIN users u ON u.user_id = tc.user_id
                    {where_clause}
                    ORDER BY COALESCE(ar.created_at, ar.generated_at, s.generated_at) DESC NULLS LAST
                    LIMIT %s
                    """,
                    tuple(params),
                )
                return [dict(row) for row in cursor.fetchall()]

    def _admin_result_count(
        self,
        classroom_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        status: Optional[str] = None,
        days: Optional[int] = None,
    ) -> int:
        filters = []
        params: List[Any] = []
        if classroom_id:
            filters.append("ar.classroom_id = %s")
            params.append(classroom_id)
        if teacher_id:
            if str(teacher_id) == "demo":
                filters.append("tc.user_id IS NULL")
            else:
                filters.append("tc.user_id::text = %s")
                params.append(str(teacher_id))
        if status:
            filters.append("ar.status = %s")
            params.append(status)
        if days is not None:
            filters.append("COALESCE(ar.created_at, ar.generated_at, s.generated_at) >= now() - (%s * interval '1 day')")
            params.append(days)
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM analysis_results ar
                    LEFT JOIN sessions s ON s.analysis_id = ar.analysis_id
                    LEFT JOIN classrooms c ON c.classroom_id = ar.classroom_id
                    LEFT JOIN teacher_classrooms tc ON tc.classroom_id = ar.classroom_id
                    {where_clause}
                    """,
                    tuple(params),
                )
                return int(cursor.fetchone()[0] or 0)

    def _teacher_result_rows(
        self,
        user_id: Optional[str] = None,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        self.ensure_phase2_schema()
        filters = []
        params: List[Any] = []
        join_clause = ""
        if user_id is not None:
            join_clause = "JOIN teacher_classrooms tc ON tc.classroom_id = ar.classroom_id"
            filters.append("tc.user_id::text = %s")
            params.append(str(user_id))
        if classroom_id:
            filters.append("ar.classroom_id = %s")
            params.append(classroom_id)
        if status:
            filters.append("ar.status = %s")
            params.append(status)
        if days is not None:
            filters.append("COALESCE(ar.created_at, ar.generated_at, s.generated_at) >= now() - (%s * interval '1 day')")
            params.append(days)
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        params.extend([max(1, min(int(limit or 20), 500)), max(0, int(offset or 0))])
        with self._connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        ar.*,
                        c.name AS mapped_classroom_name,
                        s.recorded_at AS session_recorded_at,
                        s.generated_at AS session_generated_at,
                        s.duration_seconds AS session_duration_seconds,
                        s.video_id AS session_video_id
                    FROM analysis_results ar
                    {join_clause}
                    LEFT JOIN sessions s ON s.analysis_id = ar.analysis_id
                    LEFT JOIN classrooms c ON c.classroom_id = ar.classroom_id
                    {where_clause}
                    ORDER BY COALESCE(ar.created_at, ar.generated_at, s.generated_at) DESC NULLS LAST
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params),
                )
                return [dict(row) for row in cursor.fetchall()]

    def _teacher_result_count(
        self,
        user_id: Optional[str] = None,
        classroom_id: Optional[str] = None,
        status: Optional[str] = None,
        days: Optional[int] = None,
    ) -> int:
        filters = []
        params: List[Any] = []
        join_clause = ""
        if user_id is not None:
            join_clause = "JOIN teacher_classrooms tc ON tc.classroom_id = ar.classroom_id"
            filters.append("tc.user_id::text = %s")
            params.append(str(user_id))
        if classroom_id:
            filters.append("ar.classroom_id = %s")
            params.append(classroom_id)
        if status:
            filters.append("ar.status = %s")
            params.append(status)
        if days is not None:
            filters.append("COALESCE(ar.created_at, ar.generated_at, s.generated_at) >= now() - (%s * interval '1 day')")
            params.append(days)
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM analysis_results ar
                    {join_clause}
                    LEFT JOIN sessions s ON s.analysis_id = ar.analysis_id
                    LEFT JOIN classrooms c ON c.classroom_id = ar.classroom_id
                    {where_clause}
                    """,
                    tuple(params),
                )
                return int(cursor.fetchone()[0] or 0)

    def _row_to_teacher_result_item(self, row: Dict[str, Any]) -> Dict[str, Any]:
        detail = self._row_to_workbench_detail(row)
        payload = detail.get("raw_payload") or {}
        time_info = payload.get("time") or {}
        video = detail.get("video") or {}
        generated_at = self._as_iso(row.get("generated_at")) or self._as_iso(row.get("session_generated_at"))
        recorded_at = self._as_iso(row.get("session_recorded_at")) or time_info.get("recorded_at") or ""
        duration_seconds = self._number_value(row.get("session_duration_seconds"), time_info.get("duration_seconds"))
        analysis_id = detail.get("analysis_id") or row.get("analysis_id")
        video_status = video.get("status") or "missing"
        presentation_scope = detail.get("presentation_scope") or {}
        return {
            "result_id": analysis_id,
            "analysis_id": analysis_id,
            "classroom_id": detail.get("classroom_id") or row.get("classroom_id") or "unknown",
            "classroom_name": detail.get("classroom_name") or row.get("mapped_classroom_name") or row.get("classroom_id") or "unknown",
            "lesson_title": detail.get("lesson_title") or row.get("lesson_title") or row.get("session_video_id") or "Untitled Lesson",
            "recorded_at": recorded_at,
            "generated_at": generated_at,
            "created_at": self._as_iso(row.get("created_at")),
            "duration_seconds": duration_seconds,
            "feedback_score": detail.get("feedback_score"),
            "attention_score": detail.get("attention_score"),
            "response_score": detail.get("response_score"),
            "status": detail.get("status") or "raw",
            "has_video": video_status == "playable" or bool(video.get("video_id") or video.get("raw_video_path")),
            "video_status": video_status,
            "source_dataset": detail.get("source_dataset"),
            "sample_type": detail.get("sample_type"),
            "is_pi_capture": detail.get("is_pi_capture"),
            "is_own_capture": detail.get("is_own_capture"),
            "data_quality_note": presentation_scope.get("note") or detail.get("data_quality_note") or "",
            "presentation_scope": presentation_scope,
            "display_metrics": presentation_scope.get("metrics") or [],
            "display_badge": presentation_scope.get("display_badge") or "课堂样本",
            "record_kind": presentation_scope.get("record_kind") or "standard_classroom",
            "frontend_visible": presentation_scope.get("frontend_visible", True),
            "detail_url": f"/dashboard?result_id={analysis_id}",
            "updated_at": self._as_iso(row.get("updated_at")),
        }

    def _row_to_admin_result_item(self, row: Dict[str, Any]) -> Dict[str, Any]:
        item = self._row_to_teacher_result_item(row)
        teacher_user_id = row.get("teacher_user_id")
        teacher_id = str(teacher_user_id) if teacher_user_id not in (None, "") else "demo"
        teacher_name = row.get("teacher_username") or ("Demo Teacher" if teacher_id == "demo" else f"Teacher {teacher_id}")
        item.update(
            {
                "teacher_id": teacher_id,
                "teacher_name": teacher_name,
                "teacher_username": row.get("teacher_username") or "demo_teacher",
            }
        )
        return item

    def _row_to_ingestion_item(self, row: Dict[str, Any]) -> Dict[str, Any]:
        record = self._row_to_record(row)
        payload = record.get("payload") or {}
        source = payload.get("source") or {}
        capture = payload.get("capture") or {}
        video = payload.get("video") or {}
        upload = payload.get("upload") or {}
        time_info = payload.get("time") or {}
        summary = record.get("summary") or {}
        result_id = row.get("analysis_id") or summary.get("analysis_id")
        inferred_device_id = (
            capture.get("device_id")
            or video.get("device_id")
            or source.get("source_host")
            or "unknown"
        )
        source_host = source.get("source_host") or upload.get("source_host") or "unknown"
        capture_time = (
            capture.get("captured_at")
            or time_info.get("start_time")
            or row.get("created_at")
        )
        upload_time = (
            upload.get("uploaded_at")
            or row.get("created_at")
            or time_info.get("generated_at")
            or row.get("generated_at")
        )
        standardized_video_path = video.get("standardized_video_path") or capture.get("standardized_video_path") or ""
        browser_compatible = video.get("browser_compatible")
        transcode_status = video.get("transcode_status") or ("present" if standardized_video_path else "unknown")
        transcode_error = video.get("transcode_error") or ""
        video_status = self._ingestion_video_status(payload)
        display_scope = self._display_scope(payload)
        missing_metadata = []
        if not capture:
            missing_metadata.append("capture")
        if source_host == "unknown":
            missing_metadata.append("source_host")
        if not video:
            missing_metadata.append("video")
        metadata_status = "complete" if not missing_metadata else "partial"
        return {
            "result_id": result_id,
            "analysis_id": result_id,
            "classroom_id": row.get("classroom_id") or payload.get("classroom_id") or capture.get("classroom_id") or "unknown",
            "lesson_title": row.get("lesson_title") or payload.get("lesson_title") or payload.get("video_id") or "Untitled Lesson",
            "device_id": inferred_device_id,
            "device_name": capture.get("device_name") or inferred_device_id or "unknown device",
            "source_host": source_host,
            "capture_time": self._as_iso(capture_time),
            "upload_time": self._as_iso(upload_time),
            "video_status": video_status,
            "standardized_video_path": standardized_video_path,
            "standardized_video_present": bool(standardized_video_path),
            "browser_compatible": browser_compatible,
            "transcode_status": transcode_status,
            "transcode_error": transcode_error,
            "source_dataset": display_scope.get("source_dataset"),
            "sample_type": display_scope.get("sample_type"),
            "is_pi_capture": display_scope.get("is_pi_capture"),
            "is_own_capture": display_scope.get("is_own_capture"),
            "capture_label": display_scope.get("capture_label"),
            "data_quality_note": display_scope.get("data_quality_note") or "",
            "metadata_status": metadata_status,
            "metadata_quality": "good" if metadata_status == "complete" else "needs_metadata",
            "missing_metadata": missing_metadata,
            "freshness": self._freshness(upload_time),
            "detail_url": f"/dashboard?result_id={result_id}",
        }

    def _ingestion_video_status(self, payload: Dict[str, Any]) -> str:
        capture = payload.get("capture") or {}
        video = payload.get("video") or {}
        if video.get("video_url"):
            return "playable"
        if video.get("raw_video_path") or video.get("standardized_video_path") or capture.get("video_path") or capture.get("standardized_video_path"):
            return "pending"
        return "missing"

    def _ingestion_devices(self, ingestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in ingestions:
            key = f"{item.get('device_id') or 'unknown'}::{item.get('classroom_id') or 'unknown'}::{item.get('source_host') or 'unknown'}"
            device = grouped.setdefault(
                key,
                {
                    "device_id": item.get("device_id") or "unknown",
                    "device_name": item.get("device_name") or "unknown device",
                    "classroom_id": item.get("classroom_id") or "unknown",
                    "source_host": item.get("source_host") or "unknown",
                    "latest_result_id": item.get("result_id"),
                    "latest_capture_time": item.get("capture_time"),
                    "latest_upload_time": item.get("upload_time"),
                    "freshness": item.get("freshness") or "unknown",
                    "total_sessions": 0,
                    "video_status": item.get("video_status") or "missing",
                    "standardized_video_present": bool(item.get("standardized_video_present")),
                    "browser_compatible": item.get("browser_compatible"),
                    "transcode_status": item.get("transcode_status") or "unknown",
                    "transcode_error": item.get("transcode_error") or "",
                    "metadata_quality": item.get("metadata_quality") or "needs_metadata",
                },
            )
            device["total_sessions"] += 1
            latest_upload = item.get("upload_time")
            if latest_upload and (not device.get("latest_upload_time") or str(latest_upload) > str(device["latest_upload_time"])):
                device["latest_result_id"] = item.get("result_id")
                device["latest_capture_time"] = item.get("capture_time")
                device["latest_upload_time"] = latest_upload
                device["freshness"] = item.get("freshness") or "unknown"
                device["video_status"] = item.get("video_status") or "missing"
                device["standardized_video_present"] = bool(item.get("standardized_video_present"))
                device["browser_compatible"] = item.get("browser_compatible")
                device["transcode_status"] = item.get("transcode_status") or "unknown"
                device["transcode_error"] = item.get("transcode_error") or ""
                device["metadata_quality"] = item.get("metadata_quality") or "needs_metadata"
        devices = list(grouped.values())
        devices.sort(key=lambda item: str(item.get("latest_upload_time") or ""), reverse=True)
        return devices

    def _ingestion_video_summary(self, ingestions: List[Dict[str, Any]]) -> Dict[str, int]:
        summary = {
            "playable": 0,
            "pending": 0,
            "missing": 0,
            "unknown": 0,
            "standardized_present": 0,
            "browser_compatible": 0,
            "browser_incompatible": 0,
            "transcode_failed": 0,
        }
        for item in ingestions:
            status = item.get("video_status") or "unknown"
            if status not in {"playable", "pending", "missing", "unknown"}:
                status = "unknown"
            summary[status] += 1
            if item.get("standardized_video_present"):
                summary["standardized_present"] += 1
            if item.get("browser_compatible") is True:
                summary["browser_compatible"] += 1
            elif item.get("browser_compatible") is False:
                summary["browser_incompatible"] += 1
            if item.get("transcode_status") == "failed" or item.get("transcode_error"):
                summary["transcode_failed"] += 1
        return summary

    def _ingestion_overview(
        self,
        ingestions: List[Dict[str, Any]],
        devices: List[Dict[str, Any]],
        video_summary: Dict[str, int],
    ) -> Dict[str, Any]:
        unknown_metadata = len([item for item in ingestions if item.get("metadata_status") != "complete"])
        complete_count = len(ingestions) - unknown_metadata
        complete_rate = round((complete_count / len(ingestions)) * 100, 1) if ingestions else 0.0
        return {
            "total_results": len(ingestions),
            "active_devices": len([item for item in devices if item.get("freshness") == "online"]),
            "stale_devices": len([item for item in devices if item.get("freshness") == "stale"]),
            "offline_devices": len([item for item in devices if item.get("freshness") == "offline"]),
            "unknown_devices": len([item for item in devices if item.get("freshness") == "unknown"]),
            "playable_videos": video_summary.get("playable", 0),
            "pending_videos": video_summary.get("pending", 0),
            "missing_videos": video_summary.get("missing", 0),
            "unknown_metadata_count": unknown_metadata,
            "metadata_complete_rate": complete_rate,
        }

    def _ingestion_pipeline(self, overview: Dict[str, Any]) -> List[Dict[str, Any]]:
        total = overview.get("total_results", 0)
        return [
            {
                "stage": "Capture or External Sample",
                "status": "inferred",
                "count": total,
                "description": "Capture endpoint, uploaded package, or external sample metadata inferred from payload.",
            },
            {
                "stage": "Local Analysis",
                "status": "inferred",
                "count": total,
                "description": "Local analyzer/source host inferred from payload.source or payload.upload.",
            },
            {
                "stage": "Cloud Storage",
                "status": "ok" if total else "waiting",
                "count": total,
                "description": "Raw JSON preserved and indexed in PostgreSQL.",
            },
            {
                "stage": "Teacher Feedback",
                "status": "ready" if total else "waiting",
                "count": total,
                "description": "Results can open the teacher classroom analysis dashboard.",
            },
        ]

    def _ingestion_validation_hints(
        self,
        ingestions: List[Dict[str, Any]],
        devices: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        hints: List[Dict[str, Any]] = []
        missing_capture = len([item for item in ingestions if "capture" in (item.get("missing_metadata") or [])])
        missing_source = len([item for item in ingestions if "source_host" in (item.get("missing_metadata") or [])])
        missing_video = len([item for item in ingestions if "video" in (item.get("missing_metadata") or [])])
        stale_devices = [item for item in devices if item.get("freshness") in {"stale", "offline"}]
        failed_transcodes = len([item for item in ingestions if item.get("transcode_status") == "failed" or item.get("transcode_error")])
        incompatible_videos = len([item for item in ingestions if item.get("browser_compatible") is False])
        if missing_capture:
            hints.append({"type": "missing_capture_metadata", "severity": "warning", "message": f"{missing_capture} result(s) are missing capture metadata."})
        if missing_source:
            hints.append({"type": "missing_source_host", "severity": "warning", "message": f"{missing_source} result(s) are missing source host metadata."})
        if missing_video:
            hints.append({"type": "missing_video_metadata", "severity": "info", "message": f"{missing_video} result(s) are missing video metadata."})
        if failed_transcodes:
            hints.append({"type": "video_transcode_failed", "severity": "warning", "message": f"{failed_transcodes} result(s) report video transcode failure or error metadata."})
        if incompatible_videos:
            hints.append({"type": "video_browser_incompatible", "severity": "warning", "message": f"{incompatible_videos} result(s) report browser_compatible=false."})
        if stale_devices:
            hints.append({"type": "stale_device_upload", "severity": "warning", "message": f"{len(stale_devices)} device/source group(s) have stale or offline inferred freshness."})
        if not hints:
            hints.append({"type": "metadata_ready", "severity": "ok", "message": "Current ingestion metadata is sufficient for cloud-side traceability."})
        return hints

    def _row_to_phase3_lesson(self, row: Dict[str, Any]) -> Dict[str, Any]:
        detail = self._row_to_workbench_detail(row)
        payload = detail.get("raw_payload") or {}
        summary = detail.get("summary") or {}
        timeline = detail.get("timeline") or {}
        stage = detail.get("stage_distribution") or {}
        events = detail.get("events") or []
        teacher = payload.get("teacher") or {}
        students = payload.get("students") or {}
        dataset_source = self._dataset_source(payload)
        presentation_scope = detail.get("presentation_scope") or {}
        data_quality_note = presentation_scope.get("note") or detail.get("data_quality_note") or self._external_asr_data_quality_note(payload)
        score = self._number_value(summary.get("feedback_score"), row.get("feedback_score"), payload.get("score"), payload.get("overall_score"))
        attention_score = self._number_value(summary.get("attention_score"), row.get("attention_score"), summary.get("avg_attention_ratio") * 100 if summary.get("avg_attention_ratio") else None)
        activity_score = self._activity_score(payload, timeline, students)
        question_events = teacher.get("question_events") or payload.get("question_events") or []
        question_count = int(self._number_value(summary.get("teacher_question_count"), len(question_events)))
        response_rate = self._number_value(summary.get("response_success_rate"), payload.get("response_rate"))
        if response_rate > 1:
            response_rate = response_rate / 100.0
        issue_count = len(payload.get("issues") or []) + len([event for event in events if event.get("event_type") not in {"question", "unknown"}])
        metrics = {
            "score": score,
            "attention_score": attention_score,
            "activity_score": activity_score,
            "question_count": question_count,
            "response_rate": response_rate,
            "management_ratio": stage.get("management_ratio"),
            "issue_count": issue_count,
        }
        rule = build_rule_report(metrics)
        risk_level = "sample" if presentation_scope.get("record_kind") == "competition_final" else rule["risk_level"]
        created_at = self._as_iso(row.get("created_at")) or self._as_iso(row.get("generated_at")) or self._as_iso(row.get("session_generated_at"))
        return {
            "result_id": detail.get("analysis_id") or row.get("analysis_id"),
            "analysis_id": detail.get("analysis_id") or row.get("analysis_id"),
            "classroom_id": detail.get("classroom_id") or row.get("classroom_id") or "unknown",
            "classroom_name": detail.get("classroom_name") or row.get("mapped_classroom_name") or row.get("classroom_id") or "unknown",
            "teacher_id": str(row.get("teacher_user_id") or "demo"),
            "teacher_name": row.get("teacher_display_name") or row.get("teacher_username") or "Demo Teacher",
            "lesson_title": detail.get("lesson_title") or row.get("lesson_title") or "Untitled Lesson",
            "created_at": created_at,
            "score": round(score, 2),
            "attention_score": round(attention_score, 2),
            "activity_score": round(activity_score, 2),
            "question_count": question_count,
            "response_rate": round(response_rate, 3),
            "discussion_ratio": self._ratio_value(stage.get("discussion_ratio")),
            "exposition_ratio": self._ratio_value(stage.get("exposition_ratio")),
            "management_ratio": self._ratio_value(stage.get("management_ratio")),
            "summary_ratio": self._ratio_value(stage.get("summary_ratio")),
            "issue_count": issue_count,
            "event_count": len(events),
            "dataset_source": dataset_source,
            "source_dataset": detail.get("source_dataset"),
            "sample_type": detail.get("sample_type"),
            "data_quality_note": data_quality_note,
            "presentation_scope": presentation_scope,
            "display_metrics": presentation_scope.get("metrics") or [],
            "display_badge": presentation_scope.get("display_badge") or "课堂样本",
            "record_kind": presentation_scope.get("record_kind") or "standard_classroom",
            "report_eligible": presentation_scope.get("report_eligible", True),
            "trend_eligible": presentation_scope.get("trend_eligible", True),
            "risk_level": risk_level,
            "detail_url": f"/dashboard?result_id={detail.get('analysis_id') or row.get('analysis_id')}",
            "report_url": f"/teacher/reports?result_id={detail.get('analysis_id') or row.get('analysis_id')}",
        }

    def _row_to_phase3_report_item(self, row: Dict[str, Any]) -> Dict[str, Any]:
        item = self._row_to_phase3_lesson(row)
        return {
            **item,
            "dashboard_url": item["detail_url"],
        }

    def _row_to_phase3_report_detail(self, row: Dict[str, Any]) -> Dict[str, Any]:
        lesson = self._row_to_phase3_lesson(row)
        detail = self._row_to_workbench_detail(row)
        payload = detail.get("raw_payload") or {}
        timeline = detail.get("timeline") or {}
        stage = detail.get("stage_distribution") or {}
        events = detail.get("events") or []
        narrative = self._phase3_report_narrative(lesson, detail)
        enhanced_fields = self._phase32_enhanced_fields(payload)
        question_guidance = self._phase33_question_guidance_fields(payload)
        report = {
            "basic": {
                "result_id": lesson["result_id"],
                "classroom_id": lesson["classroom_id"],
                "classroom_name": lesson["classroom_name"],
                "teacher_name": lesson["teacher_name"],
                "lesson_title": lesson["lesson_title"],
                "created_at": lesson["created_at"],
                "status": detail.get("status") or "raw",
            },
            "scores": {
                "overall_score": lesson["score"],
                "attention_score": lesson["attention_score"],
                "activity_score": lesson["activity_score"],
                "response_rate": lesson["response_rate"],
            },
            "timeline": {
                "attention_curve": timeline.get("attention_curve") or [],
                "activity_curve": timeline.get("activity_curve") or [],
                "heat_curve": timeline.get("heat_curve") or [],
            },
            "stage_distribution": stage,
            "question_analysis": {
                "question_count": lesson["question_count"],
                "response_rate": lesson["response_rate"],
                "events": [
                    event for event in events
                    if event.get("question_type") or event.get("event_type") in {"question", "question_candidate"}
                ],
            },
            "issues": [event for event in events if event.get("event_type") not in {"question", "unknown"}],
            "highlights": narrative["highlights"],
            "risks": narrative["risks"],
            "recommendations": narrative["recommendations"],
            "risk_level": narrative["risk_level"],
            "ai_summary": {"enabled": False, "status": "not_configured", "content": ""},
            "dataset_source": lesson["dataset_source"],
            "source_dataset": lesson.get("source_dataset"),
            "sample_type": lesson.get("sample_type"),
            "data_quality_note": lesson.get("data_quality_note") or "",
            "presentation_scope": lesson.get("presentation_scope") or {},
            "display_metrics": lesson.get("display_metrics") or [],
            "display_badge": lesson.get("display_badge") or "课堂样本",
            "record_kind": lesson.get("record_kind") or "standard_classroom",
            "display_scope": detail.get("display_scope") or {},
            "display_flags": detail.get("display_flags") or {},
            "asr_display": detail.get("asr_display") or {},
            "dashboard_url": lesson["detail_url"],
        }
        if enhanced_fields:
            report["phase32"] = enhanced_fields
            report["enhanced_issues"] = enhanced_fields.get("enhanced_issues") or []
            report["quality_metrics"] = enhanced_fields.get("quality_metrics") or {}
            report["score_breakdown"] = enhanced_fields.get("score_breakdown") or {}
        if question_guidance:
            report["phase33"] = question_guidance
            report["teacher_question_events"] = question_guidance.get("teacher_question_events") or []
            report["question_guidance_summary"] = question_guidance.get("question_guidance_summary") or {}
        return report

    def _phase3_report_narrative(self, lesson: Dict[str, Any], detail: Dict[str, Any]) -> Dict[str, Any]:
        presentation = lesson.get("presentation_scope") or {}
        profile = presentation.get("metric_profile") or "standard"
        if profile == "asr_multimodal":
            asr = detail.get("asr_display") or {}
            transcript_count = int(self._number_value(asr.get("transcript_segment_count")))
            question_count = int(self._number_value(asr.get("question_event_count")))
            response_count = int(self._number_value(asr.get("response_detected_count")))
            response_rate = self._number_value(asr.get("response_success_rate")) * 100
            return {
                "risk_level": "sample",
                "highlights": [
                    f"本节课为最终 ASR 增强完整课堂展示样本，已生成 {transcript_count} 个转写片段。",
                    f"识别出 {question_count} 个教师提问候选事件，完成视觉响应对齐并检测到 {response_count} 次响应。",
                    f"响应率约 {response_rate:.1f}%，报告以视频证据、ASR 转写和响应对齐为主要依据。",
                ],
                "risks": [],
                "recommendations": [
                    "比赛展示时优先打开课堂分析页，同屏说明视频证据、ASR 提问候选和响应对齐。",
                    "该 SAV 外部公开课堂样本不作为常规课堂质量排名依据，不展示专注度 0 或教学阶段灰图。",
                    "当前未进行说话人分离，提问事件应表述为教师提问候选，不作为精准教师身份识别结论。",
                ],
            }
        if profile == "unavailable":
            return {
                "risk_level": "unknown",
                "highlights": ["该记录属于旧测试数据或缺少有效分析结果，仅允许直达查看原始详情。"],
                "risks": [],
                "recommendations": ["不要将该记录纳入正式课堂报告、趋势或质量排名。"],
            }
        rule = build_rule_report(lesson)
        if presentation.get("record_kind") in {"historical_version", "smoke_test"}:
            rule["risk_level"] = "unknown"
            rule["risks"] = []
        return rule

    def _phase3_overview(self, lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "lesson_count": len(lessons),
            "avg_score": self._average_metric(lessons, "score"),
            "avg_attention_score": self._average_metric(lessons, "attention_score"),
            "avg_activity_score": self._average_metric(lessons, "activity_score"),
            "avg_response_rate": self._average_metric(lessons, "response_rate"),
            "risk_lesson_count": len([item for item in lessons if item.get("risk_level") in {"medium", "high"}]),
            "high_risk_count": len([item for item in lessons if item.get("risk_level") == "high"]),
        }

    def _phase3_series(self, lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
        labels = [str(item.get("created_at") or "")[:10] for item in lessons]
        return {
            "labels": labels,
            "score": [item.get("score") for item in lessons],
            "attention_score": [item.get("attention_score") for item in lessons],
            "activity_score": [item.get("activity_score") for item in lessons],
            "question_count": [item.get("question_count") for item in lessons],
            "response_rate": [item.get("response_rate") for item in lessons],
        }

    def _phase3_stage_average(self, lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            key: self._average_metric(lessons, key)
            for key in ["discussion_ratio", "exposition_ratio", "management_ratio", "summary_ratio"]
        }

    def _phase3_recommendations(self, lessons: List[Dict[str, Any]]) -> List[str]:
        recommendations: List[str] = []
        for item in lessons:
            recommendations.extend(build_rule_report(item)["recommendations"])
        if not recommendations:
            return ["真实数据不足时，建议先完成多节课上传，再观察趋势变化。"]
        seen = set()
        result = []
        for recommendation in recommendations:
            if recommendation in seen:
                continue
            seen.add(recommendation)
            result.append(recommendation)
        return result[:6]

    def _phase3_data_quality(self, lessons: List[Dict[str, Any]], data_source: str) -> Dict[str, Any]:
        source_counts: Dict[str, int] = {}
        for item in lessons:
            source = item.get("dataset_source") or "unknown"
            source_counts[source] = source_counts.get(source, 0) + 1
        external_asr_notes = [
            item.get("data_quality_note")
            for item in lessons
            if item.get("sample_type") == "external_full_classroom_video_with_asr" and item.get("data_quality_note")
        ]
        return {
            "data_source": data_source,
            "source_counts": source_counts,
            "insufficient_real_data": data_source == "real" and len(lessons) < 2,
            "demo_warning": data_source in {"demo", "all"},
            "external_asr_sample_present": bool(external_asr_notes),
            "notes": external_asr_notes[:1],
        }

    def _phase3_classroom_rankings(self, lessons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in lessons:
            classroom_id = item.get("classroom_id") or "unknown"
            group = grouped.setdefault(classroom_id, {"classroom_id": classroom_id, "classroom_name": item.get("classroom_name"), "lesson_count": 0, "_scores": []})
            group["lesson_count"] += 1
            group["_scores"].append(item.get("score"))
        result = []
        for group in grouped.values():
            scores = [float(value) for value in group.pop("_scores") if value is not None]
            group["avg_score"] = round(sum(scores) / len(scores), 2) if scores else None
            result.append(group)
        return sorted(result, key=lambda item: item.get("avg_score") or 0, reverse=True)[:10]

    def _phase3_teacher_activity(self, lessons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in lessons:
            teacher_id = item.get("teacher_id") or "demo"
            group = grouped.setdefault(teacher_id, {"teacher_id": teacher_id, "teacher_name": item.get("teacher_name"), "lesson_count": 0, "_scores": []})
            group["lesson_count"] += 1
            group["_scores"].append(item.get("score"))
        result = []
        for group in grouped.values():
            scores = [float(value) for value in group.pop("_scores") if value is not None]
            group["avg_score"] = round(sum(scores) / len(scores), 2) if scores else None
            result.append(group)
        return sorted(result, key=lambda item: (item.get("lesson_count") or 0, item.get("avg_score") or 0), reverse=True)[:10]

    def _phase3_lesson_to_report_summary(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "result_id": item.get("result_id"),
            "classroom_name": item.get("classroom_name"),
            "teacher_name": item.get("teacher_name"),
            "lesson_title": item.get("lesson_title"),
            "score": item.get("score"),
            "risk_level": item.get("risk_level"),
            "dataset_source": item.get("dataset_source"),
            "source_dataset": item.get("source_dataset"),
            "sample_type": item.get("sample_type"),
            "data_quality_note": item.get("data_quality_note"),
            "presentation_scope": item.get("presentation_scope") or {},
            "display_metrics": item.get("display_metrics") or [],
            "display_badge": item.get("display_badge") or "课堂样本",
            "record_kind": item.get("record_kind") or "standard_classroom",
            "report_url": item.get("report_url"),
            "dashboard_url": item.get("detail_url"),
        }

    def _dataset_source(self, payload: Dict[str, Any]) -> str:
        dataset = payload.get("dataset") or {}
        source = str(dataset.get("source") or "real").strip().lower()
        if source in {"real", "demo"}:
            return source
        return "unknown"

    def _normalize_data_source(self, data_source: Optional[str]) -> str:
        normalized = str(data_source or "real").strip().lower()
        if normalized not in {"real", "demo", "all"}:
            return "real"
        return normalized

    def _record_kind(self, payload: Dict[str, Any], analysis_id: Optional[str], scope: Dict[str, Any]) -> Tuple[str, str, bool, bool, bool, str]:
        timeline = payload.get("timeline") or {}
        summary = payload.get("summary") or {}
        lesson_title = self._text_value(payload.get("lesson_title"), payload.get("video_id"))
        video_id = self._text_value(payload.get("video_id"), (payload.get("video") or {}).get("video_id"))
        dataset_source = self._dataset_source(payload)
        source_dataset = str(scope.get("source_dataset") or "")
        sample_type = str(scope.get("sample_type") or "")
        normalized_id = str(analysis_id or payload.get("analysis_id") or "")
        activity_curve = self._number_list(timeline.get("activity_curve"))
        attention_curve = self._number_list(timeline.get("attention_curve"))
        event_count = len(payload.get("events") or [])
        active_windows = len([value for value in activity_curve if value > 0])
        all_zero_core = not event_count and not active_windows and not any(value > 0 for value in attention_curve) and self._number_value(summary.get("feedback_score")) == 0
        kind, profile = "standard_classroom", "standard"
        visible = report_ok = trend_ok = True
        if dataset_source == "demo":
            kind = "demo_data"
        if normalized_id == FINAL_COMPETITION_ANALYSIS_ID:
            kind, profile = "competition_final", "asr_multimodal"
            trend_ok = False
        elif normalized_id in SMOKE_TEST_ANALYSIS_IDS or "cloud_playback_demo" in sample_type.lower():
            kind = "smoke_test"
            visible = report_ok = trend_ok = False
        elif normalized_id in SAV_FULL_CLASSROOM_HISTORY_IDS or (source_dataset.upper() == "SAV" and sample_type in {"external_full_classroom_video", "cloud_playback_demo_from_external_classroom_video"}):
            kind = "historical_version"
            visible = report_ok = trend_ok = False
        if normalized_id in LEGACY_TEST_ANALYSIS_IDS or video_id in LEGACY_TEST_VIDEO_IDS or (all_zero_core and (lesson_title == "video_video" or not source_dataset)):
            kind, profile = "legacy_test_data", "unavailable"
            visible = report_ok = trend_ok = False
        return kind, profile, visible, report_ok, trend_ok, dataset_source

    def _presentation_metrics(self, payload: Dict[str, Any], profile: str, asr: Dict[str, Any], flags: Dict[str, Any]) -> List[Dict[str, Any]]:
        summary = payload.get("summary") or {}
        timeline = payload.get("timeline") or {}
        activity_curve = self._number_list(timeline.get("activity_curve"))
        active_windows = len([value for value in activity_curve if value > 0])
        event_count = len(payload.get("events") or [])
        if profile == "asr_multimodal":
            return [
                {"key": "transcript_segments", "label": "转写片段", "value": int(self._number_value(asr.get("transcript_segment_count")))},
                {"key": "question_candidates", "label": "提问候选", "value": int(self._number_value(asr.get("question_event_count")))},
                {"key": "response_detected", "label": "检测到响应", "value": int(self._number_value(asr.get("response_detected_count")))},
                {"key": "response_rate", "label": "响应率", "value": round(self._number_value(asr.get("response_success_rate")) * 100, 1), "suffix": "%"},
                {"key": "active_windows", "label": "活跃片段", "value": active_windows},
            ]
        if profile == "unavailable":
            return []
        metrics = [
            {"key": "feedback_score", "label": "反馈分", "value": round(self._number_value(summary.get("feedback_score")), 2)},
            {"key": "response_score", "label": "响应", "value": round(self._number_value(summary.get("response_score")), 2)},
            {"key": "question_count", "label": "提问", "value": int(self._number_value(summary.get("teacher_question_count"), event_count))},
        ]
        if not flags.get("hide_attention_metrics"):
            metrics.insert(1, {"key": "attention_score", "label": "专注", "value": round(self._number_value(summary.get("attention_score")), 2)})
        return metrics

    def _presentation_scope(
        self,
        payload: Dict[str, Any],
        analysis_id: Optional[str] = None,
        display_scope: Optional[Dict[str, Any]] = None,
        asr_display: Optional[Dict[str, Any]] = None,
        display_flags: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        scope = display_scope or self._display_scope(payload)
        asr = asr_display or self._asr_display(payload)
        flags = display_flags or self._display_flags(payload, display_scope=scope, asr_display=asr)
        kind, profile, visible, report_ok, trend_ok, dataset_source = self._record_kind(payload, analysis_id, scope)
        badge_map = {
            "competition_final": "最终展示样本",
            "historical_version": "历史阶段样本",
            "smoke_test": "播放链路 smoke test",
            "legacy_test_data": "旧测试数据",
            "demo_data": "演示数据",
            "standard_classroom": "课堂样本",
        }
        note_map = {
            "competition_final": scope.get("data_quality_note") or "外部 SAV ASR 增强样本，不参与常规课堂质量排名。",
            "historical_version": "同一 SAV 完整课堂的历史阶段版本，默认不作为前端展示样本。",
            "smoke_test": "播放链路验证记录，不作为完整课堂报告或趋势样本。",
            "legacy_test_data": "早期测试/旧导入数据，缺少有效分析结果。",
            "demo_data": "演示数据，仅用于功能展示，不代表真实课堂结论。",
        }
        return {
            "record_kind": kind,
            "display_badge": badge_map.get(kind, "课堂样本"),
            "frontend_visible": visible,
            "report_eligible": report_ok,
            "trend_eligible": trend_ok,
            "metric_profile": profile,
            "is_demo_data": dataset_source == "demo",
            "is_historical": kind in {"historical_version", "smoke_test", "legacy_test_data"},
            "note": note_map.get(kind, scope.get("data_quality_note") or ""),
            "metrics": self._presentation_metrics(payload, profile, asr, flags),
        }

    def _frontstage_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self._sort_presentation_items([
            item for item in items if (item.get("presentation_scope") or {}).get("frontend_visible", True)
        ])

    def _report_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self._sort_presentation_items([
            item for item in items if (item.get("presentation_scope") or {}).get("report_eligible", True)
        ])

    def _trend_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [item for item in items if (item.get("presentation_scope") or {}).get("trend_eligible", True)]

    def _sort_presentation_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        priority = {
            "competition_final": 0,
            "standard_classroom": 1,
            "demo_data": 2,
            "historical_version": 3,
            "smoke_test": 4,
            "legacy_test_data": 5,
        }
        newest_first = sorted(items, key=lambda item: str(item.get("created_at") or item.get("generated_at") or ""), reverse=True)
        return sorted(
            newest_first,
            key=lambda item: priority.get((item.get("presentation_scope") or {}).get("record_kind") or item.get("record_kind"), 9),
        )

    def _record_frontstage_visible(self, record: Dict[str, Any]) -> bool:
        payload = record.get("payload") or {}
        summary = record.get("summary") or {}
        analysis_id = summary.get("analysis_id") or payload.get("analysis_id")
        return bool(self._presentation_scope(payload, analysis_id=analysis_id).get("frontend_visible", True))

    def _activity_score(self, payload: Dict[str, Any], timeline: Dict[str, Any], students: Dict[str, Any]) -> float:
        activity_curve = timeline.get("activity_curve") or []
        if activity_curve:
            values = [self._number_value(value) for value in activity_curve]
            avg = sum(values) / len(values)
            return avg * 100 if avg <= 1 else avg
        zones = (students.get("zones") or {}) if isinstance(students, dict) else {}
        zone_values = [
            self._number_value((zones.get(zone) or {}).get("active_ratio"))
            for zone in ["front", "middle", "back"]
            if (zones.get(zone) or {}).get("active_ratio") is not None
        ]
        if zone_values:
            avg = sum(zone_values) / len(zone_values)
            return avg * 100 if avg <= 1 else avg
        return 0.0

    def _ratio_value(self, value: Any) -> float:
        number = self._number_value(value)
        return number / 100.0 if number > 1 else number

    def _teacher_context(self, user_id: Optional[str]) -> Dict[str, Any]:
        if user_id is None:
            return {"id": None, "username": "demo_teacher", "display_name": "Demo Teacher", "role": "teacher"}
        return {"id": str(user_id), "user_id": str(user_id), "username": "teacher", "display_name": "Demo Teacher", "role": "teacher"}

    def _admin_context(self) -> Dict[str, Any]:
        return {"id": None, "username": "demo_admin", "display_name": "Demo Admin", "role": "admin"}

    def _teacher_metrics(self, items: List[Dict[str, Any]], classroom_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(items)
        recent_count = len([item for item in items if item.get("created_at")])
        status_counts = {"raw": 0, "reviewed": 0, "archived": 0}
        for item in items:
            status = item.get("status") or "raw"
            if status in status_counts:
                status_counts[status] += 1
        return {
            "classroom_count": len(classroom_summaries),
            "total_result_count": total,
            "recent_result_count": recent_count,
            "raw_count": status_counts["raw"],
            "reviewed_count": status_counts["reviewed"],
            "archived_count": status_counts["archived"],
            "avg_feedback_score": self._average_metric(items, "feedback_score"),
            "avg_attention_score": self._average_metric(items, "attention_score"),
            "avg_response_score": self._average_metric(items, "response_score"),
        }

    def _admin_metrics(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        status_counts = self._status_distribution(items)
        today = datetime.now().date().isoformat()
        classroom_ids = {item.get("classroom_id") for item in items if item.get("classroom_id")}
        teacher_ids = {item.get("teacher_id") for item in items if item.get("teacher_id")}
        return {
            "teacher_count": len(teacher_ids),
            "classroom_count": len(classroom_ids),
            "result_count": len(items),
            "recent_result_count": len([item for item in items if item.get("created_at")]),
            "today_result_count": len([item for item in items if str(item.get("created_at") or item.get("generated_at") or "").startswith(today)]),
            "raw_count": status_counts["raw"],
            "reviewed_count": status_counts["reviewed"],
            "archived_count": status_counts["archived"],
            "avg_feedback_score": self._average_metric(items, "feedback_score"),
            "avg_attention_score": self._average_metric(items, "attention_score"),
            "avg_response_score": self._average_metric(items, "response_score"),
        }

    def _admin_system_status(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        latest = items[0] if items else {}
        detail = self.get_workbench_result_detail(latest.get("analysis_id")) if latest.get("analysis_id") else None
        return {
            "cloud_service": "ok",
            "database": "ok",
            "latest_upload_at": latest.get("created_at") or latest.get("generated_at"),
            "latest_raw_path": (detail or {}).get("raw_path") or "",
            "latest_analysis_id": latest.get("analysis_id") or "",
        }

    def _admin_results_overview(self, items: List[Dict[str, Any]], total: int) -> Dict[str, Any]:
        low_attention = [
            item for item in items
            if self._item_metric_visible(item, "attention_score") and float(item.get("attention_score") or 0) < 75
        ]
        high_score = [item for item in items if float(item.get("feedback_score") or 0) >= 85]
        return {
            "result_count": total,
            "page_count": len(items),
            "status_distribution": self._status_distribution(items),
            "avg_feedback_score": self._average_metric(items, "feedback_score"),
            "avg_attention_score": self._average_metric(items, "attention_score"),
            "avg_response_score": self._average_metric(items, "response_score"),
            "high_score_count": len(high_score),
            "low_attention_count": len(low_attention),
            "tips": [
                {
                    "type": "high_score",
                    "title": "High-score classroom examples",
                    "description": f"{len(high_score)} result(s) on this page have feedback score >= 85.",
                    "target_url": "/admin/results",
                },
                {
                    "type": "low_attention",
                    "title": "Low-attention sessions",
                    "description": f"{len(low_attention)} result(s) on this page have attention score below 75.",
                    "target_url": "/admin/results",
                },
            ],
        }

    def _teacher_todo_items(self, metrics: Dict[str, Any], latest_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        todos: List[Dict[str, Any]] = []
        if metrics.get("raw_count", 0) > 0:
            todos.append({
                "type": "review",
                "title": "Review pending classroom analyses",
                "description": f"{metrics['raw_count']} raw result(s) are waiting for teacher review.",
                "target_url": "/teacher/results?status=raw",
            })
        low_attention = next((
            item for item in latest_results
            if self._item_metric_visible(item, "attention_score") and float(item.get("attention_score") or 0) < 75
        ), None)
        if low_attention:
            todos.append({
                "type": "attention",
                "title": "Check low attention session",
                "description": f"{low_attention.get('classroom_name')} has attention score below 75.",
                "target_url": low_attention.get("detail_url"),
            })
        high_quality = next((item for item in latest_results if float(item.get("feedback_score") or 0) >= 90), None)
        if high_quality:
            todos.append({
                "type": "highlight",
                "title": "Archive a high-quality classroom example",
                "description": f"{high_quality.get('lesson_title')} is suitable for teaching review.",
                "target_url": high_quality.get("detail_url"),
            })
        if not latest_results:
            todos.append({
                "type": "empty",
                "title": "Waiting for classroom analysis data",
                "description": "Upload or receive the first classroom analysis result to activate this console.",
                "target_url": "/teacher/results",
            })
        return todos

    def _average_metric(self, items: List[Dict[str, Any]], key: str) -> Optional[float]:
        values: List[float] = []
        for item in items:
            display_keys = {metric.get("key") for metric in item.get("display_metrics") or [] if isinstance(metric, dict)}
            metric_key = "feedback_score" if key == "score" else key
            if display_keys and metric_key in {"feedback_score", "attention_score", "response_score"} and metric_key not in display_keys:
                continue
            if item.get(key) is None:
                continue
            values.append(float(item.get(key) or 0))
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def _item_metric_visible(self, item: Dict[str, Any], key: str) -> bool:
        display_metrics = item.get("display_metrics") or []
        display_keys = {metric.get("key") for metric in display_metrics if isinstance(metric, dict)}
        metric_key = "feedback_score" if key == "score" else key
        return not display_keys or metric_key in display_keys

    def _status_distribution(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {"raw": 0, "reviewed": 0, "archived": 0}
        for item in items:
            status = item.get("status") or "raw"
            if status in counts:
                counts[status] += 1
        return counts

    def _append_metric_value(self, values: List[float], value: Any) -> None:
        if value in (None, ""):
            return
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            return

    def _average_values(self, values: List[float]) -> Optional[float]:
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def _normalize_days_value(self, days: Optional[int]) -> Optional[int]:
        if days is None:
            return None
        value = int(days)
        if value <= 0:
            return None
        if value <= 7:
            return 7
        if value <= 30:
            return 30
        return None

    def _freshness(self, value: Any) -> str:
        parsed = self._parse_datetime_value(value)
        if parsed is None:
            return "unknown"
        now = datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        age = now - parsed
        if age <= timedelta(days=1):
            return "online"
        if age <= timedelta(days=7):
            return "stale"
        return "offline"

    def _connect(self):
        return psycopg2.connect(self.database_url)

    def ensure_phase2_schema(self) -> None:
        if self._phase2_schema_checked:
            return
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS classroom_name TEXT;
                    ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS lesson_title TEXT;
                    ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'raw';
                    ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
                    ALTER TABLE analysis_results ALTER COLUMN classroom_id DROP NOT NULL;
                    UPDATE analysis_results SET status = 'raw' WHERE status IS NULL OR status = '';
                    UPDATE analysis_results SET updated_at = COALESCE(updated_at, created_at, now());
                    CREATE INDEX IF NOT EXISTS idx_analysis_results_status_created ON analysis_results(status, created_at DESC);
                    """
                )
        self._phase2_schema_checked = True

    def _row_to_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        payload = row["payload_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        summary = self.fallback_repository.summarize_result(payload)
        summary["analysis_id"] = summary.get("analysis_id") or row.get("analysis_id")
        summary["classroom_id"] = summary.get("classroom_id") or row.get("classroom_id") or "unknown"
        status = row.get("status") or "raw"
        summary["status"] = status
        summary["classroom_name"] = row.get("classroom_name")
        summary["lesson_title"] = row.get("lesson_title")
        summary["created_at"] = self._as_iso(row.get("created_at"))
        summary["updated_at"] = self._as_iso(row.get("updated_at"))
        return {
            "source_kind": row.get("source_kind") or "raw",
            "source_path": Path(row.get("source_path") or ""),
            "payload": payload,
            "summary": summary,
            "status": status,
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def _row_to_workbench_item(self, record: Dict[str, Any]) -> Dict[str, Any]:
        summary = record.get("summary") or {}
        return {
            "result_id": summary.get("analysis_id"),
            "analysis_id": summary.get("analysis_id"),
            "classroom_id": summary.get("classroom_id"),
            "classroom_name": summary.get("classroom_name") or summary.get("classroom_id") or "unknown",
            "lesson_title": summary.get("lesson_title") or summary.get("video_id") or "Untitled Lesson",
            "status": summary.get("status") or record.get("status") or "raw",
            "score": summary.get("feedback_score"),
            "feedback_score": summary.get("feedback_score"),
            "attention_score": summary.get("attention_score"),
            "response_score": summary.get("response_score"),
            "source_kind": record.get("source_kind") or "raw",
            "raw_path": str(record.get("source_path") or ""),
            "created_at": summary.get("created_at") or summary.get("generated_at"),
            "updated_at": summary.get("updated_at"),
        }

    def _row_to_workbench_detail(self, row: Dict[str, Any]) -> Dict[str, Any]:
        record = self._row_to_record(row)
        item = self._row_to_workbench_item(record)
        payload = record["payload"]
        summary = self._display_summary(payload, item)
        timeline = self._display_timeline(payload)
        stage_distribution = self._display_stage_distribution(payload)
        zones = self._display_zones(payload)
        events = self._display_events(payload)
        video = self._display_video(payload, item)
        display_scope = self._display_scope(payload)
        asr_display = self._asr_display(payload)
        data_quality_note = self._external_asr_data_quality_note(payload)
        display_flags = self._display_flags(payload, display_scope=display_scope, asr_display=asr_display)
        presentation_scope = self._presentation_scope(
            payload,
            analysis_id=item.get("analysis_id"),
            display_scope=display_scope,
            asr_display=asr_display,
            display_flags=display_flags,
        )
        item.update(
            {
                "teacher_name": payload.get("teacher_name") or "",
                "video": video,
                "summary": summary,
                "timeline": timeline,
                "stage_distribution": stage_distribution,
                "zones": zones,
                "events": events,
                "raw_path": str(record["source_path"]),
                "raw_payload": payload,
                "result": payload,
                "display_scope": display_scope,
                "asr_display": asr_display,
                "display_flags": display_flags,
                "presentation_scope": presentation_scope,
                "source_dataset": display_scope.get("source_dataset"),
                "sample_type": display_scope.get("sample_type"),
                "is_pi_capture": display_scope.get("is_pi_capture"),
                "is_own_capture": display_scope.get("is_own_capture"),
                "is_demo_playback_sample": display_scope.get("is_demo_playback_sample"),
                "is_final_dashboard_sample": display_scope.get("is_final_dashboard_sample"),
                "data_quality_note": data_quality_note,
            }
        )
        enhanced_fields = self._phase32_enhanced_fields(payload)
        if enhanced_fields:
            item.update(enhanced_fields)
            item["phase32"] = enhanced_fields
        question_guidance = self._phase33_question_guidance_fields(payload)
        if question_guidance:
            item.update(question_guidance)
            item["phase33"] = question_guidance
        if not item.get("classroom_name"):
            item["classroom_name"] = row.get("mapped_classroom_name") or item.get("classroom_id") or "unknown"
        return item

    def _phase32_enhanced_fields(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            "analysis_version",
            "algorithm_profile",
            "quality_metrics",
            "score_breakdown",
            "curve_metadata",
            "evidence_summary",
            "enhanced_events",
            "enhanced_issues",
        ]
        return {key: payload.get(key) for key in keys if payload.get(key) not in (None, "", [], {})}

    def _phase33_question_guidance_fields(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        keys = [
            "teacher_question_events",
            "question_guidance_summary",
        ]
        return {key: payload.get(key) for key in keys if payload.get(key) not in (None, "", [], {})}

    def _asr_display(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        audio = payload.get("audio") or {}
        asr_quality = payload.get("asr_quality") or {}
        evidence_summary = payload.get("evidence_summary") or {}
        summary = payload.get("summary") or {}
        transcript = payload.get("transcript") or []
        teacher = payload.get("teacher") or {}
        question_events = teacher.get("question_events") or payload.get("teacher_question_events") or []
        alignment = payload.get("interaction_alignment") or []

        transcript_segments = [segment for segment in transcript if isinstance(segment, dict)]
        question_items = [event for event in question_events if isinstance(event, dict)]
        alignment_items = [item for item in alignment if isinstance(item, dict)]
        response_by_event_id = {
            str(item.get("question_event_id") or item.get("event_id") or ""): item
            for item in alignment_items
        }
        response_detected_count = sum(1 for item in alignment_items if item.get("response_detected") is True)
        question_event_count = len(question_items)
        response_success_rate = self._number_value(
            summary.get("response_success_rate"),
            response_detected_count / question_event_count if question_event_count else None,
        )
        transcript_segment_count = int(self._number_value(
            audio.get("transcript_segment_count"),
            evidence_summary.get("transcript_segment_count"),
            len(transcript_segments),
        ))
        speaker_diarization = self._bool_or_none(asr_quality.get("speaker_diarization"))
        if speaker_diarization is None:
            speaker_diarization = False

        snippets = []
        for segment in transcript_segments:
            text = str(segment.get("text") or "").strip()
            if not text:
                continue
            snippets.append(
                {
                    "start_sec": self._number_value(segment.get("start_sec")),
                    "end_sec": self._number_value(segment.get("end_sec")),
                    "text": text,
                }
            )
            if len(snippets) >= 8:
                break

        display_questions = []
        for event in question_items[:5]:
            event_id = str(event.get("event_id") or event.get("id") or "")
            aligned = response_by_event_id.get(event_id) or {}
            display_questions.append(
                {
                    "event_id": event_id,
                    "start_sec": self._number_value(event.get("start_sec")),
                    "end_sec": self._number_value(event.get("end_sec")),
                    "text": str(event.get("text") or event.get("question_text") or "").strip(),
                    "confidence": event.get("confidence"),
                    "response_detected": bool(aligned.get("response_detected")) if aligned else False,
                }
            )

        transcript_present = bool(
            payload.get("has_asr_transcript")
            or audio.get("transcript_present")
            or evidence_summary.get("transcript_present")
            or transcript_segments
        )
        note = "提问事件基于本地 ASR 转写、规则检测与视觉响应对齐生成；当前未进行说话人分离，因此作为教师提问候选事件展示，不做精准教师身份判断。"
        if not transcript_present:
            note = "当前样本未提供课堂转写，语音相关指标仅作结构展示。"

        return {
            "transcript_present": transcript_present,
            "transcript_segment_count": transcript_segment_count,
            "asr_engine": audio.get("asr_engine") or "",
            "question_event_count": question_event_count,
            "alignment_count": len(alignment_items),
            "response_detected_count": response_detected_count,
            "response_success_rate": response_success_rate,
            "speaker_diarization": speaker_diarization,
            "teacher_identity_confidence": asr_quality.get("teacher_identity_confidence") or "low_without_diarization",
            "snippets": snippets,
            "question_events": display_questions,
            "note": note,
        }

    def _asr_summary_override(self, payload: Dict[str, Any], asr_display: Optional[Dict[str, Any]] = None) -> str:
        display = asr_display or self._asr_display(payload)
        if not display.get("transcript_present"):
            return ""
        question_count = int(self._number_value(display.get("question_event_count")))
        if question_count <= 0:
            return ""
        transcript_count = int(self._number_value(display.get("transcript_segment_count")))
        alignment_count = int(self._number_value(display.get("alignment_count")))
        response_count = int(self._number_value(display.get("response_detected_count")))
        return (
            f"本节课已完成本地 ASR 转写，生成 {transcript_count} 个转写片段，"
            f"识别出 {question_count} 个教师提问候选事件，并完成 {alignment_count} 条视觉响应对齐，"
            f"其中 {response_count} 条检测到学生响应。由于当前未进行说话人分离，提问事件作为候选结果展示。"
        )

    def _external_asr_data_quality_note(self, payload: Dict[str, Any]) -> str:
        display = self._asr_display(payload)
        source_dataset = self._text_value(
            payload.get("source_dataset"),
            (payload.get("capture") or {}).get("source_dataset"),
            (payload.get("source") or {}).get("source_dataset"),
        )
        sample_type = self._text_value(
            payload.get("sample_type"),
            (payload.get("capture") or {}).get("sample_type"),
            (payload.get("video") or {}).get("sample_type"),
        )
        if sample_type == "external_full_classroom_video_with_asr" or (
            source_dataset.upper() == "SAV" and display.get("transcript_present")
        ):
            return "该样本为外部 SAV ASR 增强演示样本，视觉专注度/阶段分布低置信度，不作为常规课堂质量排名依据。"
        return ""

    def _display_flags(
        self,
        payload: Dict[str, Any],
        display_scope: Optional[Dict[str, Any]] = None,
        asr_display: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        scope = display_scope or self._display_scope(payload)
        display = asr_display or self._asr_display(payload)
        timeline = payload.get("timeline") or {}
        students = payload.get("students") or {}
        zones = payload.get("zones") or students.get("zones") or {}
        stage_distribution = payload.get("stage_distribution") or (payload.get("teacher") or {}).get("stage_distribution") or {}

        source_dataset = str(scope.get("source_dataset") or "").upper()
        sample_type = str(scope.get("sample_type") or "")
        attention_curve = self._number_list(timeline.get("attention_curve"))
        heat_curve = self._number_list(timeline.get("heat_curve"))
        stage_values = [self._number_value(value) for value in stage_distribution.values()] if isinstance(stage_distribution, dict) else []
        zone_attention_values = [
            self._number_value((zones.get(zone_name) or {}).get("avg_attention_ratio"))
            for zone_name in ["front", "middle", "back"]
            if isinstance(zones, dict)
        ]
        estimated_student_count = self._number_value(students.get("estimated_student_count"), payload.get("estimated_student_count"))

        attention_unavailable = bool(attention_curve) and all(value == 0 for value in attention_curve)
        heat_unavailable = bool(heat_curve) and all(value == 0 for value in heat_curve)
        stage_unavailable = bool(stage_values) and all(value == 0 for value in stage_values)
        zone_attention_unavailable = bool(zone_attention_values) and all(value == 0 for value in zone_attention_values)
        student_count_unavailable = estimated_student_count == 0
        asr_sav_sample = bool(
            display.get("transcript_present")
            and self._number_value(display.get("question_event_count")) > 0
            and (sample_type == "external_full_classroom_video_with_asr" or source_dataset == "SAV")
        )

        hide_attention = asr_sav_sample and attention_unavailable
        return {
            "asr_trusted_metrics_only": asr_sav_sample,
            "hide_attention_metrics": hide_attention,
            "hide_avg_attention": hide_attention,
            "hide_attention_curve": hide_attention,
            "hide_region_attention": asr_sav_sample and zone_attention_unavailable,
            "hide_student_count": asr_sav_sample and student_count_unavailable,
            "hide_stage_distribution": asr_sav_sample and stage_unavailable,
            "hide_phase32_score_breakdown": asr_sav_sample,
            "hide_feedback_score_as_primary": asr_sav_sample,
            "visual_attention_low_confidence": asr_sav_sample and attention_unavailable and heat_unavailable,
            "visual_stage_low_confidence": asr_sav_sample and stage_unavailable,
        }

    def _display_scope(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        source = payload.get("source") or {}
        capture = payload.get("capture") or {}
        video = payload.get("video") or {}
        evidence_summary = payload.get("evidence_summary") or {}
        question_guidance = payload.get("question_guidance_summary") or {}
        phase37 = payload.get("phase37_final_dashboard_sample") or {}

        source_dataset = self._text_value(payload.get("source_dataset"), capture.get("source_dataset"), source.get("source_dataset"))
        sample_type = self._text_value(payload.get("sample_type"), capture.get("sample_type"), video.get("sample_type"))
        is_pi_capture = self._bool_or_none(payload.get("is_pi_capture"), capture.get("is_pi_capture"), source.get("is_pi_capture"))
        is_own_capture = self._bool_or_none(payload.get("is_own_capture"), capture.get("is_own_capture"), source.get("is_own_capture"))
        is_demo_playback_sample = self._bool_or_none(
            payload.get("is_demo_playback_sample"),
            capture.get("is_demo_playback_sample"),
            video.get("is_demo_playback_sample"),
        )
        is_final_dashboard_sample = self._bool_or_none(
            payload.get("is_final_dashboard_sample"),
            capture.get("is_final_dashboard_sample"),
            video.get("is_final_dashboard_sample"),
            phase37.get("final_dashboard_sample"),
        )
        if is_demo_playback_sample is None:
            is_demo_playback_sample = "cloud_playback_demo" in sample_type.lower()
        if is_final_dashboard_sample is None:
            is_final_dashboard_sample = False

        audio_present = self._bool_or_none(payload.get("audio_present"), evidence_summary.get("audio_present"))
        transcript = payload.get("transcript") or []
        transcript_present = self._bool_or_none(
            payload.get("transcript_present"),
            evidence_summary.get("transcript_present"),
            payload.get("has_asr_transcript"),
            True if transcript else None,
        )
        question_events = payload.get("teacher_question_events") or (payload.get("teacher") or {}).get("question_events") or []
        question_source = str(question_guidance.get("source") or "").lower()
        unsupported_metric_note = ""
        if source_dataset.upper() == "SAV" and transcript_present is True and question_events:
            unsupported_metric_note = "该外部视频样本未接入树莓派语音触发与说话人分离；课堂转写由本地离线 ASR 生成，提问事件作为候选结果展示。"
        elif source_dataset.upper() == "SAV" and (
            audio_present is False
            or transcript_present is False
            or not question_events
            or question_source in {"teacher_transcript_empty", "unavailable"}
        ):
            unsupported_metric_note = "该外部视频样本未提供有效课堂转写或提问证据，语音相关教学阶段和教师提问指标仅作结构展示，不作为主要评价依据。"

        final_sample_note = ""
        if is_final_dashboard_sample and source_dataset.upper() == "SAV" and is_pi_capture is False and is_own_capture is False:
            final_sample_note = "当前课堂样本来自 SAV 外部公开课堂视频，已由本地分析端处理并自动上传至云端；该样本用于完整课堂展示，不属于树莓派自采数据。"

        demo_playback_note = ""
        if is_demo_playback_sample or "cloud_playback_demo" in sample_type.lower():
            demo_playback_note = "该记录为播放链路 smoke test，不作为最终完整课堂分析展示样本。"

        return {
            "source_dataset": source_dataset,
            "source_label": "SAV 外部公开课堂视频" if source_dataset.upper() == "SAV" else source_dataset,
            "analysis_scope": "完整课堂分析" if is_final_dashboard_sample else ("播放链路 smoke test" if is_demo_playback_sample else "课堂分析"),
            "capture_label": "非树莓派采集 / 非自采" if is_pi_capture is False and is_own_capture is False else "采集来源按原始数据展示",
            "sample_type": sample_type,
            "is_final_dashboard_sample": bool(is_final_dashboard_sample),
            "is_demo_playback_sample": bool(is_demo_playback_sample),
            "is_pi_capture": is_pi_capture,
            "is_own_capture": is_own_capture,
            "final_sample_note": final_sample_note,
            "demo_playback_note": demo_playback_note,
            "unsupported_metric_note": unsupported_metric_note,
            "data_quality_note": self._external_asr_data_quality_note(payload),
            "no_sav50_mixed": bool(phase37.get("not_sav50_composite") or is_final_dashboard_sample),
        }

    def _display_summary(self, payload: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        summary = payload.get("summary") or {}
        asr_display = self._asr_display(payload)
        summary_text = self._asr_summary_override(payload, asr_display) or summary.get("summary_text") or payload.get("summary_text") or ""
        teacher_question_count = int(self._number_value(
            summary.get("teacher_question_count"),
            asr_display.get("question_event_count"),
            0,
        ))
        response_success_rate = self._number_value(
            summary.get("response_success_rate"),
            asr_display.get("response_success_rate"),
        )
        return {
            "feedback_score": self._number_value(summary.get("feedback_score"), item.get("score"), payload.get("overall_score")),
            "attention_score": self._number_value(summary.get("attention_score")),
            "response_score": self._number_value(summary.get("response_score")),
            "teacher_question_count": teacher_question_count,
            "avg_attention_ratio": self._number_value(summary.get("avg_attention_ratio")),
            "response_success_rate": response_success_rate,
            "summary_text": summary_text,
        }

    def _display_timeline(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timeline = payload.get("timeline") or {}
        return {
            "window_size_seconds": self._number_value(timeline.get("window_size_seconds"), 30),
            "attention_curve": self._number_list(timeline.get("attention_curve")),
            "activity_curve": self._number_list(timeline.get("activity_curve")),
            "heat_curve": self._number_list(timeline.get("heat_curve")),
        }

    def _display_stage_distribution(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        teacher = payload.get("teacher") or {}
        stage_distribution = payload.get("stage_distribution") or teacher.get("stage_distribution") or {}
        return {
            "exposition_ratio": self._number_value(stage_distribution.get("exposition_ratio")),
            "question_ratio": self._number_value(stage_distribution.get("question_ratio")),
            "discussion_ratio": self._number_value(stage_distribution.get("discussion_ratio")),
            "summary_ratio": self._number_value(stage_distribution.get("summary_ratio")),
            "management_ratio": self._number_value(stage_distribution.get("management_ratio")),
        }

    def _display_zones(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        students = payload.get("students") or {}
        zones = payload.get("zones") or students.get("zones") or {}
        return {
            zone_name: {
                "avg_attention_ratio": self._number_value((zones.get(zone_name) or {}).get("avg_attention_ratio")),
                "active_ratio": self._number_value((zones.get(zone_name) or {}).get("active_ratio")),
            }
            for zone_name in ["front", "middle", "back"]
        }

    def _display_events(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        teacher = payload.get("teacher") or {}
        teacher_question_events = teacher.get("question_events") or payload.get("teacher_question_events") or []
        asr_display = self._asr_display(payload)
        prefer_asr_questions = bool(asr_display.get("transcript_present") and teacher_question_events)
        raw_events = teacher_question_events if prefer_asr_questions else (
            payload.get("events")
            or payload.get("issues")
            or teacher_question_events
            or payload.get("question_events")
            or []
        )
        events: List[Dict[str, Any]] = []
        for index, event in enumerate(raw_events):
            if not isinstance(event, dict):
                continue
            if prefer_asr_questions:
                event_type = "question_candidate"
            else:
                event_type = (
                    event.get("event_type")
                    or event.get("type")
                    or event.get("category")
                    or event.get("question_type")
                    or "unknown"
                )
            events.append(
                {
                    "event_id": event.get("event_id") or f"event_{index + 1:03d}",
                    "event_type": event_type,
                    "question_type": event.get("question_type") or event_type,
                    "start_sec": self._number_value(event.get("start_sec")),
                    "end_sec": self._number_value(event.get("end_sec")),
                    "text": event.get("text") or event.get("description") or event.get("message") or "",
                    "raw_event": event,
                }
            )
        return events

    def _display_video(self, payload: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        source = payload.get("source") or {}
        video = payload.get("video") or {}
        time_info = payload.get("time") or {}
        explicit_video_url = video.get("video_url") or payload.get("video_url") or source.get("video_url") or ""
        demo_video_url, demo_video_path = self._demo_video_url()
        video_url = explicit_video_url or demo_video_url
        video_id = video.get("video_id") or payload.get("video_id") or item.get("lesson_title") or ""
        raw_video_path = (
            video.get("raw_video_path")
            or payload.get("raw_video_path")
            or source.get("source_path")
            or demo_video_path
            or ""
        )
        if video_url:
            video_status = "playable"
        elif video_id or raw_video_path:
            video_status = "pending"
        else:
            video_status = "missing"
        return {
            "status": video_status,
            "video_id": video_id,
            "video_url": video_url,
            "thumbnail_url": video.get("thumbnail_url") or payload.get("thumbnail_url") or "",
            "duration_seconds": self._number_value(video.get("duration_seconds"), time_info.get("duration_seconds")),
            "captured_at": video.get("captured_at") or time_info.get("recorded_at") or "",
            "device_id": video.get("device_id") or source.get("source_host") or "",
            "raw_video_path": raw_video_path,
        }

    def _demo_video_url(self) -> Tuple[str, str]:
        supported_suffixes = {".mp4", ".webm", ".mov", ".ogg"}
        candidates = [self.settings.video_upload_dir, Path("/root/video_project/upload")]
        for directory in candidates:
            preferred = directory / "video.mp4"
            if preferred.exists() and preferred.is_file():
                return "/uploads/video.mp4", str(preferred)
        discovered: List[Path] = []
        for directory in candidates:
            if not directory.exists() or not directory.is_dir():
                continue
            discovered.extend(
                path
                for path in directory.iterdir()
                if path.is_file() and path.suffix.lower() in supported_suffixes
            )
        if not discovered:
            return "", ""
        latest = max(discovered, key=lambda path: path.stat().st_mtime)
        return f"/uploads/{latest.name}", str(latest)

    def _extract_workbench_metadata(self, payload: Dict[str, Any], summary: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        source = payload.get("source") or {}
        classroom_name = payload.get("classroom_name") or summary.get("classroom_name")
        lesson_title = payload.get("lesson_title") or source.get("lesson_title") or payload.get("video_id")
        return self._as_text(classroom_name), self._as_text(lesson_title)

    def _normalize_status(self, status: Optional[str], allow_empty: bool) -> Optional[str]:
        if status in (None, ""):
            if allow_empty:
                return None
            raise ValueError("status is required")
        normalized = str(status).strip()
        if normalized not in {"raw", "reviewed", "archived"}:
            raise ValueError("status must be raw, reviewed, or archived")
        return normalized

    def _text_value(self, *values: Any) -> str:
        for value in values:
            if value not in (None, ""):
                return str(value)
        return ""

    def _bool_or_none(self, *values: Any) -> Optional[bool]:
        for value in values:
            if value in (None, ""):
                continue
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            text = str(value).strip().lower()
            if text in {"1", "true", "yes", "y", "on"}:
                return True
            if text in {"0", "false", "no", "n", "off"}:
                return False
        return None

    def _number_value(self, *values: Any) -> float:
        for value in values:
            if value in (None, ""):
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _number_list(self, values: Any) -> List[float]:
        if not isinstance(values, list):
            return []
        return [self._number_value(value) for value in values]

    def _as_datetime(self, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        return str(value)

    def _as_iso(self, value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _as_text(self, value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        return str(value)

    def _parse_datetime_value(self, value: Any) -> Optional[datetime]:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
