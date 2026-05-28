from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Callable


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
TARGET_TOTALS = {
    "question_interaction": 25,
    "classroom_routine_standing": 15,
    "attention_learning_state": 10,
}
NEW_TARGETS = {
    "question_interaction": 17,
    "classroom_routine_standing": 7,
    "attention_learning_state": 10,
}
CATEGORY_CN = {
    "question_interaction": "课堂互动型",
    "classroom_routine_standing": "课堂流程型",
    "attention_learning_state": "注意力/学习状态型",
}
OUTPUT_FIELDS = (
    "dataset_order",
    "clip_id",
    "source_video_id",
    "split",
    "clip_index",
    "start_sec",
    "end_sec",
    "person_count",
    "sit_count",
    "stand_count",
    "look_forward_count",
    "look_sideways_count",
    "read_count",
    "flip_books_count",
    "touch_sth_count",
    "raise_hand_count",
    "hands_down_count",
    "take_notes_count",
    "applaud_count",
    "bend_count",
    "turn_around_count",
    "talk_with_others_count",
    "answer_questions_count",
    "target_action_names",
    "phase34_category",
    "phase34_category_cn",
    "candidate_origin",
    "selection_reason",
    "manual_review_status",
    "selected_for_phase34",
    "source_name",
    "source_type",
    "data_mode",
    "is_demo",
    "is_own_capture",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Select SAV-50 candidate clips for Phase 3.4b.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--target-csv", type=Path, default=None)
    parser.add_argument("--manual-review-csv", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    target_csv = args.target_csv.resolve() if args.target_csv else reports_dir / "sav_target_candidate_clips.csv"
    manual_review_csv = args.manual_review_csv.resolve() if args.manual_review_csv else reports_dir / "manual_review_results.csv"
    output_csv = args.output_csv.resolve() if args.output_csv else reports_dir / "selected_sav50_candidates.csv"
    summary_json = args.summary_json.resolve() if args.summary_json else reports_dir / "selected_sav50_summary.json"

    if not target_csv.exists() or not manual_review_csv.exists():
        print(f"PHASE34_SAV50_TARGET_CSV_PRESENT={_bool_text(target_csv.exists())}")
        print(f"PHASE34_SAV50_MANUAL_REVIEW_PRESENT={_bool_text(manual_review_csv.exists())}")
        print("PHASE34_SAV50_WRITTEN=false")
        return 1

    target_rows = _read_rows(target_csv)
    manual_rows = _read_rows(manual_review_csv)
    target_by_clip = {str(row.get("clip_id") or ""): row for row in target_rows}
    selected_clip_ids: set[str] = set()
    source_counts: Counter[str] = Counter()
    output_rows: list[dict[str, str]] = []

    for manual_row in manual_rows:
        clip_id = str(manual_row.get("clip_id") or "")
        target_row = target_by_clip.get(clip_id, {})
        category = str(manual_row.get("manual_category") or "")
        output_rows.append(
            _build_output_row(
                dataset_order=len(output_rows) + 1,
                row={**target_row, **_manual_time_fields(manual_row)},
                category=category,
                candidate_origin="sav16_manual_reviewed",
                selection_reason=str(manual_row.get("manual_summary") or CATEGORY_CN.get(category, "")),
                manual_review_status=str(manual_row.get("manual_review_status") or "classified"),
                selected_for_phase34="yes",
                notes="SAV-16 已人工复核基础样本。",
            )
        )
        selected_clip_ids.add(clip_id)
        source_counts[str(manual_row.get("source_video_id") or target_row.get("source_video_id") or "")] += 1

    new_rows: list[dict[str, str]] = []
    category_specs = (
        ("question_interaction", _is_question_interaction, _question_sort_key, "新增课堂互动型候选：举手/回答/讨论行为优先。"),
        ("classroom_routine_standing", _is_routine_standing, _routine_sort_key, "新增课堂流程型候选：群体站立且无举手行为优先。"),
        ("attention_learning_state", _is_attention_state_strict, _attention_sort_key, "新增注意力/学习状态型候选：弯腰、侧看、回头、记笔记、阅读等行为优先。"),
    )
    for category, predicate, sort_key, reason in category_specs:
        selected = _select_new_candidates(
            rows=target_rows,
            category=category,
            target_count=NEW_TARGETS[category],
            predicate=predicate,
            sort_key=sort_key,
            selected_clip_ids=selected_clip_ids,
            source_counts=source_counts,
            selection_reason=reason,
        )
        if category == "attention_learning_state" and len(selected) < NEW_TARGETS[category]:
            selected.extend(
                _select_new_candidates(
                    rows=target_rows,
                    category=category,
                    target_count=NEW_TARGETS[category] - len(selected),
                    predicate=_is_attention_state_relaxed,
                    sort_key=_attention_sort_key,
                    selected_clip_ids=selected_clip_ids,
                    source_counts=source_counts,
                    selection_reason=reason,
                    extra_note="attention_raise_hand_limit_relaxed",
                )
            )
        new_rows.extend(selected)

    for row in new_rows:
        row["dataset_order"] = str(len(output_rows) + 1)
        output_rows.append(row)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_rows(output_csv, output_rows)
    summary = _build_summary(output_rows)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PHASE34_SAV50_OUTPUT_CSV={output_csv}")
    print(f"PHASE34_SAV50_SUMMARY_JSON={summary_json}")
    print(f"PHASE34_SAV50_TOTAL_COUNT={len(output_rows)}")
    print(f"PHASE34_SAV50_EXISTING_COUNT={sum(1 for row in output_rows if row.get('candidate_origin') == 'sav16_manual_reviewed')}")
    print(f"PHASE34_SAV50_NEW_COUNT={sum(1 for row in output_rows if row.get('candidate_origin') == 'sav50_auto_selected')}")
    print(f"PHASE34_SAV50_INTERACTION_COUNT={sum(1 for row in output_rows if row.get('phase34_category') == 'question_interaction')}")
    print(f"PHASE34_SAV50_ROUTINE_COUNT={sum(1 for row in output_rows if row.get('phase34_category') == 'classroom_routine_standing')}")
    print(f"PHASE34_SAV50_ATTENTION_COUNT={sum(1 for row in output_rows if row.get('phase34_category') == 'attention_learning_state')}")
    print(f"PHASE34_SAV50_WRITTEN={_bool_text(output_csv.exists() and summary_json.exists())}")
    return 0 if len(output_rows) == 50 and output_csv.exists() and summary_json.exists() else 1


def _select_new_candidates(
    *,
    rows: list[dict[str, str]],
    category: str,
    target_count: int,
    predicate: Callable[[dict[str, str]], bool],
    sort_key: Callable[[dict[str, str]], tuple[int, ...]],
    selected_clip_ids: set[str],
    source_counts: Counter[str],
    selection_reason: str,
    extra_note: str = "",
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    notes_for_relaxed_limit = ""
    for source_limit in (3, 5):
        if source_limit == 5:
            notes_for_relaxed_limit = "source_video_limit_relaxed"
        candidates = sorted(
            (
                row
                for row in rows
                if predicate(row)
                and str(row.get("clip_id") or "") not in selected_clip_ids
                and source_counts[str(row.get("source_video_id") or "")] < source_limit
            ),
            key=sort_key,
        )
        for row in candidates:
            if len(selected) >= target_count:
                return selected
            clip_id = str(row.get("clip_id") or "")
            source_video_id = str(row.get("source_video_id") or "")
            if clip_id in selected_clip_ids or source_counts[source_video_id] >= source_limit:
                continue
            note_parts = [part for part in (notes_for_relaxed_limit, extra_note) if part]
            selected.append(
                _build_output_row(
                    dataset_order=0,
                    row=row,
                    category=category,
                    candidate_origin="sav50_auto_selected",
                    selection_reason=selection_reason,
                    manual_review_status="pending",
                    selected_for_phase34="pending_manual_review",
                    notes=";".join(note_parts),
                )
            )
            selected_clip_ids.add(clip_id)
            source_counts[source_video_id] += 1
    return selected


def _build_output_row(
    *,
    dataset_order: int,
    row: dict[str, str],
    category: str,
    candidate_origin: str,
    selection_reason: str,
    manual_review_status: str,
    selected_for_phase34: str,
    notes: str,
) -> dict[str, str]:
    result = {field: "" for field in OUTPUT_FIELDS}
    for field in OUTPUT_FIELDS:
        if field in row:
            result[field] = str(row.get(field) or "")
    result.update(
        {
            "dataset_order": str(dataset_order),
            "phase34_category": category,
            "phase34_category_cn": CATEGORY_CN.get(category, ""),
            "candidate_origin": candidate_origin,
            "selection_reason": selection_reason,
            "manual_review_status": manual_review_status,
            "selected_for_phase34": selected_for_phase34,
            "source_name": "SAV",
            "source_type": "public_dataset",
            "data_mode": "external_real_clip",
            "is_demo": "false",
            "is_own_capture": "false",
            "notes": notes,
        }
    )
    return result


def _manual_time_fields(row: dict[str, str]) -> dict[str, str]:
    return {
        "start_sec": str(row.get("official_start_sec") or ""),
        "end_sec": str(row.get("official_end_sec") or ""),
    }


def _build_summary(rows: list[dict[str, str]]) -> dict[str, object]:
    source_counts = Counter(str(row.get("source_video_id") or "") for row in rows)
    category_counts = Counter(str(row.get("phase34_category") or "") for row in rows)
    return {
        "total_count": len(rows),
        "existing_sav16_count": sum(1 for row in rows if row.get("candidate_origin") == "sav16_manual_reviewed"),
        "new_candidate_count": sum(1 for row in rows if row.get("candidate_origin") == "sav50_auto_selected"),
        "question_interaction_count": category_counts["question_interaction"],
        "classroom_routine_standing_count": category_counts["classroom_routine_standing"],
        "attention_learning_state_count": category_counts["attention_learning_state"],
        "unique_source_video_count": len(source_counts),
        "source_video_max_candidate_count": max(source_counts.values()) if source_counts else 0,
        "notes": [
            "SAV-50 candidate list only; no download, clipping, upload, or local analysis was executed.",
            "SAV rows are marked external_real_clip / public_dataset / not demo / not own capture.",
        ],
    }


def _is_question_interaction(row: dict[str, str]) -> bool:
    return _int(row, "raise_hand_count") > 0 or _int(row, "answer_questions_count") > 0 or _int(row, "talk_with_others_count") > 0


def _is_routine_standing(row: dict[str, str]) -> bool:
    return _int(row, "stand_count") >= 10 and _int(row, "raise_hand_count") == 0


def _is_attention_state_strict(row: dict[str, str]) -> bool:
    return _is_attention_state_relaxed(row) and _int(row, "raise_hand_count") <= 5


def _is_attention_state_relaxed(row: dict[str, str]) -> bool:
    return (
        _int(row, "bend_count") > 0
        or _int(row, "look_sideways_count") >= 8
        or _int(row, "turn_around_count") > 0
        or _int(row, "take_notes_count") > 0
        or _int(row, "read_count") > 0
    )


def _question_sort_key(row: dict[str, str]) -> tuple[int, ...]:
    return (
        -_int(row, "raise_hand_count"),
        -_int(row, "answer_questions_count"),
        -_int(row, "talk_with_others_count"),
        -_int(row, "person_count"),
        _int(row, "clip_index"),
    )


def _routine_sort_key(row: dict[str, str]) -> tuple[int, ...]:
    return (
        -_int(row, "stand_count"),
        -_int(row, "person_count"),
        -_int(row, "answer_questions_count"),
        _int(row, "clip_index"),
    )


def _attention_sort_key(row: dict[str, str]) -> tuple[int, ...]:
    return (
        -_int(row, "bend_count"),
        -_int(row, "look_sideways_count"),
        -_int(row, "turn_around_count"),
        -_int(row, "take_notes_count"),
        -_int(row, "read_count"),
        -_int(row, "person_count"),
        _int(row, "clip_index"),
    )


def _int(row: dict[str, str], key: str) -> int:
    try:
        return int(float(str(row.get(key) or "0")))
    except ValueError:
        return 0


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in OUTPUT_FIELDS})


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
