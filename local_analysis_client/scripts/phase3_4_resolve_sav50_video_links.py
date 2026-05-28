from __future__ import annotations

import argparse
import csv
import re
from collections import OrderedDict
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
OUTPUT_FIELDS = (
    "source_video_id",
    "candidate_count",
    "clip_ids",
    "min_start_sec",
    "max_end_sec",
    "video_link",
    "link_found",
    "download_status",
    "local_video_path",
    "notes",
)
URL_RE = re.compile(r"https?://\S+")


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve video links for SAV-50 new Phase 3.4b candidates.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--candidates-csv", type=Path, default=None)
    parser.add_argument("--video-link-file", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    reports_dir = sav_root / "reports"
    candidates_csv = args.candidates_csv.resolve() if args.candidates_csv else reports_dir / "selected_sav50_candidates.csv"
    video_link_file = args.video_link_file.resolve() if args.video_link_file else sav_root / "source_files" / "video_link.txt"
    output_csv = args.output_csv.resolve() if args.output_csv else reports_dir / "selected_sav50_video_links.csv"

    if not candidates_csv.exists() or not video_link_file.exists():
        print(f"PHASE34_SAV50_CANDIDATES_PRESENT={_bool_text(candidates_csv.exists())}")
        print(f"PHASE34_SAV50_VIDEO_LINK_SOURCE_PRESENT={_bool_text(video_link_file.exists())}")
        print("PHASE34_SAV50_VIDEO_LINK_RESOLVE_OK=false")
        return 1

    new_rows = [row for row in _read_rows(candidates_csv) if row.get("candidate_origin") == "sav50_auto_selected"]
    grouped = _group_rows_by_source(new_rows)
    selected_source_ids = list(grouped.keys())
    link_map = _resolve_video_link_map(sav_root=sav_root, video_link_file=video_link_file, selected_source_ids=selected_source_ids)
    output_rows = []

    for source_video_id, rows in grouped.items():
        starts = [_safe_float(row.get("start_sec")) for row in rows if _safe_float(row.get("start_sec")) is not None]
        ends = [_safe_float(row.get("end_sec")) for row in rows if _safe_float(row.get("end_sec")) is not None]
        video_link = link_map.get(source_video_id, "")
        output_rows.append(
            {
                "source_video_id": source_video_id,
                "candidate_count": str(len(rows)),
                "clip_ids": ";".join(str(row.get("clip_id") or "") for row in rows),
                "min_start_sec": _format_number(min(starts)) if starts else "",
                "max_end_sec": _format_number(max(ends)) if ends else "",
                "video_link": video_link,
                "link_found": _bool_text(bool(video_link)),
                "download_status": "pending_manual_or_auto_download",
                "local_video_path": "",
                "notes": "" if video_link else "video_link_not_found",
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_rows(output_csv, output_rows)
    found_count = sum(1 for row in output_rows if row["link_found"] == "true")
    missing_count = len(output_rows) - found_count
    ok = bool(output_csv.exists() and len(new_rows) == 34 and found_count > 0)

    print(f"PHASE34_SAV50_VIDEO_LINK_FILE_PRESENT={_bool_text(output_csv.exists())}")
    print(f"PHASE34_SAV50_NEW_SOURCE_COUNT={len(output_rows)}")
    print(f"PHASE34_SAV50_VIDEO_LINK_FOUND_COUNT={found_count}")
    print(f"PHASE34_SAV50_VIDEO_LINK_MISSING_COUNT={missing_count}")
    print(f"PHASE34_SAV50_VIDEO_LINK_RESOLVE_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _group_rows_by_source(rows: list[dict[str, str]]) -> OrderedDict[str, list[dict[str, str]]]:
    grouped: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for row in rows:
        source_video_id = str(row.get("source_video_id") or "").strip()
        if source_video_id:
            grouped.setdefault(source_video_id, []).append(row)
    return grouped


def _resolve_video_link_map(*, sav_root: Path, video_link_file: Path, selected_source_ids: list[str]) -> dict[str, str]:
    lines = [line.strip() for line in video_link_file.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
    link_map = _resolve_direct_link_map(lines, selected_source_ids)
    missing_source_ids = [source_id for source_id in selected_source_ids if source_id not in link_map]
    if not missing_source_ids:
        return link_map
    positional_map = _resolve_positional_link_map(sav_root=sav_root, lines=lines)
    for source_id in missing_source_ids:
        if source_id in positional_map:
            link_map[source_id] = positional_map[source_id]
    return link_map


def _resolve_direct_link_map(lines: list[str], selected_source_ids: list[str]) -> dict[str, str]:
    link_map: dict[str, str] = {}
    selected_set = set(selected_source_ids)
    for line in lines:
        url = _extract_url(line)
        if not url:
            continue
        for source_id in selected_source_ids:
            if source_id in line:
                link_map[source_id] = url
        tokens = [token.strip() for token in re.split(r"[\t,\s]+", line) if token.strip()]
        if len(tokens) >= 2 and tokens[0] in selected_set and URL_RE.search(tokens[1]):
            link_map[tokens[0]] = _extract_url(tokens[1])
    return link_map


def _resolve_positional_link_map(*, sav_root: Path, lines: list[str]) -> dict[str, str]:
    summary_csv = sav_root / "reports" / "sav_clip_action_summary.csv"
    if not summary_csv.exists():
        return {}
    source_ids = sorted({str(row.get("source_video_id") or "").strip() for row in _read_rows(summary_csv) if row.get("source_video_id")})
    urls = [_extract_url(line) for line in lines]
    urls = [url for url in urls if url]
    if len(source_ids) != len(urls):
        return {}
    return dict(zip(source_ids, urls))


def _extract_url(value: str) -> str:
    match = URL_RE.search(value)
    return match.group(0).rstrip(",;") if match else ""


def _safe_float(value: str | None) -> float | None:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return None


def _format_number(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
