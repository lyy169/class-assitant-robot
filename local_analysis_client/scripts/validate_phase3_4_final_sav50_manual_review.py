from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
SOURCE_FIELDS = {
    "source_name": "SAV",
    "source_type": "public_dataset",
    "data_mode": "external_real_clip",
    "is_demo": "false",
    "is_own_capture": "false",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate finalized Phase 3.4 SAV-50 manual review results.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--review-csv", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    review_csv = args.review_csv.resolve() if args.review_csv else reports_dir / "final_sav50_manual_review_results.csv"
    summary_json = args.summary_json.resolve() if args.summary_json else reports_dir / "final_sav50_summary.json"

    review_present = review_csv.exists()
    summary_present = summary_json.exists()
    rows = _read_rows(review_csv) if review_present else []
    summary = _read_json(summary_json) if summary_present else {}
    counts = Counter(row.get("final_phase34_category") for row in rows)

    total_count = len(rows)
    interaction_count = counts.get("question_interaction", 0)
    routine_standing_count = counts.get("classroom_routine_standing", 0)
    routine_bending_count = counts.get("classroom_routine_bending", 0)
    routine_total = routine_standing_count + routine_bending_count
    all_classified = bool(rows) and all(row.get("manual_review_status") == "classified" for row in rows)
    all_selected = bool(rows) and all(row.get("selected_for_phase34") == "yes" for row in rows)
    all_clips_exist = bool(rows) and all(
        row.get("manual_clip_exists") == "true" and Path(str(row.get("manual_clip_path") or "")).exists()
        for row in rows
    )
    source_marked = bool(rows) and all(
        all(str(row.get(field) or "") == expected for field, expected in SOURCE_FIELDS.items())
        for row in rows
    )
    original_attention_rows = [row for row in rows if row.get("original_phase34_category") == "attention_learning_state"]
    no_attention_mislabel = (
        counts.get("attention_learning_state", 0) == 0
        and len(original_attention_rows) == 10
        and all(row.get("final_phase34_category") == "classroom_routine_bending" for row in original_attention_rows)
    )
    summary_ok = _summary_matches(
        summary=summary,
        total_count=total_count,
        interaction_count=interaction_count,
        routine_standing_count=routine_standing_count,
        routine_bending_count=routine_bending_count,
        routine_total=routine_total,
    )
    ok = (
        review_present
        and summary_present
        and total_count == 50
        and interaction_count == 25
        and routine_standing_count == 15
        and routine_bending_count == 10
        and routine_total == 25
        and all_classified
        and all_selected
        and all_clips_exist
        and source_marked
        and no_attention_mislabel
        and summary_ok
    )

    print(f"PHASE34_FINAL_SAV50_REVIEW_FILE_PRESENT={_bool_text(review_present)}")
    print(f"PHASE34_FINAL_SAV50_SUMMARY_PRESENT={_bool_text(summary_present)}")
    print(f"PHASE34_FINAL_SAV50_TOTAL_COUNT={total_count}")
    print(f"PHASE34_FINAL_SAV50_INTERACTION_COUNT={interaction_count}")
    print(f"PHASE34_FINAL_SAV50_ROUTINE_STANDING_COUNT={routine_standing_count}")
    print(f"PHASE34_FINAL_SAV50_ROUTINE_BENDING_COUNT={routine_bending_count}")
    print(f"PHASE34_FINAL_SAV50_ROUTINE_TOTAL={routine_total}")
    print(f"PHASE34_FINAL_SAV50_ALL_CLASSIFIED={_bool_text(all_classified)}")
    print(f"PHASE34_FINAL_SAV50_ALL_SELECTED={_bool_text(all_selected)}")
    print(f"PHASE34_FINAL_SAV50_ALL_CLIPS_EXIST={_bool_text(all_clips_exist)}")
    print(f"PHASE34_FINAL_SAV50_SOURCE_MARKED={_bool_text(source_marked)}")
    print(f"PHASE34_FINAL_SAV50_NO_ATTENTION_MISLABEL={_bool_text(no_attention_mislabel)}")
    print(f"PHASE34_FINAL_SAV50_MANUAL_REVIEW_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _summary_matches(
    *,
    summary: dict[str, object],
    total_count: int,
    interaction_count: int,
    routine_standing_count: int,
    routine_bending_count: int,
    routine_total: int,
) -> bool:
    return (
        summary.get("dataset_name") == "phase3_4_sav50_validation_set"
        and summary.get("total_count") == total_count
        and summary.get("question_interaction_count") == interaction_count
        and summary.get("classroom_routine_standing_count") == routine_standing_count
        and summary.get("classroom_routine_bending_count") == routine_bending_count
        and summary.get("classroom_interaction_total") == interaction_count
        and summary.get("classroom_routine_total") == routine_total
        and summary.get("source_name") == "SAV"
        and summary.get("source_type") == "public_dataset"
        and summary.get("data_mode") == "external_real_clip"
        and summary.get("is_demo") is False
        and summary.get("is_own_capture") is False
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
