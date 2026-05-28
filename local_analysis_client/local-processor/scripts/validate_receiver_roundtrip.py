from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import keyframe_receiver


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the receiver -> analysis -> result pipeline via FastAPI TestClient.")
    parser.add_argument("--sample-dir", type=Path, default=None, help="Path to an existing saved keyframe directory.")
    parser.add_argument("--window-id", default="validation_receiver_window", help="Window id used for the simulated upload.")
    args = parser.parse_args()

    sample_dir = resolve_sample_dir(args.sample_dir)
    image_paths = sorted(sample_dir.glob("*.jpg"))
    if not image_paths:
        raise FileNotFoundError(f"No JPEG frames found under {sample_dir}")

    receiver_module = keyframe_receiver._MODULE
    receiver_module.PROCESSOR.config.cloud_push_enabled = False
    receiver_module.PROCESSOR.config.output_dir = REPO_ROOT / "processed_results" / "validation_receiver"
    receiver_module.PROCESSOR.config.output_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(keyframe_receiver.app)
    files = []
    handles = []
    for image_path in image_paths:
        handle = image_path.open("rb")
        handles.append(handle)
        files.append(("images", (image_path.name, handle, "image/jpeg")))

    try:
        response = client.post(
            "/api/keyframes",
            data={
                "window_id": args.window_id,
                "timestamp": "1776254775",
                "device_id": "pi-test-001",
                "classroom_id": "room-test-001",
                "frame_timestamps": "[1776254775,1776254777,1776254779]",
                "metadata_json": json.dumps(
                    {
                        "trigger": "validate_receiver_roundtrip",
                        "analysis_id": f"analysis_{args.window_id}",
                        "video_id": f"video_{args.window_id}",
                        "source_kind": "captured_video",
                        "source_path": str(sample_dir),
                        "source_host": "raspberrypi-01",
                        "recorded_at": "2026-04-17T09:00:00Z",
                        "teacher_transcript_segments": [
                            {"start_sec": 1, "end_sec": 5, "text": "谁来回答一下这个问题？"},
                            {"start_sec": 6, "end_sec": 12, "text": "我们把这个结论总结一下。"},
                        ],
                        "timeline": {
                            "window_size_seconds": 20,
                            "heat_curve": [0.22],
                        },
                    },
                    ensure_ascii=False,
                ),
            },
            files=files,
        )
    finally:
        for handle in handles:
            handle.close()

    print(response.status_code)
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def resolve_sample_dir(sample_dir: Path | None) -> Path:
    if sample_dir is not None:
        return sample_dir.resolve()

    candidates = sorted(
        (path for path in (REPO_ROOT / "received_keyframes").rglob("*") if path.is_dir() and list(path.glob("*.jpg"))),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No sample keyframe directories were found under received_keyframes/")
    return candidates[0]


if __name__ == "__main__":
    main()
