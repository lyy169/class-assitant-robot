from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_SAV_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV")

REQUIRED_DIRECTORIES = (
    "annotations",
    "frame_list",
    "source_files",
    "candidate_clips",
    "selected_clips",
    "reports",
    "clip_packages",
)

REQUIRED_FILES = {
    "PHASE34_SAV_ANNOTATION_LABEL_PRESENT": Path("annotations") / "education_first_label.pbtxt",
    "PHASE34_SAV_ANNOTATION_TRAIN_PRESENT": Path("annotations") / "train.csv",
    "PHASE34_SAV_ANNOTATION_VAL_PRESENT": Path("annotations") / "val.csv",
    "PHASE34_SAV_FRAME_LIST_TRAIN_PRESENT": Path("frame_list") / "train.csv",
    "PHASE34_SAV_FRAME_LIST_VAL_PRESENT": Path("frame_list") / "val.csv",
    "PHASE34_SAV_CLIPS_TO_KEEP_PRESENT": Path("source_files") / "clips_to_keep.txt",
    "PHASE34_SAV_VIDEO_LINK_PRESENT": Path("source_files") / "video_link.txt",
}

README_SECTION_MARKER = "<!-- PHASE34_SAV_WORKSPACE_V1 -->"
README_TEXT = f"""{README_SECTION_MARKER}
# SAV Dataset Workspace

This directory is the local organization workspace for the SAV dataset in this project.

Google Drive files must be downloaded manually by the user. Codex/CLI only prepares the local directory structure and validation scripts; it does not log in to Google Drive or download dataset files.

Place files in these locations:

- `annotations\\education_first_label.pbtxt`
- `annotations\\train.csv`
- `annotations\\val.csv`
- `frame_list\\train.csv`
- `frame_list\\val.csv`
- `source_files\\clips_to_keep.txt`
- `source_files\\video_link.txt`

There are two different `train.csv` files:

- `frame_list\\train.csv` contains frame paths such as `img_000001.jpg`.
- `annotations\\train.csv` contains annotation rows with bbox, action_id, and person_id.

Current Phase 3.4 only parses annotations and the label map first. Video download and manual clip screening will be done later.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare local SAV dataset workspace for Phase 3.4.")
    parser.add_argument("--sav-root", type=Path, default=DEFAULT_SAV_ROOT)
    args = parser.parse_args()

    sav_root = args.sav_root.resolve()
    workspace_created = _prepare_workspace(sav_root)
    _ensure_readme(sav_root / "README.md")
    presence = {marker: (sav_root / relative_path).exists() for marker, relative_path in REQUIRED_FILES.items()}
    parse_ready = all(
        presence[key]
        for key in (
            "PHASE34_SAV_ANNOTATION_LABEL_PRESENT",
            "PHASE34_SAV_ANNOTATION_TRAIN_PRESENT",
            "PHASE34_SAV_ANNOTATION_VAL_PRESENT",
        )
    )

    print(f"PHASE34_SAV_WORKSPACE_CREATED={_bool_text(workspace_created)}")
    for marker in REQUIRED_FILES:
        print(f"{marker}={_bool_text(presence[marker])}")
    print(f"PHASE34_SAV_REQUIRED_FOR_PARSE_READY={_bool_text(parse_ready)}")
    if not parse_ready:
        print("PHASE34_SAV_PARSE_HINT=Place annotations\\education_first_label.pbtxt, annotations\\train.csv, and annotations\\val.csv, then rerun parse.")
    return 0


def _prepare_workspace(sav_root: Path) -> bool:
    sav_root.mkdir(parents=True, exist_ok=True)
    for directory in REQUIRED_DIRECTORIES:
        (sav_root / directory).mkdir(parents=True, exist_ok=True)
    return sav_root.exists() and all((sav_root / directory).is_dir() for directory in REQUIRED_DIRECTORIES)


def _ensure_readme(readme_path: Path) -> None:
    if not readme_path.exists():
        readme_path.write_text(README_TEXT, encoding="utf-8")
        return
    current_text = readme_path.read_text(encoding="utf-8", errors="ignore")
    if README_SECTION_MARKER not in current_text:
        readme_path.write_text(current_text.rstrip() + "\n\n" + README_TEXT, encoding="utf-8")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
