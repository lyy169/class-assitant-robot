from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")

CANDIDATE_TIME_FIELDS = (
    "official_start_time",
    "official_end_time",
    "suggested_clip_start_sec",
    "suggested_clip_end_sec",
    "suggested_clip_start_time",
    "suggested_clip_end_time",
)

VIDEO_LINK_TIME_FIELDS = (
    "min_start_time",
    "max_end_time",
    "suggested_min_start_sec",
    "suggested_max_end_sec",
    "suggested_min_start_time",
    "suggested_max_end_time",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Add readable MM:SS.s time columns to Phase 3.4 SAV CSV files.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--candidates-csv", type=Path, default=None)
    parser.add_argument("--video-links-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    candidates_csv = args.candidates_csv.resolve() if args.candidates_csv else sav_root / "reports" / "selected_sav_candidates.csv"
    video_links_csv = args.video_links_csv.resolve() if args.video_links_csv else sav_root / "reports" / "selected_sav_video_links.csv"

    if not candidates_csv.exists():
        print(f"PHASE34_READABLE_TIMES_CANDIDATES_CSV={candidates_csv}")
        print("PHASE34_READABLE_TIMES_CANDIDATES_UPDATED=false")
        return 1
    if not video_links_csv.exists():
        print(f"PHASE34_READABLE_TIMES_VIDEO_LINKS_CSV={video_links_csv}")
        print("PHASE34_READABLE_TIMES_VIDEO_LINKS_UPDATED=false")
        return 1

    candidate_rows, candidate_fields = _read_rows(candidates_csv)
    video_link_rows, video_link_fields = _read_rows(video_links_csv)
    candidate_rows_updated = _add_candidate_times(candidate_rows)
    video_link_rows_updated = _add_video_link_times(video_link_rows, candidate_rows_updated)
    candidate_output_fields = _extend_fields(candidate_fields, CANDIDATE_TIME_FIELDS)
    video_link_output_fields = _extend_fields(video_link_fields, VIDEO_LINK_TIME_FIELDS)

    # Probe both files before writing so a locked CSV does not leave only one file refreshed.
    _assert_writable(candidates_csv)
    _assert_writable(video_links_csv)
    _write_rows(candidates_csv, candidate_output_fields, candidate_rows_updated)
    _write_rows(video_links_csv, video_link_output_fields, video_link_rows_updated)

    print(f"PHASE34_READABLE_TIMES_CANDIDATES_CSV={candidates_csv}")
    print(f"PHASE34_READABLE_TIMES_VIDEO_LINKS_CSV={video_links_csv}")
    print(f"PHASE34_READABLE_TIMES_CANDIDATE_COUNT={len(candidate_rows_updated)}")
    print(f"PHASE34_READABLE_TIMES_VIDEO_LINK_COUNT={len(video_link_rows_updated)}")
    print("PHASE34_READABLE_TIMES_CANDIDATES_UPDATED=true")
    print("PHASE34_READABLE_TIMES_VIDEO_LINKS_UPDATED=true")
    return 0


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), list(reader.fieldnames or [])


def _add_candidate_times(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    updated: list[dict[str, str]] = []
    for row in rows:
        current = dict(row)
        start_sec = _safe_float(current.get("start_sec"))
        end_sec = _safe_float(current.get("end_sec"))
        if start_sec is not None:
            suggested_start_sec = max(start_sec - 10.0, 0.0)
            current["official_start_time"] = _format_readable_time(start_sec)
            current["suggested_clip_start_sec"] = _format_seconds_value(suggested_start_sec)
            current["suggested_clip_start_time"] = _format_readable_time(suggested_start_sec)
        if end_sec is not None:
            suggested_end_sec = end_sec + 10.0
            current["official_end_time"] = _format_readable_time(end_sec)
            current["suggested_clip_end_sec"] = _format_seconds_value(suggested_end_sec)
            current["suggested_clip_end_time"] = _format_readable_time(suggested_end_sec)
        updated.append(current)
    return updated


def _add_video_link_times(video_link_rows: list[dict[str, str]], candidate_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    candidate_ranges: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in candidate_rows:
        source_video_id = str(row.get("source_video_id") or "").strip()
        start_sec = _safe_float(row.get("start_sec"))
        end_sec = _safe_float(row.get("end_sec"))
        if source_video_id and start_sec is not None and end_sec is not None:
            candidate_ranges[source_video_id].append((start_sec, end_sec))

    updated: list[dict[str, str]] = []
    for row in video_link_rows:
        current = dict(row)
        source_video_id = str(current.get("source_video_id") or "").strip()
        ranges = candidate_ranges.get(source_video_id, [])
        if ranges:
            min_start_sec = min(start for start, _ in ranges)
            max_end_sec = max(end for _, end in ranges)
        else:
            min_start_sec = _safe_float(current.get("min_start_sec"))
            max_end_sec = _safe_float(current.get("max_end_sec"))
        if min_start_sec is not None:
            suggested_min_start_sec = max(min_start_sec - 10.0, 0.0)
            current["min_start_time"] = _format_readable_time(min_start_sec)
            current["suggested_min_start_sec"] = _format_seconds_value(suggested_min_start_sec)
            current["suggested_min_start_time"] = _format_readable_time(suggested_min_start_sec)
        if max_end_sec is not None:
            suggested_max_end_sec = max_end_sec + 10.0
            current["max_end_time"] = _format_readable_time(max_end_sec)
            current["suggested_max_end_sec"] = _format_seconds_value(suggested_max_end_sec)
            current["suggested_max_end_time"] = _format_readable_time(suggested_max_end_sec)
        updated.append(current)
    return updated


def _extend_fields(existing_fields: list[str], new_fields: tuple[str, ...]) -> list[str]:
    fields = list(existing_fields)
    for field in new_fields:
        if field not in fields:
            fields.append(field)
    return fields


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _assert_writable(path: Path) -> None:
    with path.open("a", encoding="utf-8-sig", newline=""):
        pass


def _safe_float(value: str | None) -> float | None:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return None


def _format_seconds_value(seconds: float) -> str:
    return f"{seconds:.1f}"


def _format_readable_time(seconds: float) -> str:
    safe_seconds = max(seconds, 0.0)
    minutes = int(safe_seconds // 60)
    remaining_seconds = safe_seconds - minutes * 60
    return f"{minutes:02d}:{remaining_seconds:04.1f}"


if __name__ == "__main__":
    raise SystemExit(main())
