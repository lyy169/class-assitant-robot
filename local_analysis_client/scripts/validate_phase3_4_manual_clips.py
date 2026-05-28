from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
FIRST_SAMPLE_CLIP_ID = "20200908_17_494"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4 SAV manual clip registry.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--selected-csv", type=Path, default=None)
    parser.add_argument("--manual-clips-dir", type=Path, default=None)
    parser.add_argument("--registry-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    selected_csv = args.selected_csv.resolve() if args.selected_csv else sav_root / "reports" / "selected_sav_candidates.csv"
    manual_clips_dir = args.manual_clips_dir.resolve() if args.manual_clips_dir else sav_root / "manual_clips"
    registry_csv = args.registry_csv.resolve() if args.registry_csv else sav_root / "reports" / "manual_clip_registry.csv"

    manual_clip_dir_present = manual_clips_dir.is_dir()
    registry_present = registry_csv.exists()
    registry_rows = _read_rows(registry_csv) if registry_present else []
    selected_rows = _read_rows(selected_csv) if selected_csv.exists() else []
    selected_clip_ids = {str(row.get("clip_id") or "").strip() for row in selected_rows}
    first_sample_path = manual_clips_dir / f"{FIRST_SAMPLE_CLIP_ID}.mp4"
    first_sample_rows = [row for row in registry_rows if row.get("clip_id") == FIRST_SAMPLE_CLIP_ID]
    first_sample_row = first_sample_rows[0] if first_sample_rows else {}

    manual_clip_count = len(registry_rows)
    source_matched = bool(registry_rows) and all(str(row.get("clip_id") or "").strip() in selected_clip_ids for row in registry_rows)
    first_sample_present = first_sample_path.exists()
    first_sample_source_matched = FIRST_SAMPLE_CLIP_ID in selected_clip_ids
    first_sample_passed = bool(
        first_sample_row
        and first_sample_row.get("manual_review_status") == "passed"
        and first_sample_row.get("selected_for_phase34") == "yes"
    )
    registry_ok = bool(
        manual_clip_dir_present
        and registry_present
        and manual_clip_count >= 1
        and source_matched
        and first_sample_present
        and first_sample_source_matched
        and first_sample_passed
    )

    print(f"PHASE34_MANUAL_CLIP_DIR_PRESENT={_bool_text(manual_clip_dir_present)}")
    print(f"PHASE34_MANUAL_CLIP_REGISTRY_PRESENT={_bool_text(registry_present)}")
    print(f"PHASE34_MANUAL_CLIP_COUNT={manual_clip_count}")
    print(f"PHASE34_MANUAL_CLIP_SOURCE_MATCHED={_bool_text(source_matched and first_sample_source_matched)}")
    print(f"PHASE34_MANUAL_CLIP_FIRST_SAMPLE_PRESENT={_bool_text(first_sample_present)}")
    print(f"PHASE34_MANUAL_CLIP_FIRST_SAMPLE_PASSED={_bool_text(first_sample_passed)}")
    print(f"PHASE34_MANUAL_CLIP_REGISTRY_OK={_bool_text(registry_ok)}")
    return 0 if registry_ok else 1


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
