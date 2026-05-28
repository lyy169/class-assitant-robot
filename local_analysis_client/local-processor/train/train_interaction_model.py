from __future__ import annotations

import logging
from pathlib import Path

import torch
from ultralytics import YOLO
import ultralytics.data.base as data_base
import ultralytics.data.dataset as data_dataset
import ultralytics.data.utils as data_utils


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
LOGGER = logging.getLogger("train_interaction_model")

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_YAML = REPO_ROOT / "datasets" / "interaction-standing-hand-v1" / "data.yaml"
MODEL_PATH = REPO_ROOT / "yolo11n.pt"


class SequentialPool:
    """Minimal pool interface used by Ultralytics cache-building code."""

    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def imap(self, func, iterable):
        for item in iterable:
            yield func(item)


def apply_windows_threadpool_patch() -> None:
    """Avoid Windows permission issues from multiprocessing-backed ThreadPool in restricted environments."""
    data_dataset.ThreadPool = SequentialPool
    data_base.ThreadPool = SequentialPool
    data_utils.ThreadPool = SequentialPool
    LOGGER.info("Applied sequential pool compatibility patch for Windows training")


def main() -> None:
    if not DATA_YAML.exists():
        raise FileNotFoundError(
            f"Merged dataset yaml not found: {DATA_YAML}. Run `python build_interaction_dataset.py` first."
        )

    LOGGER.info("Start training interaction model")
    LOGGER.info("model=%s", MODEL_PATH)
    LOGGER.info("data=%s", DATA_YAML)

    apply_windows_threadpool_patch()
    device = 0 if torch.cuda.is_available() else "cpu"
    batch = 16 if torch.cuda.is_available() else 8
    LOGGER.info("training_device=%s", device)
    LOGGER.info("training_batch=%s", batch)

    model = YOLO(str(MODEL_PATH))
    model.train(
        data=str(DATA_YAML),
        epochs=30,
        imgsz=640,
        batch=batch,
        cache=False,
        workers=0,
        project=str(REPO_ROOT / "runs" / "detect"),
        name="train_interaction_v1",
        exist_ok=True,
        pretrained=True,
        patience=20,
        device=device,
    )


if __name__ == "__main__":
    main()
