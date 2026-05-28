from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
SOURCE_NAME = "SAV"
SOURCE_TYPE = "public_dataset"
DATA_MODE = "external_real_clip"
NOTES = "SAV 外部真实课堂切片，用于本地端识别可信度验证，不作为树莓派自采数据。"

OUTPUT_FIELDS = (
    "dataset_order",
    "clip_id",
    "source_video_id",
    "manual_clip_path",
    "manual_clip_exists",
    "person_count",
    "stand_count",
    "raise_hand_count",
    "bend_count",
    "look_sideways_count",
    "talk_with_others_count",
    "answer_questions_count",
    "target_action_names",
    "original_phase34_category",
    "final_phase34_category",
    "final_phase34_category_cn",
    "manual_review_status",
    "selected_for_phase34",
    "manual_summary",
    "teaching_interpretation",
    "source_name",
    "source_type",
    "data_mode",
    "is_demo",
    "is_own_capture",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize Phase 3.4 SAV-50 manual review results.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--selected-csv", type=Path, default=None)
    parser.add_argument("--manual-review-csv", type=Path, default=None)
    parser.add_argument("--clip-status-csv", type=Path, default=None)
    parser.add_argument("--manual-clips-dir", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    selected_csv = args.selected_csv.resolve() if args.selected_csv else reports_dir / "selected_sav50_candidates.csv"
    manual_review_csv = args.manual_review_csv.resolve() if args.manual_review_csv else reports_dir / "manual_review_results.csv"
    clip_status_csv = args.clip_status_csv.resolve() if args.clip_status_csv else reports_dir / "sav50_clip_download_status.csv"
    manual_clips_dir = args.manual_clips_dir.resolve() if args.manual_clips_dir else sav_root / "manual_clips"
    output_csv = args.output_csv.resolve() if args.output_csv else reports_dir / "final_sav50_manual_review_results.csv"
    summary_json = args.summary_json.resolve() if args.summary_json else reports_dir / "final_sav50_summary.json"

    if not selected_csv.exists() or not manual_review_csv.exists() or not clip_status_csv.exists():
        print(f"PHASE34_FINAL_SAV50_SELECTED_PRESENT={_bool_text(selected_csv.exists())}")
        print(f"PHASE34_FINAL_SAV50_MANUAL_REVIEW_PRESENT={_bool_text(manual_review_csv.exists())}")
        print(f"PHASE34_FINAL_SAV50_CLIP_STATUS_PRESENT={_bool_text(clip_status_csv.exists())}")
        print("PHASE34_FINAL_SAV50_WRITTEN=false")
        return 1

    selected_rows = _read_rows(selected_csv)
    manual_review_by_clip = {str(row.get("clip_id") or ""): row for row in _read_rows(manual_review_csv)}
    clip_status_by_clip = {str(row.get("clip_id") or ""): row for row in _read_rows(clip_status_csv)}
    manual_clip_paths = {path.stem: path for path in manual_clips_dir.glob("*.mp4")} if manual_clips_dir.exists() else {}

    output_rows = [
        _build_output_row(
            selected_row=selected_row,
            manual_review_row=manual_review_by_clip.get(str(selected_row.get("clip_id") or ""), {}),
            clip_status_row=clip_status_by_clip.get(str(selected_row.get("clip_id") or ""), {}),
            manual_clip_paths=manual_clip_paths,
            manual_clips_dir=manual_clips_dir,
        )
        for selected_row in sorted(selected_rows, key=_dataset_order_key)
    ]

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_rows(output_csv, output_rows)
    summary = _build_summary(output_rows)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = Counter(row.get("final_phase34_category") for row in output_rows)
    print(f"PHASE34_FINAL_SAV50_REVIEW_CSV={output_csv}")
    print(f"PHASE34_FINAL_SAV50_SUMMARY_JSON={summary_json}")
    print(f"PHASE34_FINAL_SAV50_TOTAL_COUNT={len(output_rows)}")
    print(f"PHASE34_FINAL_SAV50_INTERACTION_COUNT={counts.get('question_interaction', 0)}")
    print(f"PHASE34_FINAL_SAV50_ROUTINE_STANDING_COUNT={counts.get('classroom_routine_standing', 0)}")
    print(f"PHASE34_FINAL_SAV50_ROUTINE_BENDING_COUNT={counts.get('classroom_routine_bending', 0)}")
    print(f"PHASE34_FINAL_SAV50_WRITTEN={_bool_text(output_csv.exists() and summary_json.exists())}")
    return 0 if output_csv.exists() and summary_json.exists() and len(output_rows) == 50 else 1


def _build_output_row(
    *,
    selected_row: dict[str, str],
    manual_review_row: dict[str, str],
    clip_status_row: dict[str, str],
    manual_clip_paths: dict[str, Path],
    manual_clips_dir: Path,
) -> dict[str, str]:
    clip_id = str(selected_row.get("clip_id") or "")
    original_category = str(selected_row.get("phase34_category") or "")
    final_category = _final_category(original_category)
    category_cn, manual_summary, teaching_interpretation = _category_text(final_category)
    manual_clip_path = _resolve_manual_clip_path(
        clip_id=clip_id,
        manual_review_row=manual_review_row,
        clip_status_row=clip_status_row,
        manual_clip_paths=manual_clip_paths,
        manual_clips_dir=manual_clips_dir,
    )

    return {
        "dataset_order": str(selected_row.get("dataset_order") or ""),
        "clip_id": clip_id,
        "source_video_id": str(selected_row.get("source_video_id") or ""),
        "manual_clip_path": str(manual_clip_path),
        "manual_clip_exists": _bool_text(manual_clip_path.exists()),
        "person_count": str(selected_row.get("person_count") or ""),
        "stand_count": str(selected_row.get("stand_count") or ""),
        "raise_hand_count": str(selected_row.get("raise_hand_count") or ""),
        "bend_count": str(selected_row.get("bend_count") or ""),
        "look_sideways_count": str(selected_row.get("look_sideways_count") or ""),
        "talk_with_others_count": str(selected_row.get("talk_with_others_count") or ""),
        "answer_questions_count": str(selected_row.get("answer_questions_count") or ""),
        "target_action_names": str(selected_row.get("target_action_names") or ""),
        "original_phase34_category": original_category,
        "final_phase34_category": final_category,
        "final_phase34_category_cn": category_cn,
        "manual_review_status": "classified",
        "selected_for_phase34": "yes",
        "manual_summary": manual_summary,
        "teaching_interpretation": teaching_interpretation,
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": "false",
        "is_own_capture": "false",
        "notes": NOTES,
    }


def _resolve_manual_clip_path(
    *,
    clip_id: str,
    manual_review_row: dict[str, str],
    clip_status_row: dict[str, str],
    manual_clip_paths: dict[str, Path],
    manual_clips_dir: Path,
) -> Path:
    if clip_id in manual_clip_paths:
        return manual_clip_paths[clip_id].resolve()
    path_text = str(clip_status_row.get("manual_clip_path") or manual_review_row.get("manual_clip_path") or "").strip()
    if path_text:
        return Path(path_text).resolve()
    return (manual_clips_dir / f"{clip_id}.mp4").resolve()


def _final_category(original_category: str) -> str:
    if original_category == "attention_learning_state":
        return "classroom_routine_bending"
    return original_category


def _category_text(category: str) -> tuple[str, str, str]:
    if category == "question_interaction":
        return (
            "课堂互动型",
            "课堂提问对应的多个体举手以及少个体站立。",
            "可用于验证课堂互动、举手响应、少量站立回答等互动行为。",
        )
    if category == "classroom_routine_standing":
        return (
            "课堂流程型站立",
            "上课前或下课时触发的群体站立行为。",
            "可用于验证系统对课堂流程/仪式性站立行为的识别，但不应简单解释为课堂互动增强。",
        )
    if category == "classroom_routine_bending":
        return (
            "课堂流程型弯腰",
            "实际画面表现为课堂流程中的弯腰/鞠躬行为，并非学习投入或注意力偏移。",
            "该类样本用于说明课堂流程动作与注意力行为需要结合上下文区分，不能简单将 bend 解释为注意力下降。",
        )
    return ("待确认", "待人工确认。", "待人工确认。")


def _build_summary(rows: list[dict[str, str]]) -> dict[str, object]:
    counts = Counter(row.get("final_phase34_category") for row in rows)
    question_count = counts.get("question_interaction", 0)
    standing_count = counts.get("classroom_routine_standing", 0)
    bending_count = counts.get("classroom_routine_bending", 0)
    return {
        "dataset_name": "phase3_4_sav50_validation_set",
        "total_count": len(rows),
        "question_interaction_count": question_count,
        "classroom_routine_standing_count": standing_count,
        "classroom_routine_bending_count": bending_count,
        "classroom_interaction_total": question_count,
        "classroom_routine_total": standing_count + bending_count,
        "source_name": SOURCE_NAME,
        "source_type": SOURCE_TYPE,
        "data_mode": DATA_MODE,
        "is_demo": False,
        "is_own_capture": False,
        "validation_scope": "stand_and_raise_hand_focused_validation",
        "notes": "50 个 SAV 外部真实课堂切片已完成人工复核分类，用于验证本地端对举手、站立等课堂行为的识别可信度；其中 bend 标签经人工复核为课堂流程型弯腰，不作为注意力下降结论。",
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
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in OUTPUT_FIELDS})


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
