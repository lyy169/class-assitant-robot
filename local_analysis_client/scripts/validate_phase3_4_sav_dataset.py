from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")
REQUIRED_LABELS = {
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
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.4 SAV dataset workspace and generated reports.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    label_map_path = sav_root / "reports" / "sav_label_map.csv"
    summary_path = sav_root / "reports" / "sav_clip_action_summary.csv"
    candidate_path = sav_root / "reports" / "sav_target_candidate_clips.csv"
    required_source_files = (
        sav_root / "annotations" / "education_first_label.pbtxt",
        sav_root / "annotations" / "train.csv",
        sav_root / "annotations" / "val.csv",
    )
    report_files = (label_map_path, summary_path, candidate_path)

    workspace_present = sav_root.is_dir()
    files_present = all(path.exists() for path in required_source_files)
    reports_present = all(path.exists() for path in report_files)
    labels = _read_label_map(label_map_path) if label_map_path.exists() else set()
    candidates = _read_rows(candidate_path) if candidate_path.exists() else []
    required_labels_present = REQUIRED_LABELS.issubset(labels)
    stand_candidates_present = any(int(row.get("stand_count") or 0) > 0 for row in candidates)
    raise_hand_candidates_present = any(int(row.get("raise_hand_count") or 0) > 0 for row in candidates)
    dataset_prep_ok = bool(
        workspace_present
        and files_present
        and reports_present
        and required_labels_present
        and (stand_candidates_present or raise_hand_candidates_present)
    )

    print(f"PHASE34_SAV_WORKSPACE_PRESENT={_bool_text(workspace_present)}")
    print(f"PHASE34_SAV_FILES_PRESENT={_bool_text(files_present)}")
    print(f"PHASE34_SAV_LABEL_COUNT={len(labels)}")
    print(f"PHASE34_SAV_REQUIRED_LABELS_PRESENT={_bool_text(required_labels_present)}")
    print(f"PHASE34_SAV_REPORTS_PRESENT={_bool_text(reports_present)}")
    print(f"PHASE34_SAV_STAND_CANDIDATES_PRESENT={_bool_text(stand_candidates_present)}")
    print(f"PHASE34_SAV_RAISE_HAND_CANDIDATES_PRESENT={_bool_text(raise_hand_candidates_present)}")
    print(f"PHASE34_SAV_DATASET_PREP_OK={_bool_text(dataset_prep_ok)}")
    return 0 if dataset_prep_ok else 1


def _read_label_map(path: Path) -> set[str]:
    labels: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            label = str(row.get("action_name") or "").strip()
            if label:
                labels.add(label)
    return labels


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
