from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
REQUIRED_STATUS_FIELDS = {
    "clip_id",
    "source_video_id",
    "phase34_category",
    "candidate_origin",
    "manual_clip_path",
    "download_status",
    "clip_status",
}
DELETE_FIELDS = {
    "source_deleted",
    "source_delete_mode",
    "source_delete_error",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SAV-50 new downloaded/clipped candidates.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--status-csv", type=Path, default=None)
    parser.add_argument("--candidates-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    status_csv = args.status_csv.resolve() if args.status_csv else reports_dir / "sav50_clip_download_status.csv"
    candidates_csv = args.candidates_csv.resolve() if args.candidates_csv else reports_dir / "selected_sav50_candidates.csv"
    manual_clips_dir = sav_root / "manual_clips"

    status_present = status_csv.exists()
    manual_dir_present = manual_clips_dir.is_dir()
    status_rows, status_fields = _read_rows_and_fields(status_csv) if status_present else ([], [])
    expected_new_ids = {
        str(row.get("clip_id") or "")
        for row in _read_rows(candidates_csv)
        if row.get("candidate_origin") == "sav50_auto_selected"
    } if candidates_csv.exists() else set()
    mp4_count = sum(1 for clip_id in expected_new_ids if (manual_clips_dir / f"{clip_id}.mp4").exists()) if manual_dir_present else 0
    schema_ok = REQUIRED_STATUS_FIELDS.issubset(set(status_fields))
    delete_fields_ok = DELETE_FIELDS.issubset(set(status_fields))
    delete_mode_ok = _delete_modes_ok(status_rows) if delete_fields_ok else False
    validation_ok = bool(status_present and manual_dir_present and mp4_count >= 1 and schema_ok and delete_fields_ok and delete_mode_ok)

    print(f"PHASE34_SAV50_CLIP_STATUS_FILE_PRESENT={_bool_text(status_present)}")
    print(f"PHASE34_SAV50_MANUAL_CLIPS_DIR_PRESENT={_bool_text(manual_dir_present)}")
    print(f"PHASE34_SAV50_NEW_CLIP_MP4_COUNT={mp4_count}")
    print(f"PHASE34_SAV50_EXPECTED_NEW_COUNT={len(expected_new_ids) if expected_new_ids else 34}")
    print(f"PHASE34_SAV50_CLIP_STATUS_SCHEMA_OK={_bool_text(schema_ok)}")
    print(f"PHASE34_SAV50_DELETE_FIELDS_OK={_bool_text(delete_fields_ok and delete_mode_ok)}")
    print(f"PHASE34_SAV50_DOWNLOADED_CLIPS_VALIDATION_OK={_bool_text(validation_ok)}")
    return 0 if validation_ok else 1


def _delete_modes_ok(rows: list[dict[str, str]]) -> bool:
    for row in rows:
        deleted = str(row.get("source_deleted") or "").lower() == "true"
        mode = str(row.get("source_delete_mode") or "")
        if deleted and mode != "after_attempt":
            return False
    return True


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _read_rows_and_fields(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), list(reader.fieldnames or [])


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
