from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4 selected SAV candidate clips.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--source-csv", type=Path, default=None)
    parser.add_argument("--selected-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    source_csv = args.source_csv.resolve() if args.source_csv else sav_root / "reports" / "sav_target_candidate_clips.csv"
    selected_csv = args.selected_csv.resolve() if args.selected_csv else sav_root / "reports" / "selected_sav_candidates.csv"

    file_present = selected_csv.exists()
    selected_rows = _read_rows(selected_csv) if file_present else []
    source_rows = _read_rows(source_csv) if source_csv.exists() else []
    source_clip_ids = {str(row.get("clip_id") or "") for row in source_rows}

    total_count = len(selected_rows)
    raise_hand_count = sum(1 for row in selected_rows if row.get("selection_group") == "raise_hand")
    stand_count = sum(1 for row in selected_rows if row.get("selection_group") == "stand")
    all_source_matched = bool(selected_rows) and all(str(row.get("clip_id") or "") in source_clip_ids for row in selected_rows)
    time_fields_present = bool(selected_rows) and all(
        _has_value(row, "source_video_id") and _has_value(row, "start_sec") and _has_value(row, "end_sec")
        for row in selected_rows
    )
    manual_status_pending = bool(selected_rows) and all(row.get("manual_review_status") == "pending" for row in selected_rows)
    ready_for_manual_review = bool(
        file_present
        and total_count == 16
        and raise_hand_count == 8
        and stand_count == 8
        and all_source_matched
        and time_fields_present
        and manual_status_pending
    )

    print(f"PHASE34_SELECTED_SAV_FILE_PRESENT={_bool_text(file_present)}")
    print(f"PHASE34_SELECTED_SAV_TOTAL_COUNT={total_count}")
    print(f"PHASE34_SELECTED_SAV_RAISE_HAND_COUNT={raise_hand_count}")
    print(f"PHASE34_SELECTED_SAV_STAND_COUNT={stand_count}")
    print(f"PHASE34_SELECTED_SAV_ALL_SOURCE_MATCHED={_bool_text(all_source_matched)}")
    print(f"PHASE34_SELECTED_SAV_TIME_FIELDS_PRESENT={_bool_text(time_fields_present)}")
    print(f"PHASE34_SELECTED_SAV_READY_FOR_MANUAL_REVIEW={_bool_text(ready_for_manual_review)}")
    return 0 if ready_for_manual_review else 1


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _has_value(row: dict[str, str], key: str) -> bool:
    return bool(str(row.get(key) or "").strip())


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
