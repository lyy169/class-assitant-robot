from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
CANDIDATE_REQUIRED_FIELDS = {
    "official_start_time",
    "official_end_time",
    "suggested_clip_start_time",
    "suggested_clip_end_time",
}
VIDEO_LINK_REQUIRED_FIELDS = {
    "min_start_time",
    "max_end_time",
    "suggested_min_start_time",
    "suggested_max_end_time",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate readable MM:SS.s time columns for Phase 3.4 SAV CSV files.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--candidates-csv", type=Path, default=None)
    parser.add_argument("--video-links-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    candidates_csv = args.candidates_csv.resolve() if args.candidates_csv else sav_root / "reports" / "selected_sav_candidates.csv"
    video_links_csv = args.video_links_csv.resolve() if args.video_links_csv else sav_root / "reports" / "selected_sav_video_links.csv"

    candidate_rows, candidate_fields = _read_rows(candidates_csv) if candidates_csv.exists() else ([], [])
    video_link_rows, video_link_fields = _read_rows(video_links_csv) if video_links_csv.exists() else ([], [])

    candidates_ok = bool(candidate_rows) and CANDIDATE_REQUIRED_FIELDS.issubset(set(candidate_fields))
    video_links_ok = bool(video_link_rows) and VIDEO_LINK_REQUIRED_FIELDS.issubset(set(video_link_fields))
    format_ok = _candidate_times_have_colons(candidate_rows) and _video_link_times_have_colons(video_link_rows)
    example_ok = _example_987_5_is_correct(candidate_rows, video_link_rows)
    count_preserved = len(candidate_rows) == 16 and len(video_link_rows) == 15
    readable_times_ok = bool(candidates_ok and video_links_ok and format_ok and example_ok and count_preserved)

    print(f"PHASE34_READABLE_TIMES_CANDIDATES_OK={_bool_text(candidates_ok)}")
    print(f"PHASE34_READABLE_TIMES_VIDEO_LINKS_OK={_bool_text(video_links_ok)}")
    print(f"PHASE34_READABLE_TIMES_FORMAT_OK={_bool_text(format_ok and example_ok)}")
    print(f"PHASE34_READABLE_TIMES_COUNT_PRESERVED={_bool_text(count_preserved)}")
    print(f"PHASE34_READABLE_TIMES_OK={_bool_text(readable_times_ok)}")
    return 0 if readable_times_ok else 1


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), list(reader.fieldnames or [])


def _candidate_times_have_colons(rows: list[dict[str, str]]) -> bool:
    fields = (
        "official_start_time",
        "official_end_time",
        "suggested_clip_start_time",
        "suggested_clip_end_time",
    )
    return bool(rows) and all(_row_times_have_colons(row, fields) for row in rows)


def _video_link_times_have_colons(rows: list[dict[str, str]]) -> bool:
    fields = (
        "min_start_time",
        "max_end_time",
        "suggested_min_start_time",
        "suggested_max_end_time",
    )
    return bool(rows) and all(_row_times_have_colons(row, fields) for row in rows)


def _row_times_have_colons(row: dict[str, str], fields: tuple[str, ...]) -> bool:
    return all(":" in str(row.get(field) or "") for field in fields)


def _example_987_5_is_correct(candidate_rows: list[dict[str, str]], video_link_rows: list[dict[str, str]]) -> bool:
    matching_candidate_rows = [row for row in candidate_rows if _is_987_5(row.get("start_sec"))]
    matching_video_rows = [row for row in video_link_rows if _is_987_5(row.get("min_start_sec"))]
    if not matching_candidate_rows and not matching_video_rows:
        return True
    candidate_ok = all(row.get("official_start_time") == "16:27.5" for row in matching_candidate_rows)
    video_ok = all(row.get("min_start_time") == "16:27.5" for row in matching_video_rows)
    return candidate_ok and video_ok


def _is_987_5(value: str | None) -> bool:
    try:
        return abs(float(str(value or "").strip()) - 987.5) < 0.0001
    except ValueError:
        return False


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
