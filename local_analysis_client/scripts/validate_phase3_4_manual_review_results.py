from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4 SAV manual review classification results.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--review-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    review_csv = args.review_csv.resolve() if args.review_csv else sav_root / "reports" / "manual_review_results.csv"
    file_present = review_csv.exists()
    rows = _read_rows(review_csv) if file_present else []
    total_count = len(rows)
    interaction_count = sum(1 for row in rows if row.get("manual_category") == "question_interaction")
    routine_count = sum(1 for row in rows if row.get("manual_category") == "classroom_routine_standing")
    all_clips_exist = bool(rows) and all(str(row.get("manual_clip_exists") or "").lower() == "true" for row in rows)
    all_classified = bool(rows) and all(row.get("manual_review_status") == "classified" for row in rows)
    all_pending = bool(rows) and all(row.get("selected_for_phase34") == "pending_final_selection" for row in rows)
    category_by_clip = {str(row.get("clip_id") or ""): str(row.get("manual_category") or "") for row in rows}
    sentinel_ok = (
        category_by_clip.get("20200908_17_494") == "question_interaction"
        and category_by_clip.get("20220822_08_1098") == "classroom_routine_standing"
    )
    classification_ok = bool(
        total_count == 16
        and interaction_count == 8
        and routine_count == 8
        and all_classified
        and all_pending
        and sentinel_ok
    )
    ready = bool(file_present and all_clips_exist and classification_ok)

    print(f"PHASE34_MANUAL_REVIEW_FILE_PRESENT={_bool_text(file_present)}")
    print(f"PHASE34_MANUAL_REVIEW_TOTAL_COUNT={total_count}")
    print(f"PHASE34_MANUAL_REVIEW_INTERACTION_COUNT={interaction_count}")
    print(f"PHASE34_MANUAL_REVIEW_ROUTINE_COUNT={routine_count}")
    print(f"PHASE34_MANUAL_REVIEW_ALL_CLIPS_EXIST={_bool_text(all_clips_exist)}")
    print(f"PHASE34_MANUAL_REVIEW_CLASSIFICATION_OK={_bool_text(classification_ok)}")
    print(f"PHASE34_MANUAL_REVIEW_READY_FOR_FINAL_SELECTION={_bool_text(ready)}")
    return 0 if ready else 1


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
