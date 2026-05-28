from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from yolo_interaction_processor import build_default_processor, resolve_config_path, validate_result_payload


DEFAULT_OUTPUT_DIR = REPO_ROOT / "processed_results" / "validation"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the local interaction analysis pipeline with saved keyframes.")
    parser.add_argument("--window-dir", type=Path, default=None, help="Path to a saved keyframe window directory.")
    args = parser.parse_args()

    window_dir = resolve_window_dir(args.window_dir)
    request_meta = load_request_meta(window_dir)
    frame_paths = sorted(str(path) for path in window_dir.glob("*.jpg"))
    if not frame_paths:
        raise FileNotFoundError(f"No JPEG frames found under {window_dir}")

    processor = build_default_processor(resolve_config_path())
    processor.config.cloud_push_enabled = False
    processor.config.output_dir = DEFAULT_OUTPUT_DIR
    processor.config.output_dir.mkdir(parents=True, exist_ok=True)

    result = processor.process_window(
        window_id=str(request_meta.get("window_id") or window_dir.name),
        frame_paths=frame_paths,
        window_timestamp=request_meta.get("timestamp"),
        frame_timestamps=request_meta.get("frame_timestamps"),
        metadata={
            "analysis_id": f"analysis_{request_meta.get('window_id') or window_dir.name}",
            "video_id": str(request_meta.get("video_id") or request_meta.get("window_id") or window_dir.name),
            "source_kind": "captured_video",
            "source_path": str(window_dir),
            "source_host": "raspberrypi-01",
            "recorded_at": request_meta.get("timestamp"),
            "device_id": request_meta.get("device_id"),
            "classroom_id": request_meta.get("classroom_id"),
            "received_dir": str(window_dir),
            "validation_mode": True,
            "teacher_transcript_segments": [
                {"start_sec": 2, "end_sec": 6, "text": "谁来回答一下这个问题？"},
                {"start_sec": 10, "end_sec": 16, "text": "我们继续看这一段内容。"},
            ],
            "timeline": {
                "window_size_seconds": 20,
                "heat_curve": [0.12],
            },
        },
    )
    validation_report = validate_result_payload(result)

    print(json.dumps(
        {
            "window_dir": str(window_dir),
            "result_path": str(processor.config.output_dir / f"{request_meta.get('window_id') or window_dir.name}.json"),
            "payload_validation": validation_report,
            "analysis_id": result.get("analysis_id"),
            "summary": result.get("summary", {}),
        },
        ensure_ascii=False,
        indent=2,
    ))


def resolve_window_dir(window_dir: Path | None) -> Path:
    if window_dir is not None:
        return window_dir.resolve()

    candidates = sorted(
        (path for path in (REPO_ROOT / "received_keyframes").rglob("*") if path.is_dir() and list(path.glob("*.jpg"))),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No saved keyframe window directories were found under received_keyframes/")
    return candidates[0]


def load_request_meta(window_dir: Path) -> dict[str, Any]:
    request_meta_path = window_dir / "request_meta.json"
    if not request_meta_path.exists():
        return {}
    return json.loads(request_meta_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
