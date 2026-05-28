from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
FIRST_SAMPLE_CLIP_ID = "20200908_17_494"
FIRST_SAMPLE_METADATA = {
    "manual_review_status": "passed",
    "selected_for_phase34": "yes",
    "manual_observation": "几乎全班同学举手，且有两个学生站立",
    "candidate_type": "群体举手 + 站立互动",
    "notes": "首个 Phase 3.4 SAV 手动切片样本，约 30 秒",
}
REGISTRY_FIELDS = (
    "clip_id",
    "source_video_id",
    "selection_group",
    "selection_reason",
    "official_start_time",
    "official_end_time",
    "suggested_clip_start_time",
    "suggested_clip_end_time",
    "manual_clip_path",
    "manual_clip_exists",
    "manual_review_status",
    "selected_for_phase34",
    "manual_observation",
    "candidate_type",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Register manually clipped SAV samples for Phase 3.4.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--selected-csv", type=Path, default=None)
    parser.add_argument("--manual-clips-dir", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    selected_csv = args.selected_csv.resolve() if args.selected_csv else sav_root / "reports" / "selected_sav_candidates.csv"
    manual_clips_dir = args.manual_clips_dir.resolve() if args.manual_clips_dir else sav_root / "manual_clips"
    output_csv = args.output_csv.resolve() if args.output_csv else sav_root / "reports" / "manual_clip_registry.csv"

    manual_clips_dir.mkdir(parents=True, exist_ok=True)
    if not selected_csv.exists():
        print(f"PHASE34_MANUAL_CLIP_SELECTED_CSV={selected_csv}")
        print("PHASE34_MANUAL_CLIP_SELECTED_CSV_PRESENT=false")
        print("PHASE34_MANUAL_CLIP_REGISTRY_WRITTEN=false")
        return 1

    selected_rows = _read_rows(selected_csv)
    selected_by_clip_id = {str(row.get("clip_id") or "").strip(): row for row in selected_rows}
    registry_rows = []
    unmatched_clip_ids = []

    for clip_path in sorted(manual_clips_dir.glob("*.mp4")):
        clip_id = clip_path.stem
        selected_row = selected_by_clip_id.get(clip_id)
        if selected_row is None:
            unmatched_clip_ids.append(clip_id)
            continue
        registry_rows.append(_build_registry_row(selected_row, clip_path))

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    _write_rows(output_csv, registry_rows)

    first_sample_present = (manual_clips_dir / f"{FIRST_SAMPLE_CLIP_ID}.mp4").exists()
    first_sample_registered = any(row.get("clip_id") == FIRST_SAMPLE_CLIP_ID for row in registry_rows)
    print(f"PHASE34_MANUAL_CLIP_DIR={manual_clips_dir}")
    print(f"PHASE34_MANUAL_CLIP_REGISTRY={output_csv}")
    for clip_id in unmatched_clip_ids:
        print(f"PHASE34_MANUAL_CLIP_UNMATCHED_CLIP_ID={clip_id}")
    print(f"PHASE34_MANUAL_CLIP_COUNT={len(registry_rows)}")
    print(f"PHASE34_MANUAL_CLIP_FIRST_SAMPLE_PRESENT={_bool_text(first_sample_present)}")
    print(f"PHASE34_MANUAL_CLIP_FIRST_SAMPLE_REGISTERED={_bool_text(first_sample_registered)}")
    print(f"PHASE34_MANUAL_CLIP_REGISTRY_WRITTEN={_bool_text(output_csv.exists())}")
    return 0 if registry_rows and first_sample_present and first_sample_registered else 1


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _build_registry_row(selected_row: dict[str, str], clip_path: Path) -> dict[str, str]:
    clip_id = str(selected_row.get("clip_id") or "").strip()
    metadata = FIRST_SAMPLE_METADATA if clip_id == FIRST_SAMPLE_CLIP_ID else {
        "manual_review_status": "pending",
        "selected_for_phase34": "pending",
        "manual_observation": "",
        "candidate_type": "",
        "notes": "",
    }
    return {
        "clip_id": clip_id,
        "source_video_id": str(selected_row.get("source_video_id") or ""),
        "selection_group": str(selected_row.get("selection_group") or ""),
        "selection_reason": str(selected_row.get("selection_reason") or ""),
        "official_start_time": str(selected_row.get("official_start_time") or ""),
        "official_end_time": str(selected_row.get("official_end_time") or ""),
        "suggested_clip_start_time": str(selected_row.get("suggested_clip_start_time") or ""),
        "suggested_clip_end_time": str(selected_row.get("suggested_clip_end_time") or ""),
        "manual_clip_path": str(clip_path),
        "manual_clip_exists": _bool_text(clip_path.exists()),
        "manual_review_status": metadata["manual_review_status"],
        "selected_for_phase34": metadata["selected_for_phase34"],
        "manual_observation": metadata["manual_observation"],
        "candidate_type": metadata["candidate_type"],
        "notes": metadata["notes"],
    }


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REGISTRY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in REGISTRY_FIELDS})


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
