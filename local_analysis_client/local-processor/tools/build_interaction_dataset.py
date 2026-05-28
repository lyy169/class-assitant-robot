from __future__ import annotations

import logging
import shutil
from collections import Counter
from pathlib import Path

import yaml


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
LOGGER = logging.getLogger("build_interaction_dataset")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = REPO_ROOT / "datasets"

HAND_SRC = DATASETS_DIR / "try-hand-raise.v12i.yolov11"
STANDING_SRC = DATASETS_DIR / "Standing People.v1-people.yolov11"
TARGET_ROOT = DATASETS_DIR / "interaction-standing-hand-v1"

SPLITS = ("train", "valid", "test")
CLASS_NAMES = ["hand-raising", "standing"]


def main() -> None:
    validate_source_dataset(HAND_SRC, "hand-raising")
    validate_source_dataset(STANDING_SRC, "standing")
    rebuild_target_root()

    class_counter: Counter[int] = Counter()
    image_counter: Counter[str] = Counter()

    for split in SPLITS:
        LOGGER.info("Processing split=%s", split)
        image_counter[split] += copy_split(HAND_SRC, split, "hand", target_class_id=0, class_counter=class_counter)
        image_counter[split] += copy_split(STANDING_SRC, split, "standing", target_class_id=1, class_counter=class_counter)

    write_data_yaml()
    write_dataset_notes()

    LOGGER.info("Dataset build finished: %s", TARGET_ROOT)
    for split in SPLITS:
        LOGGER.info("split=%s image_count=%s", split, image_counter[split])
    for class_id, count in sorted(class_counter.items()):
        LOGGER.info("class_id=%s class_name=%s label_count=%s", class_id, CLASS_NAMES[class_id], count)


def validate_source_dataset(root: Path, display_name: str) -> None:
    if not root.exists():
        raise FileNotFoundError(f"Source dataset not found: {root}")
    for split in SPLITS:
        images_dir = root / split / "images"
        labels_dir = root / split / "labels"
        if not images_dir.exists() or not labels_dir.exists():
            raise FileNotFoundError(f"Missing split folders in {root}: {split}")
    LOGGER.info("Validated source dataset for %s: %s", display_name, root)


def rebuild_target_root() -> None:
    if TARGET_ROOT.exists():
        LOGGER.info("Removing existing target dataset: %s", TARGET_ROOT)
        shutil.rmtree(TARGET_ROOT)

    for split in SPLITS:
        (TARGET_ROOT / split / "images").mkdir(parents=True, exist_ok=True)
        (TARGET_ROOT / split / "labels").mkdir(parents=True, exist_ok=True)


def copy_split(
    src_root: Path,
    split: str,
    prefix: str,
    *,
    target_class_id: int,
    class_counter: Counter[int],
) -> int:
    src_images = src_root / split / "images"
    src_labels = src_root / split / "labels"
    copied_images = 0

    for image_path in sorted(src_images.iterdir()):
        if not image_path.is_file():
            continue

        label_path = src_labels / f"{image_path.stem}.txt"
        if not label_path.exists():
            LOGGER.warning("Label not found for image: %s", image_path)
            continue

        target_name = f"{prefix}_{image_path.name}"
        target_image_path = TARGET_ROOT / split / "images" / target_name
        target_label_path = TARGET_ROOT / split / "labels" / f"{Path(target_name).stem}.txt"

        shutil.copy2(image_path, target_image_path)
        converted_lines = remap_label_file(label_path, target_class_id)
        target_label_path.write_text("\n".join(converted_lines) + ("\n" if converted_lines else ""), encoding="utf-8")
        class_counter[target_class_id] += len(converted_lines)
        copied_images += 1

    return copied_images


def remap_label_file(label_path: Path, target_class_id: int) -> list[str]:
    converted_lines: list[str] = []
    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            LOGGER.warning("Skip malformed label in %s: %s", label_path, line)
            continue
        converted_lines.append(" ".join([str(target_class_id), *parts[1:]]))
    return converted_lines


def write_data_yaml() -> None:
    data = {
        "path": str(TARGET_ROOT),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(CLASS_NAMES),
        "names": CLASS_NAMES,
    }
    yaml_path = TARGET_ROOT / "data.yaml"
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    LOGGER.info("Wrote dataset yaml: %s", yaml_path)


def write_dataset_notes() -> None:
    notes = (
        "This dataset is built by combining two single-class datasets:\n"
        "- try-hand-raise.v12i.yolov11 -> class 0: hand-raising\n"
        "- Standing People.v1-people.yolov11 -> class 1: standing\n\n"
        "Important caveat:\n"
        "The source datasets were annotated independently, so some images may contain unlabeled objects from the other target class.\n"
        "Use this merged dataset as a practical baseline and validate carefully on classroom data.\n"
    )
    notes_path = TARGET_ROOT / "README.merge.txt"
    notes_path.write_text(notes, encoding="utf-8")
    LOGGER.info("Wrote dataset notes: %s", notes_path)


if __name__ == "__main__":
    main()
