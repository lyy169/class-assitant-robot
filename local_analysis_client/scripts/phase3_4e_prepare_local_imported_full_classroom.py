from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
SAMPLE_ID = "local_imported_sav_full_classroom_20200908_17"
SOURCE_VIDEO_ID = "20200908_17"
SOURCE_DATASET = "SAV"
SOURCE_TYPE = "local_imported_video"
SAMPLE_TYPE = "external_full_classroom_video"
EXPECTED_KEY_EVENT_NOTE = "16:27.5-16:30.5 contains many raised hands and a few standing students"

MANIFEST_FIELDS = (
    "sample_id",
    "source_video_id",
    "video_path",
    "source_dataset",
    "source_type",
    "sample_type",
    "is_pi_capture",
    "is_own_capture",
    "is_local_processed",
    "expected_key_event_note",
    "created_at",
    "video_link",
    "link_found",
    "download_status",
    "video_size_bytes",
    "duration_seconds",
    "analysis_package_dir",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Phase 3.4e local imported SAV full-classroom workspace.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    videos_dir = sample_root / "videos"
    reports_dir = sample_root / "reports"
    analysis_results_dir = sample_root / "analysis_results"
    packages_dir = sample_root / "packages"
    for path in (sample_root, videos_dir, reports_dir, analysis_results_dir, packages_dir):
        path.mkdir(parents=True, exist_ok=True)

    target_video = videos_dir / f"{SAMPLE_ID}.mp4"
    manifest_csv = reports_dir / "local_imported_full_classroom_manifest.csv"
    existing_row = _read_first_row(manifest_csv)
    row = _build_manifest_row(target_video=target_video, packages_dir=packages_dir, existing_row=existing_row)
    _write_rows(manifest_csv, [row])

    video_present = target_video.exists()
    ready_for_analysis = video_present
    print(f"PHASE34E_LOCAL_IMPORTED_WORKSPACE={sample_root}")
    print(f"PHASE34E_LOCAL_IMPORTED_VIDEO_PATH={target_video}")
    print(f"PHASE34E_LOCAL_IMPORTED_MANIFEST={manifest_csv}")
    print(f"PHASE34E_LOCAL_IMPORTED_VIDEO_PRESENT={_bool_text(video_present)}")
    print(f"PHASE34E_LOCAL_IMPORTED_READY_FOR_ANALYSIS={_bool_text(ready_for_analysis)}")
    return 0


def _build_manifest_row(*, target_video: Path, packages_dir: Path, existing_row: dict[str, str]) -> dict[str, str]:
    return {
        "sample_id": SAMPLE_ID,
        "source_video_id": SOURCE_VIDEO_ID,
        "video_path": str(target_video),
        "source_dataset": SOURCE_DATASET,
        "source_type": SOURCE_TYPE,
        "sample_type": SAMPLE_TYPE,
        "is_pi_capture": "false",
        "is_own_capture": "false",
        "is_local_processed": "true",
        "expected_key_event_note": EXPECTED_KEY_EVENT_NOTE,
        "created_at": existing_row.get("created_at") or _utc_now(),
        "video_link": existing_row.get("video_link", ""),
        "link_found": existing_row.get("link_found", "false"),
        "download_status": existing_row.get("download_status", "existing" if target_video.exists() else "pending"),
        "video_size_bytes": str(target_video.stat().st_size) if target_video.exists() else existing_row.get("video_size_bytes", ""),
        "duration_seconds": existing_row.get("duration_seconds", ""),
        "analysis_package_dir": str(packages_dir / SAMPLE_ID),
    }


def _read_first_row(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    return rows[0] if rows else {}


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in MANIFEST_FIELDS})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
