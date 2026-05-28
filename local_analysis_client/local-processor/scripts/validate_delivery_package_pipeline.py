from __future__ import annotations

import json
from pathlib import Path
import sys
import wave

import cv2
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from classroom_feedback_pipeline import analyze_delivery_package


SAMPLE_PACKAGE_DIR = REPO_ROOT / "captures_local_delivery" / "classroom_101" / "2026-04-17" / "session_001"


def main() -> None:
    package_dir = build_sample_delivery_package(SAMPLE_PACKAGE_DIR)
    result = analyze_delivery_package(package_dir, upload_mode="auto")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_sample_delivery_package(package_dir: Path) -> Path:
    package_dir.mkdir(parents=True, exist_ok=True)
    image_dir = REPO_ROOT / "scripts" / "sample_keyframes"
    image_paths = sorted(image_dir.glob("*.jpg"))
    if not image_paths:
        raise FileNotFoundError(f"No sample images found in {image_dir}")

    video_path = package_dir / "video.mp4"
    audio_path = package_dir / "audio.wav"
    metadata_path = package_dir / "metadata.json"
    transcript_path = package_dir / "teacher_transcript.json"

    first_frame = cv2.imread(str(image_paths[0]))
    if first_frame is None:
        raise RuntimeError(f"Failed to read sample image: {image_paths[0]}")
    height, width = first_frame.shape[:2]
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 1.0, (width, height))
    try:
        for _ in range(4):
            for image_path in image_paths:
                frame = cv2.imread(str(image_path))
                writer.write(frame)
    finally:
        writer.release()

    generate_sample_audio(audio_path, duration_seconds=12)

    metadata = {
        "classroom_id": "classroom_101",
        "session_id": "session_001",
        "source_host": "raspberrypi-01",
        "source_kind": "captured_video",
        "source_path": "captures/classroom_101/2026-04-17/session_001/video.mp4",
        "started_at": "2026-04-17T09:00:00Z",
        "ended_at": "2026-04-17T09:00:12Z",
        "duration_seconds": 12,
        "analysis_id": "cls_20260417_101_001",
        "video_id": "video_20260417_001",
        "teacher_transcript_segments": [
            {"start_sec": 1, "end_sec": 6, "text": "这一段是 metadata fallback 文本。"},
        ],
        "students": {
            "estimated_student_count": 36,
            "zones": {
                "front": {"avg_attention_ratio": 0.83},
                "middle": {"avg_attention_ratio": 0.75},
                "back": {"avg_attention_ratio": 0.61},
            },
        },
        "window_size_seconds": 4,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    transcript_payload = {
        "segments": [
            {"start_sec": 1, "end_sec": 4, "text": "谁来回答一下这个问题？"},
            {"start_sec": 5, "end_sec": 9, "text": "大家想一想，这一步为什么这样做。"},
            {"start_sec": 9, "end_sec": 11, "text": "我们把今天的重点总结一下。"},
        ]
    }
    transcript_path.write_text(json.dumps(transcript_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return package_dir


def generate_sample_audio(audio_path: Path, *, duration_seconds: int) -> None:
    sample_rate = 16000
    timeline = np.linspace(0, duration_seconds, sample_rate * duration_seconds, endpoint=False)
    signal = np.zeros_like(timeline)
    signal += 0.1 * np.sin(2 * np.pi * 220 * timeline)
    signal[(timeline >= 4) & (timeline < 8)] += 0.35 * np.sin(2 * np.pi * 440 * timeline[(timeline >= 4) & (timeline < 8)])
    signal[(timeline >= 8) & (timeline < 12)] += 0.2 * np.sin(2 * np.pi * 330 * timeline[(timeline >= 8) & (timeline < 12)])
    pcm = np.int16(np.clip(signal, -1.0, 1.0) * 32767)
    with wave.open(str(audio_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main()
