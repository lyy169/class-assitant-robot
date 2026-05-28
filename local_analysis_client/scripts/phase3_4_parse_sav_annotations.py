from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
EXPECTED_LABELS = (
    "sit",
    "stand",
    "look_forward",
    "look_sideways",
    "read",
    "flip_books",
    "touch_sth",
    "raise_hand",
    "hands_down",
    "take_notes",
    "applaud",
    "bend",
    "turn_around",
    "talk_with_others",
    "answer_questions",
)
COUNT_FIELDS = tuple(f"{name}_count" for name in EXPECTED_LABELS)
TARGET_ACTIONS = {
    "stand",
    "raise_hand",
    "bend",
    "look_sideways",
    "turn_around",
    "talk_with_others",
    "answer_questions",
}
HIGH_ACTIONS = {"raise_hand", "stand"}
MEDIUM_ACTIONS = {"bend", "look_sideways", "turn_around", "talk_with_others", "answer_questions"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse SAV annotation CSVs and generate Phase 3.4 candidate clip reports.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    output_dir = args.output_dir.resolve() if args.output_dir else sav_root / "reports"
    markers: dict[str, Any] = {
        "PHASE34_SAV_LABEL_MAP_VALID": False,
        "PHASE34_SAV_ANNOTATION_TRAIN_VALID": False,
        "PHASE34_SAV_ANNOTATION_VAL_VALID": False,
        "PHASE34_SAV_CLIP_SUMMARY_GENERATED": False,
        "PHASE34_SAV_TARGET_CANDIDATES_GENERATED": False,
        "PHASE34_SAV_TOTAL_CLIP_COUNT": 0,
        "PHASE34_SAV_TARGET_CANDIDATE_COUNT": 0,
        "PHASE34_SAV_HIGH_CANDIDATE_COUNT": 0,
    }

    if not sav_root.exists():
        print(f"PHASE34_SAV_PARSE_HINT=Workspace missing. Run: python scripts\\phase3_4_prepare_sav_workspace.py --sav-root \"{sav_root}\"")
        _print_markers(markers)
        return 0

    label_path = sav_root / "annotations" / "education_first_label.pbtxt"
    train_path = sav_root / "annotations" / "train.csv"
    val_path = sav_root / "annotations" / "val.csv"
    missing = [str(path) for path in (label_path, train_path, val_path) if not path.exists()]
    if missing:
        print("PHASE34_SAV_PARSE_HINT=Missing required files for parsing:")
        for path in missing:
            print(f"PHASE34_SAV_MISSING_FILE={path}")
        print("PHASE34_SAV_PARSE_HINT=Place the missing files and rerun scripts\\phase3_4_parse_sav_annotations.py.")
        _print_markers(markers)
        return 0

    label_map = _parse_label_map(label_path)
    markers["PHASE34_SAV_LABEL_MAP_VALID"] = bool(label_map)
    train_rows, train_valid = _read_annotation_rows(train_path, split="train", label_map=label_map)
    val_rows, val_valid = _read_annotation_rows(val_path, split="val", label_map=label_map)
    markers["PHASE34_SAV_ANNOTATION_TRAIN_VALID"] = train_valid
    markers["PHASE34_SAV_ANNOTATION_VAL_VALID"] = val_valid

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_label_map(output_dir / "sav_label_map.csv", label_map)
    summary_rows = _build_clip_summary(train_rows + val_rows, label_map)
    candidates = _build_target_candidates(summary_rows)
    _write_rows(output_dir / "sav_clip_action_summary.csv", summary_rows)
    _write_rows(output_dir / "sav_target_candidate_clips.csv", candidates)

    markers["PHASE34_SAV_CLIP_SUMMARY_GENERATED"] = bool(summary_rows)
    markers["PHASE34_SAV_TARGET_CANDIDATES_GENERATED"] = True
    markers["PHASE34_SAV_TOTAL_CLIP_COUNT"] = len(summary_rows)
    markers["PHASE34_SAV_TARGET_CANDIDATE_COUNT"] = len(candidates)
    markers["PHASE34_SAV_HIGH_CANDIDATE_COUNT"] = sum(1 for row in candidates if row.get("recommended_level") == "high")
    _print_markers(markers)
    return 0


def _parse_label_map(path: Path) -> dict[int, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    item_blocks = re.findall(r"item\s*\{(.*?)\}", text, flags=re.DOTALL)
    label_map: dict[int, str] = {}
    blocks = item_blocks if item_blocks else [text]
    for block in blocks:
        id_match = re.search(r"(?:id|label_id)\s*:\s*(\d+)", block)
        name_match = re.search(r"(?:name|display_name)\s*:\s*['\"]([^'\"]+)['\"]", block)
        if not id_match or not name_match:
            continue
        label_map[int(id_match.group(1))] = _normalize_label_name(name_match.group(1))
    return dict(sorted(label_map.items()))


def _read_annotation_rows(path: Path, *, split: str, label_map: dict[int, str]) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    valid = True
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        for line_number, row in enumerate(reader, start=1):
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) < 8:
                print(f"PHASE34_SAV_INVALID_ROW={path}:{line_number}:expected_8_columns")
                valid = False
                continue
            try:
                action_id = int(float(row[6]))
                person_id = str(row[7]).strip()
                parsed = {
                    "split": split,
                    "clip_id": row[0].strip(),
                    "timestamp": float(row[1]),
                    "x1": float(row[2]),
                    "y1": float(row[3]),
                    "x2": float(row[4]),
                    "y2": float(row[5]),
                    "action_id": action_id,
                    "person_id": person_id,
                }
            except ValueError:
                print(f"PHASE34_SAV_INVALID_ROW={path}:{line_number}:parse_failed")
                valid = False
                continue
            if action_id not in label_map:
                print(f"PHASE34_SAV_UNKNOWN_ACTION_ID={path}:{line_number}:{action_id}")
                valid = False
            rows.append(parsed)
    return rows, valid and bool(rows)


def _build_clip_summary(rows: list[dict[str, Any]], label_map: dict[int, str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["split"]), str(row["clip_id"]))].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (split, clip_id), items in sorted(grouped.items(), key=lambda value: (value[0][0], value[0][1])):
        source_video_id, clip_index = _split_clip_id(clip_id)
        start_sec = round(((clip_index - 1) * 2 + 1.5), 2) if clip_index > 0 else 0.0
        end_sec = round(start_sec + 3.0, 2)
        action_counter: Counter[str] = Counter(label_map.get(int(item["action_id"]), f"unknown_{item['action_id']}") for item in items)
        action_ids = sorted({int(item["action_id"]) for item in items})
        action_names = [label_map.get(action_id, f"unknown_{action_id}") for action_id in action_ids]
        target_action_names = [name for name in action_names if name in TARGET_ACTIONS]
        row: dict[str, Any] = {
            "split": split,
            "clip_id": clip_id,
            "source_video_id": source_video_id,
            "clip_index": clip_index,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "person_count": len({str(item["person_id"]) for item in items}),
            "action_ids": ";".join(str(action_id) for action_id in action_ids),
            "action_names": ";".join(action_names),
        }
        for name in EXPECTED_LABELS:
            row[f"{name}_count"] = int(action_counter.get(name, 0))
        row["target_action_names"] = ";".join(target_action_names)
        row["recommended_level"] = _recommended_level(action_counter)
        summary_rows.append(row)
    return summary_rows


def _build_target_candidates(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [row for row in summary_rows if row.get("recommended_level") in {"high", "medium"}]
    level_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        candidates,
        key=lambda row: (
            level_rank.get(str(row.get("recommended_level")), 9),
            -int(row.get("raise_hand_count") or 0),
            -int(row.get("stand_count") or 0),
            -int(row.get("person_count") or 0),
            str(row.get("clip_id") or ""),
        ),
    )


def _recommended_level(action_counter: Counter[str]) -> str:
    if any(action_counter.get(action, 0) > 0 for action in HIGH_ACTIONS):
        return "high"
    if any(action_counter.get(action, 0) > 0 for action in MEDIUM_ACTIONS):
        return "medium"
    return "low"


def _split_clip_id(clip_id: str) -> tuple[str, int]:
    parts = clip_id.rsplit("_", 1)
    if len(parts) != 2:
        return clip_id, 0
    try:
        return parts[0], int(parts[1])
    except ValueError:
        return parts[0], 0


def _write_label_map(path: Path, label_map: dict[int, str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=("action_id", "action_name"))
        writer.writeheader()
        for action_id, action_name in sorted(label_map.items()):
            writer.writerow({"action_id": action_id, "action_name": action_name})


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = (
        "split",
        "clip_id",
        "source_video_id",
        "clip_index",
        "start_sec",
        "end_sec",
        "person_count",
        "action_ids",
        "action_names",
        *COUNT_FIELDS,
        "target_action_names",
        "recommended_level",
    )
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _normalize_label_name(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _print_markers(markers: dict[str, Any]) -> None:
    for key in (
        "PHASE34_SAV_LABEL_MAP_VALID",
        "PHASE34_SAV_ANNOTATION_TRAIN_VALID",
        "PHASE34_SAV_ANNOTATION_VAL_VALID",
        "PHASE34_SAV_CLIP_SUMMARY_GENERATED",
        "PHASE34_SAV_TARGET_CANDIDATES_GENERATED",
        "PHASE34_SAV_TOTAL_CLIP_COUNT",
        "PHASE34_SAV_TARGET_CANDIDATE_COUNT",
        "PHASE34_SAV_HIGH_CANDIDATE_COUNT",
    ):
        value = markers[key]
        if isinstance(value, bool):
            value = "true" if value else "false"
        print(f"{key}={value}")


if __name__ == "__main__":
    raise SystemExit(main())
