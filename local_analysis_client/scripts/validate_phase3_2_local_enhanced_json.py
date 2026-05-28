from __future__ import annotations

import json
import math
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
REQUIRED_SCORE_FIELDS = (
    "attention_score",
    "activity_score",
    "interaction_score",
    "rhythm_score",
    "evidence_score",
    "overall_score",
    "dominant_factor",
    "summary",
)
REQUIRED_QUALITY_FIELDS = (
    "data_confidence",
    "video_available",
    "frame_count",
    "valid_frame_count",
    "valid_frame_ratio",
    "low_confidence_windows",
    "missing_windows",
    "analysis_warnings",
)
REQUIRED_EVIDENCE_FIELDS = (
    "video_path_present",
    "standardized_video_present",
    "keyframe_count",
    "audio_present",
    "transcript_present",
    "detected_student_count_avg",
    "detected_teacher_count_avg",
    "evidence_level",
)
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_ISSUE_TYPES = {
    "low_attention",
    "low_interaction",
    "single_rhythm",
    "late_drop",
    "low_evidence",
}
SCORE_WEIGHTS = {
    "attention_score": 0.30,
    "activity_score": 0.20,
    "interaction_score": 0.20,
    "rhythm_score": 0.20,
    "evidence_score": 0.10,
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/validate_phase3_2_local_enhanced_json.py <path-to-result-json>")
        return 2

    payload = _load_json(Path(sys.argv[1]))
    markers = _validate(payload)
    for key in (
        "PHASE32_LOCAL_JSON_VALID",
        "PHASE32_ANALYSIS_VERSION_PRESENT",
        "PHASE32_SCORE_BREAKDOWN_VALID",
        "PHASE32_QUALITY_METRICS_VALID",
        "PHASE32_EVIDENCE_SUMMARY_VALID",
        "PHASE32_ENHANCED_ISSUES_VALID",
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
    analysis_version_present = payload.get("analysis_version") == "3.2"
    score_breakdown_valid = _validate_score_breakdown(payload.get("score_breakdown"))
    quality_metrics_valid = _validate_quality_metrics(payload.get("quality_metrics"))
    evidence_summary_valid = _validate_evidence_summary(payload.get("evidence_summary"))
    enhanced_issues_valid = _validate_enhanced_issues(payload.get("enhanced_issues"))
    local_json_valid = (
        bool(payload)
        and all(field in payload for field in REQUIRED_LEGACY_FIELDS)
        and isinstance(payload.get("algorithm_profile"), dict)
        and isinstance(payload.get("curve_metadata"), dict)
        and isinstance(payload.get("enhanced_events"), list)
        and analysis_version_present
        and score_breakdown_valid
        and quality_metrics_valid
        and evidence_summary_valid
        and enhanced_issues_valid
    )
    return {
        "PHASE32_LOCAL_JSON_VALID": local_json_valid,
        "PHASE32_ANALYSIS_VERSION_PRESENT": analysis_version_present,
        "PHASE32_SCORE_BREAKDOWN_VALID": score_breakdown_valid,
        "PHASE32_QUALITY_METRICS_VALID": quality_metrics_valid,
        "PHASE32_EVIDENCE_SUMMARY_VALID": evidence_summary_valid,
        "PHASE32_ENHANCED_ISSUES_VALID": enhanced_issues_valid,
    }


def _validate_score_breakdown(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not all(field in value for field in REQUIRED_SCORE_FIELDS):
        return False
    for field in SCORE_WEIGHTS:
        if not _is_score(value.get(field)):
            return False
    if not _is_score(value.get("overall_score")):
        return False
    expected = sum(float(value[field]) * weight for field, weight in SCORE_WEIGHTS.items())
    if math.fabs(float(value["overall_score"]) - expected) > 0.15:
        return False
    return str(value.get("dominant_factor")) in SCORE_WEIGHTS


def _validate_quality_metrics(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not all(field in value for field in REQUIRED_QUALITY_FIELDS):
        return False
    if value.get("data_confidence") not in ALLOWED_CONFIDENCE:
        return False
    if not isinstance(value.get("video_available"), bool):
        return False
    if not _is_non_negative_int(value.get("frame_count")):
        return False
    if not _is_non_negative_int(value.get("valid_frame_count")):
        return False
    if not _is_ratio(value.get("valid_frame_ratio")):
        return False
    if not _is_non_negative_int(value.get("low_confidence_windows")):
        return False
    if not _is_non_negative_int(value.get("missing_windows")):
        return False
    return isinstance(value.get("analysis_warnings"), list)


def _validate_evidence_summary(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not all(field in value for field in REQUIRED_EVIDENCE_FIELDS):
        return False
    for field in ("video_path_present", "standardized_video_present", "audio_present", "transcript_present"):
        if not isinstance(value.get(field), bool):
            return False
    if not _is_non_negative_int(value.get("keyframe_count")):
        return False
    if not _is_number(value.get("detected_student_count_avg")):
        return False
    if not _is_number(value.get("detected_teacher_count_avg")):
        return False
    return value.get("evidence_level") in ALLOWED_CONFIDENCE


def _validate_enhanced_issues(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for issue in value:
        if not isinstance(issue, dict):
            return False
        required = ("issue_id", "type", "label", "severity", "affected_stage", "reason", "evidence", "suggestion")
        if not all(issue.get(field) not in (None, "") for field in required):
            return False
        if issue.get("type") not in ALLOWED_ISSUE_TYPES:
            return False
        if issue.get("severity") not in {"low", "medium", "high"}:
            return False
        if not isinstance(issue.get("evidence"), dict):
            return False
    return True


def _is_score(value: Any) -> bool:
    return _is_number(value) and 0.0 <= float(value) <= 100.0


def _is_ratio(value: Any) -> bool:
    return _is_number(value) and 0.0 <= float(value) <= 1.0


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and value >= 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


if __name__ == "__main__":
    raise SystemExit(main())
