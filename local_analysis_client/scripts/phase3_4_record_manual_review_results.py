from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")

INTERACTION_CLIP_IDS = {
    "20200908_17_494",
    "20220910_09_885",
    "20220207_22_536",
    "20230429_13_405",
    "20220218_01_4",
    "20220804_20_2",
    "20221210_07_975",
    "20220902_08_9",
}
ROUTINE_CLIP_IDS = {
    "20230429_13_331",
    "20201123_07_705",
    "20211231_15_276",
    "20230601_08_31",
    "20220822_08_1098",
    "20230420_31_3",
    "20230430_15_1346",
    "20220314_02_3",
}
OUTPUT_FIELDS = (
    "review_order",
    "clip_id",
    "source_video_id",
    "manual_clip_path",
    "manual_clip_exists",
    "official_start_sec",
    "official_end_sec",
    "clip_start_sec",
    "clip_end_sec",
    "person_count",
    "stand_count",
    "raise_hand_count",
    "look_forward_count",
    "look_sideways_count",
    "talk_with_others_count",
    "answer_questions_count",
    "target_action_names",
    "manual_category",
    "manual_category_cn",
    "manual_review_status",
    "selected_for_phase34",
    "manual_summary",
    "teaching_interpretation",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Phase 3.4 SAV manual review classification results.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--clip-status-csv", type=Path, default=None)
    parser.add_argument("--selected-csv", type=Path, default=None)
    parser.add_argument("--manual-clips-dir", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    clip_status_csv = args.clip_status_csv.resolve() if args.clip_status_csv else reports_dir / "clip_download_status.csv"
    selected_csv = args.selected_csv.resolve() if args.selected_csv else reports_dir / "selected_sav_candidates.csv"
    manual_clips_dir = args.manual_clips_dir.resolve() if args.manual_clips_dir else sav_root / "manual_clips"
    output_csv = args.output_csv.resolve() if args.output_csv else reports_dir / "manual_review_results.csv"

    if not clip_status_csv.exists() or not selected_csv.exists():
        print(f"PHASE34_MANUAL_REVIEW_CLIP_STATUS_PRESENT={_bool_text(clip_status_csv.exists())}")
        print(f"PHASE34_MANUAL_REVIEW_SELECTED_CSV_PRESENT={_bool_text(selected_csv.exists())}")
        print("PHASE34_MANUAL_REVIEW_WRITTEN=false")
        return 1

    clip_status_rows = _read_rows(clip_status_csv)
    selected_rows = _read_rows(selected_csv)
    selected_by_clip = {str(row.get("clip_id") or "").strip(): row for row in selected_rows}
    manual_clip_paths = {path.stem: path for path in manual_clips_dir.glob("*.mp4")} if manual_clips_dir.exists() else {}

    output_rows = [
        _build_review_row(
            review_order=index,
            status_row=status_row,
            selected_row=selected_by_clip.get(str(status_row.get("clip_id") or "").strip(), {}),
            manual_clip_paths=manual_clip_paths,
        )
        for index, status_row in enumerate(clip_status_rows, start=1)
    ]

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_rows(output_csv, output_rows)

    interaction_count = sum(1 for row in output_rows if row.get("manual_category") == "question_interaction")
    routine_count = sum(1 for row in output_rows if row.get("manual_category") == "classroom_routine_standing")
    print(f"PHASE34_MANUAL_REVIEW_OUTPUT_CSV={output_csv}")
    print(f"PHASE34_MANUAL_REVIEW_TOTAL_COUNT={len(output_rows)}")
    print(f"PHASE34_MANUAL_REVIEW_INTERACTION_COUNT={interaction_count}")
    print(f"PHASE34_MANUAL_REVIEW_ROUTINE_COUNT={routine_count}")
    print(f"PHASE34_MANUAL_REVIEW_WRITTEN={_bool_text(output_csv.exists())}")
    return 0 if output_csv.exists() and len(output_rows) == 16 else 1


def _build_review_row(
    *,
    review_order: int,
    status_row: dict[str, str],
    selected_row: dict[str, str],
    manual_clip_paths: dict[str, Path],
) -> dict[str, str]:
    clip_id = str(status_row.get("clip_id") or "").strip()
    category = _manual_category_for_clip(clip_id)
    manual_clip_path = Path(str(status_row.get("manual_clip_path") or ""))
    if clip_id in manual_clip_paths:
        manual_clip_path = manual_clip_paths[clip_id]
    manual_clip_exists = manual_clip_path.exists()
    summary, interpretation, category_cn = _category_text(category)

    return {
        "review_order": str(review_order),
        "clip_id": clip_id,
        "source_video_id": str(status_row.get("source_video_id") or ""),
        "manual_clip_path": str(manual_clip_path),
        "manual_clip_exists": _bool_text(manual_clip_exists),
        "official_start_sec": str(status_row.get("official_start_sec") or ""),
        "official_end_sec": str(status_row.get("official_end_sec") or ""),
        "clip_start_sec": str(status_row.get("clip_start_sec") or ""),
        "clip_end_sec": str(status_row.get("clip_end_sec") or ""),
        "person_count": str(selected_row.get("person_count") or ""),
        "stand_count": str(selected_row.get("stand_count") or ""),
        "raise_hand_count": str(selected_row.get("raise_hand_count") or ""),
        "look_forward_count": str(selected_row.get("look_forward_count") or ""),
        "look_sideways_count": str(selected_row.get("look_sideways_count") or ""),
        "talk_with_others_count": str(selected_row.get("talk_with_others_count") or ""),
        "answer_questions_count": str(selected_row.get("answer_questions_count") or ""),
        "target_action_names": str(selected_row.get("target_action_names") or ""),
        "manual_category": category,
        "manual_category_cn": category_cn,
        "manual_review_status": "classified",
        "selected_for_phase34": "pending_final_selection",
        "manual_summary": summary,
        "teaching_interpretation": interpretation,
        "notes": "SAV 外部真实课堂切片，需与自采数据区分。",
    }


def _manual_category_for_clip(clip_id: str) -> str:
    if clip_id in INTERACTION_CLIP_IDS:
        return "question_interaction"
    if clip_id in ROUTINE_CLIP_IDS:
        return "classroom_routine_standing"
    return "unknown"


def _category_text(category: str) -> tuple[str, str, str]:
    if category == "question_interaction":
        return (
            "课堂提问对应的多个体举手以及少个体站立。",
            "可用于验证课堂互动、举手响应、少量站立回答等互动行为。",
            "课堂互动型",
        )
    if category == "classroom_routine_standing":
        return (
            "上课前或下课时触发的群体站立行为。",
            "可用于验证系统对课堂流程/仪式性站立行为的识别，但不应简单解释为课堂互动增强。",
            "课堂流程型",
        )
    return ("待人工确认。", "待人工确认。", "待确认")


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
