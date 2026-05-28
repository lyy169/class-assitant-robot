from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_LEGACY_FIELDS = (
    "schema_version",
    "analysis_id",
    "classroom_id",
    "video_id",
    "source",
    "time",
    "summary",
    "teacher",
    "students",
    "timeline",
)
REQUIRED_PHASE32_FIELDS = (
    "analysis_version",
    "algorithm_profile",
    "quality_metrics",
    "score_breakdown",
    "curve_metadata",
    "evidence_summary",
    "enhanced_events",
    "enhanced_issues",
)
REQUIRED_EVENT_FIELDS = (
    "question_id",
    "time_range",
    "text",
    "question_type",
    "confidence",
    "source",
)
REQUIRED_SUMMARY_FIELDS = (
    "status",
    "question_count",
    "open_question_count",
    "closed_question_count",
    "check_question_count",
    "questions_per_10min",
    "coverage",
    "guidance_score",
    "main_issue",
    "suggestion",
    "source",
)
VALID_STATUS = {"available", "unavailable", "demo"}
VALID_SOURCE = {"teacher_questions_json", "transcript_fallback", "demo_seed", "teacher_transcript_empty"}
VALID_QUESTION_TYPE = {"open", "closed", "check", "unknown"}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/validate_phase3_3_local_question_guidance.py <path-to-result-json>")
        return 2

    payload = _load_json(Path(sys.argv[1]))
    markers = _validate(payload)
    for key in (
        "PHASE33_LOCAL_JSON_VALID",
        "PHASE33_TEACHER_QUESTION_EVENTS_PRESENT",
        "PHASE33_GUIDANCE_SUMMARY_PRESENT",
        "PHASE33_GUIDANCE_SUMMARY_VALID",
        "PHASE33_UNAVAILABLE_FALLBACK_VALID",
    ):
        print(f"{key}={'true' if markers[key] else 'false'}")
    return 0 if all(markers.values()) else 1


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _validate(payload: dict[str, Any]) -> dict[str, bool]:
    events = payload.get("teacher_question_events")
    summary = payload.get("question_guidance_summary")
    summary_status = summary.get("status") if isinstance(summary, dict) else None
    events_present = isinstance(events, list) and (summary_status == "unavailable" or len(events) > 0)
    summary_present = isinstance(summary, dict)
    summary_valid = _validate_guidance_summary(summary, events if isinstance(events, list) else [])
    fallback_valid = summary_status in {"available", "demo"} or _validate_unavailable_summary(summary)
    local_valid = (
        bool(payload)
        and all(field in payload for field in REQUIRED_LEGACY_FIELDS)
        and all(field in payload for field in REQUIRED_PHASE32_FIELDS)
        and events_present
        and _validate_events(events if isinstance(events, list) else [], summary_status)
        and summary_present
        and summary_valid
        and fallback_valid
    )
    return {
        "PHASE33_LOCAL_JSON_VALID": local_valid,
        "PHASE33_TEACHER_QUESTION_EVENTS_PRESENT": events_present,
        "PHASE33_GUIDANCE_SUMMARY_PRESENT": summary_present,
        "PHASE33_GUIDANCE_SUMMARY_VALID": summary_valid,
        "PHASE33_UNAVAILABLE_FALLBACK_VALID": fallback_valid,
    }


def _validate_events(events: list[Any], summary_status: Any) -> bool:
    if summary_status == "unavailable" and not events:
        return True
    for event in events:
        if not isinstance(event, dict):
            return False
        if not all(event.get(field) not in (None, "") for field in REQUIRED_EVENT_FIELDS):
            return False
        if event.get("question_type") not in VALID_QUESTION_TYPE:
            return False
        if not _is_ratio(event.get("confidence")):
            return False
        if event.get("source") not in VALID_SOURCE:
            return False
        time_range = event.get("time_range")
        if not isinstance(time_range, dict):
            return False
        if not _is_number(time_range.get("start")) or not _is_number(time_range.get("end")):
            return False
        if time_range.get("end") < time_range.get("start"):
            return False
        if not time_range.get("display"):
            return False
        response_signal = event.get("response_signal")
        if response_signal is not None and not _validate_response_signal(response_signal):
            return False
    return True


def _validate_guidance_summary(summary: Any, events: list[Any]) -> bool:
    if not isinstance(summary, dict):
        return False
    if summary.get("status") == "unavailable":
        return _validate_unavailable_summary(summary)
    if not all(field in summary for field in REQUIRED_SUMMARY_FIELDS):
        return False
    if summary.get("status") not in VALID_STATUS:
        return False
    if summary.get("source") not in VALID_SOURCE:
        return False
    if not _is_non_negative_int(summary.get("question_count")):
        return False
    if summary.get("question_count") != len(events):
        return False
    for field in ("open_question_count", "closed_question_count", "check_question_count"):
        if not _is_non_negative_int(summary.get(field)):
            return False
    if not _is_number(summary.get("questions_per_10min")) or summary.get("questions_per_10min") < 0:
        return False
    if not _validate_coverage(summary.get("coverage")):
        return False
    if not _is_score(summary.get("guidance_score")):
        return False
    if not summary.get("main_issue") or not summary.get("suggestion"):
        return False
    score_parts = summary.get("score_parts")
    if score_parts is not None and not _validate_score_parts(score_parts):
        return False
    return True


def _validate_unavailable_summary(summary: Any) -> bool:
    if not isinstance(summary, dict):
        return False
    if summary.get("status") != "unavailable":
        return False
    if summary.get("question_count") != 0:
        return False
    if summary.get("guidance_score") is not None:
        return False
    if summary.get("source") not in VALID_SOURCE:
        return False
    return bool(summary.get("main_issue") and summary.get("suggestion"))


def _validate_response_signal(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        _is_number(value.get("activity_delta"))
        and _is_number(value.get("attention_delta"))
        and _is_non_negative_int(value.get("nearby_event_count"))
    )


def _validate_coverage(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return all(_is_non_negative_int(value.get(key)) for key in ("early", "middle", "late"))


def _validate_score_parts(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    required = (
        "question_count_score",
        "coverage_score",
        "open_question_score",
        "response_signal_score",
        "source_confidence_score",
    )
    return all(_is_score(value.get(key)) for key in required)


def _is_score(value: Any) -> bool:
    return _is_number(value) and 0 <= float(value) <= 100


def _is_ratio(value: Any) -> bool:
    return _is_number(value) and 0 <= float(value) <= 1


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and value >= 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


if __name__ == "__main__":
    raise SystemExit(main())
