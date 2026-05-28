from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")

RAISE_HAND_CLIPS = (
    "20200908_17_494",
    "20220910_09_885",
    "20220207_22_536",
    "20230429_13_405",
    "20201123_07_705",
    "20211231_15_276",
    "20230429_13_331",
    "20230601_08_31",
)

STAND_CLIPS = (
    "20220822_08_1098",
    "20220218_01_4",
    "20230420_31_3",
    "20230430_15_1346",
    "20220804_20_2",
    "20221210_07_975",
    "20220314_02_3",
    "20220902_08_9",
)

EXTRA_FIELDS = (
    "selection_group",
    "selection_reason",
    "manual_review_status",
    "video_available",
    "selected_for_phase34",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Select Phase 3.4 SAV clips for manual review.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--source-csv", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    source_csv = args.source_csv.resolve() if args.source_csv else sav_root / "reports" / "sav_target_candidate_clips.csv"
    output_csv = args.output_csv.resolve() if args.output_csv else sav_root / "reports" / "selected_sav_candidates.csv"

    if not source_csv.exists():
        print("PHASE34_SELECTED_SAV_SOURCE_PRESENT=false")
        print(f"PHASE34_SELECTED_SAV_SOURCE_CSV={source_csv}")
        print("PHASE34_SELECTED_SAV_WRITTEN=false")
        print("PHASE34_SELECTED_SAV_TOTAL_COUNT=0")
        return 1

    rows, fieldnames = _read_rows(source_csv)
    rows_by_clip = {str(row.get("clip_id") or ""): row for row in rows}
    selected_rows: list[dict[str, str]] = []
    missing_clip_ids: list[str] = []

    for clip_id in RAISE_HAND_CLIPS:
        selected = _build_selected_row(
            rows_by_clip=rows_by_clip,
            clip_id=clip_id,
            selection_group="raise_hand",
            selection_reason="群体举手互动样本",
        )
        if selected is None:
            missing_clip_ids.append(clip_id)
            continue
        selected_rows.append(selected)

    for clip_id in STAND_CLIPS:
        selected = _build_selected_row(
            rows_by_clip=rows_by_clip,
            clip_id=clip_id,
            selection_group="stand",
            selection_reason="群体站立课堂状态样本",
        )
        if selected is None:
            missing_clip_ids.append(clip_id)
            continue
        selected_rows.append(selected)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_fields = list(fieldnames)
    for field in EXTRA_FIELDS:
        if field not in output_fields:
            output_fields.append(field)
    _write_rows(output_csv, output_fields, selected_rows)

    print("PHASE34_SELECTED_SAV_SOURCE_PRESENT=true")
    print(f"PHASE34_SELECTED_SAV_SOURCE_CSV={source_csv}")
    print(f"PHASE34_SELECTED_SAV_OUTPUT_CSV={output_csv}")
    for clip_id in missing_clip_ids:
        print(f"PHASE34_SELECTED_SAV_MISSING_CLIP_ID={clip_id}")
    print(f"PHASE34_SELECTED_SAV_WRITTEN={_bool_text(output_csv.exists())}")
    print(f"PHASE34_SELECTED_SAV_TOTAL_COUNT={len(selected_rows)}")
    print(f"PHASE34_SELECTED_SAV_RAISE_HAND_COUNT={sum(1 for row in selected_rows if row.get('selection_group') == 'raise_hand')}")
    print(f"PHASE34_SELECTED_SAV_STAND_COUNT={sum(1 for row in selected_rows if row.get('selection_group') == 'stand')}")
    print(f"PHASE34_SELECTED_SAV_ALL_SOURCE_MATCHED={_bool_text(not missing_clip_ids)}")
    return 0 if not missing_clip_ids and len(selected_rows) == 16 else 1


def _read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = list(reader.fieldnames or [])
        return list(reader), fieldnames


def _build_selected_row(
    *,
    rows_by_clip: dict[str, dict[str, str]],
    clip_id: str,
    selection_group: str,
    selection_reason: str,
) -> dict[str, str] | None:
    source_row = rows_by_clip.get(clip_id)
    if source_row is None:
        return None
    selected = dict(source_row)
    selected["selection_group"] = selection_group
    selected["selection_reason"] = selection_reason
    selected["manual_review_status"] = "pending"
    selected["video_available"] = "unknown"
    selected["selected_for_phase34"] = "pending"
    return selected


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
