from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
REQUIRED_SOURCE_FIELDS = {
    "source_name",
    "source_type",
    "data_mode",
    "is_demo",
    "is_own_capture",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4b SAV-50 candidate list.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--candidates-csv", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--manual-review-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    candidates_csv = args.candidates_csv.resolve() if args.candidates_csv else reports_dir / "selected_sav50_candidates.csv"
    summary_json = args.summary_json.resolve() if args.summary_json else reports_dir / "selected_sav50_summary.json"
    manual_review_csv = args.manual_review_csv.resolve() if args.manual_review_csv else reports_dir / "manual_review_results.csv"

    file_present = candidates_csv.exists()
    summary_present = summary_json.exists()
    rows = _read_rows(candidates_csv) if file_present else []
    manual_rows = _read_rows(manual_review_csv) if manual_review_csv.exists() else []
    manual_clip_ids = {str(row.get("clip_id") or "") for row in manual_rows}
    summary_ok = _summary_matches(summary_json, rows) if summary_present else False

    total_count = len(rows)
    existing_count = sum(1 for row in rows if row.get("candidate_origin") == "sav16_manual_reviewed")
    new_count = sum(1 for row in rows if row.get("candidate_origin") == "sav50_auto_selected")
    interaction_count = sum(1 for row in rows if row.get("phase34_category") == "question_interaction")
    routine_count = sum(1 for row in rows if row.get("phase34_category") == "classroom_routine_standing")
    attention_count = sum(1 for row in rows if row.get("phase34_category") == "attention_learning_state")
    clip_ids = [str(row.get("clip_id") or "") for row in rows]
    no_duplicates = len(clip_ids) == len(set(clip_ids)) == total_count
    new_rows = [row for row in rows if row.get("candidate_origin") == "sav50_auto_selected"]
    new_excludes_existing = all(str(row.get("clip_id") or "") not in manual_clip_ids for row in new_rows)
    source_marked = bool(rows) and all(_source_fields_ok(row) for row in rows)
    new_status_ok = bool(new_rows) and all(
        row.get("manual_review_status") == "pending"
        and row.get("selected_for_phase34") == "pending_manual_review"
        for row in new_rows
    )
    ready = bool(
        file_present
        and summary_present
        and summary_ok
        and total_count == 50
        and existing_count == 16
        and new_count == 34
        and interaction_count == 25
        and routine_count == 15
        and attention_count == 10
        and no_duplicates
        and new_excludes_existing
        and source_marked
        and new_status_ok
    )

    print(f"PHASE34_SAV50_FILE_PRESENT={_bool_text(file_present)}")
    print(f"PHASE34_SAV50_SUMMARY_PRESENT={_bool_text(summary_present)}")
    print(f"PHASE34_SAV50_TOTAL_COUNT={total_count}")
    print(f"PHASE34_SAV50_EXISTING_COUNT={existing_count}")
    print(f"PHASE34_SAV50_NEW_COUNT={new_count}")
    print(f"PHASE34_SAV50_INTERACTION_COUNT={interaction_count}")
    print(f"PHASE34_SAV50_ROUTINE_COUNT={routine_count}")
    print(f"PHASE34_SAV50_ATTENTION_COUNT={attention_count}")
    print(f"PHASE34_SAV50_NO_DUPLICATES={_bool_text(no_duplicates and new_excludes_existing)}")
    print(f"PHASE34_SAV50_SOURCE_MARKED={_bool_text(source_marked)}")
    print(f"PHASE34_SAV50_READY_FOR_DOWNLOAD={_bool_text(ready)}")
    print(f"PHASE34_SAV50_CANDIDATES_OK={_bool_text(ready)}")
    return 0 if ready else 1


def _summary_matches(path: Path, rows: list[dict[str, str]]) -> bool:
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        summary.get("total_count") == len(rows)
        and summary.get("existing_sav16_count") == sum(1 for row in rows if row.get("candidate_origin") == "sav16_manual_reviewed")
        and summary.get("new_candidate_count") == sum(1 for row in rows if row.get("candidate_origin") == "sav50_auto_selected")
    )


def _source_fields_ok(row: dict[str, str]) -> bool:
    if not REQUIRED_SOURCE_FIELDS.issubset(row.keys()):
        return False
    return (
        row.get("source_name") == "SAV"
        and row.get("source_type") == "public_dataset"
        and row.get("data_mode") == "external_real_clip"
        and row.get("is_demo") == "false"
        and row.get("is_own_capture") == "false"
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
