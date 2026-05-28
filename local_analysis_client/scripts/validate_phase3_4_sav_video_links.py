from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate resolved SAV video links for Phase 3.4 selected candidates.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--selected-csv", type=Path, default=None)
    parser.add_argument("--video-links-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    selected_csv = args.selected_csv.resolve() if args.selected_csv else sav_root / "reports" / "selected_sav_candidates.csv"
    video_links_csv = args.video_links_csv.resolve() if args.video_links_csv else sav_root / "reports" / "selected_sav_video_links.csv"

    file_present = video_links_csv.exists()
    selected_rows = _read_rows(selected_csv) if selected_csv.exists() else []
    link_rows = _read_rows(video_links_csv) if file_present else []
    selected_source_ids = {str(row.get("source_video_id") or "").strip() for row in selected_rows if row.get("source_video_id")}

    selected_source_count = len(selected_source_ids)
    output_source_ids = {str(row.get("source_video_id") or "").strip() for row in link_rows if row.get("source_video_id")}
    source_count_correct = bool(selected_source_ids) and output_source_ids == selected_source_ids
    video_link_found_count = sum(1 for row in link_rows if _is_true(row.get("link_found")) and _has_value(row, "video_link"))
    pending_count = sum(1 for row in link_rows if row.get("download_status") == "pending_manual_download")
    resolve_ok = bool(
        file_present
        and source_count_correct
        and video_link_found_count > 0
        and pending_count == len(link_rows)
        and len(link_rows) == selected_source_count
    )

    print(f"PHASE34_SAV_VIDEO_LINK_FILE_PRESENT={_bool_text(file_present)}")
    print(f"PHASE34_SAV_SELECTED_SOURCE_COUNT={selected_source_count}")
    print(f"PHASE34_SAV_VIDEO_LINK_FOUND_COUNT={video_link_found_count}")
    print(f"PHASE34_SAV_VIDEO_LINK_PENDING_DOWNLOAD_COUNT={pending_count}")
    print(f"PHASE34_SAV_VIDEO_LINK_RESOLVE_OK={_bool_text(resolve_ok)}")
    return 0 if resolve_ok else 1


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _is_true(value: str | None) -> bool:
    return str(value or "").strip().lower() == "true"


def _has_value(row: dict[str, str], key: str) -> bool:
    return bool(str(row.get(key) or "").strip())


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
