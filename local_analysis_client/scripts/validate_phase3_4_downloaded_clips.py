from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
FIRST_SAMPLE_CLIP = "20200908_17_494.mp4"
REQUIRED_STATUS_FIELDS = {
    "clip_id",
    "source_video_id",
    "manual_clip_path",
    "download_status",
    "clip_status",
}
DELETE_STATUS_FIELDS = {
    "source_deleted",
    "source_delete_mode",
    "source_delete_error",
}
VALID_DELETE_MODES = {"none", "after_success", "after_attempt"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4 downloaded/cut SAV clips workspace.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    status_csv = sav_root / "reports" / "clip_download_status.csv"
    manual_clips_dir = sav_root / "manual_clips"
    source_videos_dir = sav_root / "source_videos"
    status_file_present = status_csv.exists()
    manual_clips_dir_present = manual_clips_dir.is_dir()
    mp4_count = len(list(manual_clips_dir.glob("*.mp4"))) if manual_clips_dir_present else 0
    first_manual_sample_present = (manual_clips_dir / FIRST_SAMPLE_CLIP).exists()
    status_rows, status_fields = _read_rows_and_fields(status_csv) if status_file_present else ([], [])
    status_schema_ok = REQUIRED_STATUS_FIELDS.issubset(set(status_fields))
    delete_fields_ok = DELETE_STATUS_FIELDS.issubset(set(status_fields))
    delete_mode_ok = _delete_modes_are_valid(status_rows) if delete_fields_ok else False
    source_delete_safety_ok = _source_delete_rows_are_safe(status_rows, source_videos_dir) if delete_fields_ok else False
    validation_ok = bool(
        status_file_present
        and manual_clips_dir_present
        and mp4_count >= 1
        and first_manual_sample_present
        and status_schema_ok
        and delete_fields_ok
        and delete_mode_ok
        and source_delete_safety_ok
    )

    print(f"PHASE34_CLIP_STATUS_FILE_PRESENT={_bool_text(status_file_present)}")
    print(f"PHASE34_MANUAL_CLIPS_DIR_PRESENT={_bool_text(manual_clips_dir_present)}")
    print(f"PHASE34_MANUAL_CLIP_MP4_COUNT={mp4_count}")
    print(f"PHASE34_FIRST_MANUAL_SAMPLE_PRESENT={_bool_text(first_manual_sample_present)}")
    print(f"PHASE34_CLIP_STATUS_SCHEMA_OK={_bool_text(status_schema_ok)}")
    print(f"PHASE34_CLIP_STATUS_DELETE_FIELDS_OK={_bool_text(delete_fields_ok)}")
    print(f"PHASE34_SOURCE_DELETE_MODE_OK={_bool_text(delete_mode_ok)}")
    print(f"PHASE34_SOURCE_DELETE_SAFETY_OK={_bool_text(source_delete_safety_ok)}")
    print(f"PHASE34_DOWNLOADED_CLIPS_VALIDATION_OK={_bool_text(validation_ok)}")
    return 0 if validation_ok else 1


def _read_rows_and_fields(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), list(reader.fieldnames or [])


def _delete_modes_are_valid(rows: list[dict[str, str]]) -> bool:
    if not rows:
        return True
    for row in rows:
        mode = str(row.get("source_delete_mode") or "")
        deleted = str(row.get("source_deleted") or "").lower() == "true"
        if mode not in VALID_DELETE_MODES:
            return False
        if deleted and mode not in {"after_success", "after_attempt"}:
            return False
        if deleted and not str(row.get("manual_clip_path") or "").strip():
            return False
    return True


def _source_delete_rows_are_safe(rows: list[dict[str, str]], source_videos_dir: Path) -> bool:
    if not rows:
        return True
    source_dir = source_videos_dir.resolve(strict=False)
    for row in rows:
        source_video_id = str(row.get("source_video_id") or "").strip()
        source_path_text = str(row.get("source_video_path") or "").strip()
        if not source_video_id or not source_path_text:
            return False
        source_path = Path(source_path_text).resolve(strict=False)
        if source_path.parent != source_dir:
            return False
        if source_path.name != f"{source_video_id}.mp4":
            return False
    return True


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
