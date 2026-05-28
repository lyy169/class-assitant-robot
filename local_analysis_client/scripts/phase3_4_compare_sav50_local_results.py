from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")

COMPARISON_FIELDS = (
    "clip_id",
    "final_phase34_category",
    "final_phase34_category_cn",
    "sav_stand_count",
    "sav_raise_hand_count",
    "sav_bend_count",
    "sav_talk_with_others_count",
    "sav_answer_questions_count",
    "human_summary",
    "local_result_present",
    "local_detected_standing",
    "local_detected_raise_hand",
    "local_detected_event_count",
    "local_score",
    "stand_expected",
    "raise_hand_expected",
    "stand_matched",
    "raise_hand_matched",
    "comparison_status",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare SAV-50 official/human labels with local analysis results.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--review-csv", type=Path, default=None)
    parser.add_argument("--analysis-results-dir", type=Path, default=None)
    parser.add_argument("--comparison-csv", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    review_csv = args.review_csv.resolve() if args.review_csv else reports_dir / "final_sav50_manual_review_results.csv"
    analysis_results_dir = args.analysis_results_dir.resolve() if args.analysis_results_dir else sav_root / "analysis_results"
    comparison_csv = args.comparison_csv.resolve() if args.comparison_csv else reports_dir / "sav50_local_comparison.csv"
    summary_json = args.summary_json.resolve() if args.summary_json else reports_dir / "sav50_local_comparison_summary.json"

    review_rows = _read_rows(review_csv) if review_csv.exists() else []
    comparison_rows = [
        _build_comparison_row(review_row=row, analysis_results_dir=analysis_results_dir)
        for row in sorted(review_rows, key=_dataset_order_key)
    ]
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(comparison_csv, comparison_rows)
    summary = _build_summary(comparison_rows)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PHASE34_SAV50_COMPARISON_FILE_PRESENT={_bool_text(comparison_csv.exists())}")
    print(f"PHASE34_SAV50_COMPARISON_TOTAL_COUNT={len(comparison_rows)}")
    print(f"PHASE34_SAV50_LOCAL_RESULT_COUNT={summary['local_result_count']}")
    print(f"PHASE34_SAV50_STAND_EXPECTED_COUNT={summary['stand_expected_count']}")
    print(f"PHASE34_SAV50_STAND_MATCHED_COUNT={summary['stand_matched_count']}")
    print(f"PHASE34_SAV50_RAISE_HAND_EXPECTED_COUNT={summary['raise_hand_expected_count']}")
    print(f"PHASE34_SAV50_RAISE_HAND_MATCHED_COUNT={summary['raise_hand_matched_count']}")
    print(f"PHASE34_SAV50_COMPARISON_OK={_bool_text(comparison_csv.exists() and summary_json.exists() and len(comparison_rows) == 50)}")
    return 0 if comparison_csv.exists() and summary_json.exists() and len(comparison_rows) == 50 else 1


def _build_comparison_row(*, review_row: dict[str, str], analysis_results_dir: Path) -> dict[str, str]:
    clip_id = str(review_row.get("clip_id") or "")
    result_path = analysis_results_dir / f"{clip_id}.json"
    payload = _read_json(result_path) if result_path.exists() else {}
    notes: list[str] = []
    local = _extract_local_signals(payload, notes=notes)
    category = str(review_row.get("final_phase34_category") or "")
    sav_stand_count = _safe_int(review_row.get("stand_count"))
    sav_raise_hand_count = _safe_int(review_row.get("raise_hand_count"))
    stand_expected = sav_stand_count > 0 or "classroom_routine" in category
    raise_hand_expected = sav_raise_hand_count > 0 or category == "question_interaction"
    stand_matched = (not stand_expected) or local["detected_standing"]
    raise_hand_matched = (not raise_hand_expected) or local["detected_raise_hand"]
    local_result_present = bool(payload)
    comparison_status = "compared" if local_result_present else "local_result_missing"
    if local_result_present and notes:
        comparison_status = "compared_with_inference"

    return {
        "clip_id": clip_id,
        "final_phase34_category": category,
        "final_phase34_category_cn": str(review_row.get("final_phase34_category_cn") or ""),
        "sav_stand_count": str(sav_stand_count),
        "sav_raise_hand_count": str(sav_raise_hand_count),
        "sav_bend_count": str(_safe_int(review_row.get("bend_count"))),
        "sav_talk_with_others_count": str(_safe_int(review_row.get("talk_with_others_count"))),
        "sav_answer_questions_count": str(_safe_int(review_row.get("answer_questions_count"))),
        "human_summary": str(review_row.get("manual_summary") or ""),
        "local_result_present": _bool_text(local_result_present),
        "local_detected_standing": _bool_text(local["detected_standing"]),
        "local_detected_raise_hand": _bool_text(local["detected_raise_hand"]),
        "local_detected_event_count": str(local["event_count"]),
        "local_score": _format_score(local["score"]),
        "stand_expected": _bool_text(stand_expected),
        "raise_hand_expected": _bool_text(raise_hand_expected),
        "stand_matched": _bool_text(stand_matched),
        "raise_hand_matched": _bool_text(raise_hand_matched),
        "comparison_status": comparison_status,
        "notes": ";".join(notes),
    }


def _extract_local_signals(payload: dict[str, Any], *, notes: list[str]) -> dict[str, Any]:
    if not payload:
        return {"detected_standing": False, "detected_raise_hand": False, "event_count": 0, "score": ""}
    students = payload.get("students") if isinstance(payload.get("students"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    timeline = payload.get("timeline") if isinstance(payload.get("timeline"), dict) else {}
    enhanced_events = payload.get("enhanced_events") if isinstance(payload.get("enhanced_events"), list) else []

    hand_count = _safe_int(students.get("hand_raise_event_count"))
    active_values = [_safe_float(value) for value in timeline.get("activity_curve", [])] if isinstance(timeline.get("activity_curve"), list) else []
    active_values = [value for value in active_values if value is not None]
    active_window_count = sum(1 for value in active_values if value > 0)
    summary_text = str(summary.get("summary_text") or "")

    detected_raise_hand = hand_count > 0 or _text_mentions_raise_hand(summary_text) or _events_mention_raise_hand(enhanced_events)
    detected_standing = _result_has_direct_standing(payload)
    if not detected_standing and active_window_count > 0:
        detected_standing = True
        notes.append("standing_inferred_from_activity_curve_no_direct_standing_field")
    if detected_raise_hand and hand_count == 0:
        notes.append("raise_hand_inferred_from_text_or_events")

    direct_event_count = _sum_direct_event_counts(payload)
    event_count = max(hand_count + active_window_count, direct_event_count)
    score = summary.get("feedback_score")
    if score in (None, "") and isinstance(payload.get("score_breakdown"), dict):
        score = payload["score_breakdown"].get("overall_score")
    return {
        "detected_standing": detected_standing,
        "detected_raise_hand": detected_raise_hand,
        "event_count": int(event_count),
        "score": score,
    }


def _result_has_direct_standing(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in {"standing_count", "stand_count"} and _safe_int(item) > 0:
                return True
            if normalized in {"standing", "stand"} and isinstance(item, bool) and item:
                return True
            if _result_has_direct_standing(item):
                return True
    elif isinstance(value, list):
        return any(_result_has_direct_standing(item) for item in value)
    return False


def _sum_direct_event_counts(value: Any) -> int:
    total = 0
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in {"standing_count", "stand_count", "hand_raise_event_count", "hand_raising_count"}:
                total += _safe_int(item)
            elif isinstance(item, (dict, list)):
                total += _sum_direct_event_counts(item)
    elif isinstance(value, list):
        for item in value:
            total += _sum_direct_event_counts(item)
    return total


def _events_mention_raise_hand(events: list[Any]) -> bool:
    text = json.dumps(events, ensure_ascii=False).lower()
    return any(token in text for token in ("raise_hand", "hand_raise", "hand-raise", "举手"))


def _text_mentions_raise_hand(text: str) -> bool:
    normalized = text.lower()
    return any(token in normalized for token in ("raise_hand", "hand raise", "hand-raise", "举手"))


def _build_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    local_result_count = sum(1 for row in rows if row.get("local_result_present") == "true")
    stand_expected_count = sum(1 for row in rows if row.get("stand_expected") == "true")
    stand_matched_count = sum(1 for row in rows if row.get("stand_expected") == "true" and row.get("stand_matched") == "true")
    raise_hand_expected_count = sum(1 for row in rows if row.get("raise_hand_expected") == "true")
    raise_hand_matched_count = sum(
        1 for row in rows if row.get("raise_hand_expected") == "true" and row.get("raise_hand_matched") == "true"
    )
    return {
        "total_count": len(rows),
        "local_result_count": local_result_count,
        "stand_expected_count": stand_expected_count,
        "stand_matched_count": stand_matched_count,
        "raise_hand_expected_count": raise_hand_expected_count,
        "raise_hand_matched_count": raise_hand_matched_count,
        "comparison_scope": "stand_and_raise_hand",
        "notes": "local_detected_standing uses direct standing fields when available; otherwise it records activity-curve inference because the current aggregate result does not expose standing_count directly.",
    }


def _dataset_order_key(row: dict[str, str]) -> tuple[int, str]:
    try:
        return (int(str(row.get("dataset_order") or "0")), str(row.get("clip_id") or ""))
    except ValueError:
        return (0, str(row.get("clip_id") or ""))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COMPARISON_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in COMPARISON_FIELDS})


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def _safe_float(value: Any) -> float | None:
    try:
        return float(str(value))
    except ValueError:
        return None


def _format_score(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
