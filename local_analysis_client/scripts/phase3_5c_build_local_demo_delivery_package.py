from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
DEFAULT_DELIVERY_ROOT = REPO_ROOT / "captures_local_delivery"
DEMO_CLASSROOM_DIR = "classroom_local_imported_demo"
DEMO_DATE_DIR = "2026-05-23"
SAMPLE_ID = "local_imported_sav_full_classroom_20200908_17"
SOURCE_VIDEO_ID = "20200908_17"
PACKAGE_ID = "phase35_demo_local_imported_sav_full_classroom_20200908_17"
CLASSROOM_ID = "classroom_local_imported_demo"
SOURCE_DATASET = "SAV"
SOURCE_TYPE = "local_imported_video"
SAMPLE_TYPE = "external_full_classroom_video"
DATA_MODE = "external_full_classroom_video"
EXPECTED_KEY_EVENT_NOTE = "16:27.5-16:30.5 contains many raised hands and a few standing students"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a demo delivery package from the local imported SAV full-classroom video.")
    parser.add_argument("--sample-root", type=Path, default=DEFAULT_SAMPLE_ROOT)
    parser.add_argument("--delivery-root", type=Path, default=DEFAULT_DELIVERY_ROOT)
    args = parser.parse_args()

    sample_root = args.sample_root.resolve()
    delivery_root = args.delivery_root.resolve()
    package_dir = delivery_root / DEMO_CLASSROOM_DIR / DEMO_DATE_DIR / PACKAGE_ID
    package_dir.mkdir(parents=True, exist_ok=True)

    video_source = sample_root / "videos" / f"{SAMPLE_ID}.mp4"
    transcript_source = sample_root / "asr_results" / "phase312_asr_full_classroom_sav_20200908_17" / "transcript.json"
    audio_source = sample_root / "asr_results" / "phase312_asr_full_classroom_sav_20200908_17" / "extracted_audio.wav"
    question_csv = sample_root / "asr_enriched_results" / "phase313_asr_enriched_full_classroom_sav_20200908_17" / "question_events.csv"

    _require_file(video_source)
    _require_file(transcript_source)
    _require_file(audio_source)
    _require_file(question_csv)

    transcript_payload = _read_json(transcript_source)
    question_payload = _build_teacher_questions_payload(question_csv)
    duration_seconds = _probe_duration_seconds(video_source)
    transcript_count = len(transcript_payload.get("segments", [])) if isinstance(transcript_payload, dict) else 0
    question_count = len(question_payload.get("questions", []))

    video_target = package_dir / "video.mp4"
    standardized_video_target = package_dir / "standardized_video.mp4"
    audio_target = package_dir / "audio.wav"
    transcript_target = package_dir / "teacher_transcript.json"
    questions_target = package_dir / "teacher_questions.json"
    metadata_target = package_dir / "metadata.json"
    capture_metadata_target = package_dir / "capture_metadata.json"

    _link_or_copy(video_source, video_target)
    _link_or_copy(video_source, standardized_video_target)
    _link_or_copy(audio_source, audio_target)
    transcript_target.write_text(json.dumps(transcript_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    questions_target.write_text(json.dumps(question_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    metadata_payload = {
        "capture_id": PACKAGE_ID,
        "classroom_id": CLASSROOM_ID,
        "session_id": PACKAGE_ID,
        "device_id": "local-imported-sav-bridge",
        "device_name": "Local imported SAV full classroom video",
        "source_host": "local-import-bridge",
        "source_kind": "local_imported_video",
        "source_path": str(video_source),
        "source_dataset": SOURCE_DATASET,
        "source_type": SOURCE_TYPE,
        "sample_type": SAMPLE_TYPE,
        "data_mode": DATA_MODE,
        "is_pi_capture": False,
        "is_own_capture": False,
        "is_local_processed": True,
        "started_at": "2020-09-08T00:00:00Z",
        "ended_at": _offset_time("2020-09-08T00:00:00Z", duration_seconds),
        "recorded_at": "2020-09-08T00:00:00Z",
        "duration_seconds": duration_seconds,
        "status": "completed",
        "delivery_status": "ready",
        "session_ready": True,
        "delivery_mode": "local_demo_package",
        "delivery_path": str(package_dir),
        "local_video_path": str(video_source),
        "local_audio_path": str(audio_source),
        "transcript_path": str(transcript_target),
        "transcript_status": "available" if transcript_count > 0 else "unavailable",
        "transcript_source": "phase312_asr_transcript",
        "question_event_path": str(questions_target),
        "question_event_status": "available" if question_count > 0 else "unavailable",
        "question_event_source": "phase313_asr_rule_detection",
        "transcript_count": transcript_count,
        "question_event_count": question_count,
        "video_size": video_source.stat().st_size,
        "audio_size": audio_source.stat().st_size,
        "transcript_size": transcript_target.stat().st_size,
        "question_event_size": questions_target.stat().st_size,
        "window_size_seconds": 20,
        "analysis_id": PACKAGE_ID,
        "video_id": f"video_{SOURCE_VIDEO_ID}_demo_delivery",
        "expected_key_event_note": EXPECTED_KEY_EVENT_NOTE,
        "notes": "Local imported SAV full classroom video packaged into Raspberry Pi-style delivery layout for local demo; not Raspberry Pi capture.",
        "file_integrity": {
            "metadata_json": True,
            "video_mp4": True,
            "audio_wav": True,
            "teacher_transcript_json": True,
            "teacher_questions_json": True,
            "capture_metadata_json": True,
            "standardized_video_mp4": True,
        },
    }
    metadata_target.write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    capture_metadata_payload = {
        "capture": {
            "device_id": "local-imported-sav-bridge",
            "device_name": "Local imported SAV full classroom video",
            "classroom_id": CLASSROOM_ID,
            "captured_at": "2020-09-08T00:00:00Z",
            "video_path": str(video_source),
            "keyframe_dir": "",
            "standardized_video_path": str(standardized_video_target),
            "source_dataset": SOURCE_DATASET,
            "source_type": SOURCE_TYPE,
            "sample_type": SAMPLE_TYPE,
            "data_mode": DATA_MODE,
            "is_pi_capture": False,
            "is_own_capture": False,
            "is_local_processed": True,
            "notes": "External SAV public dataset video locally packaged for classroom delivery demo.",
        },
        "video": {
            "raw_video_path": str(video_target),
            "standardized_video_path": str(standardized_video_target),
            "format": "mp4",
            "codec": "source_preserved",
            "audio_codec": "pcm_or_source_preserved",
            "browser_compatible": True,
            "transcode_status": "reused_original_as_demo_package",
            "transcode_error": "",
        },
    }
    capture_metadata_target.write_text(json.dumps(capture_metadata_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PHASE35C_DEMO_PACKAGE_DIR={package_dir}")
    print(f"PHASE35C_DEMO_VIDEO_PATH={video_target}")
    print(f"PHASE35C_DEMO_AUDIO_PATH={audio_target}")
    print(f"PHASE35C_DEMO_TRANSCRIPT_COUNT={transcript_count}")
    print(f"PHASE35C_DEMO_QUESTION_COUNT={question_count}")
    print(f"PHASE35C_DEMO_SOURCE_DATASET={SOURCE_DATASET}")
    print("PHASE35C_DEMO_IS_PI_CAPTURE=false")
    print("PHASE35C_DEMO_IS_OWN_CAPTURE=false")
    print("PHASE35C_DEMO_PACKAGE_READY=true")
    return 0


def _build_teacher_questions_payload(csv_path: Path) -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            questions.append(
                {
                    "event_id": row.get("event_id", ""),
                    "question_id": row.get("event_id", ""),
                    "start_sec": _safe_float(row.get("start_sec")),
                    "end_sec": _safe_float(row.get("end_sec")),
                    "text": str(row.get("text") or "").strip(),
                    "question_type": str(row.get("question_type") or "question_candidate").strip(),
                    "source": str(row.get("source") or "asr_rule_detection").strip(),
                    "confidence": round(_safe_float(row.get("confidence"), default=0.75), 2),
                    "speaker": str(row.get("speaker") or "unknown").strip(),
                    "speaker_role": str(row.get("speaker_role") or "teacher_candidate").strip(),
                    "speaker_confidence": str(row.get("speaker_confidence") or "unknown").strip(),
                    "matched_rules": str(row.get("matched_rules") or "").strip(),
                    "source_segment_ids": str(row.get("source_segment_ids") or "").strip(),
                }
            )
    return {
        "status": "available",
        "source": "phase313_asr_rule_detection",
        "questions": questions,
        "summary": {
            "question_count": len(questions),
            "notes": "Question candidates derived from local ASR-enriched full-classroom processing.",
        },
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _probe_duration_seconds(video_path: Path) -> int:
    try:
        import cv2

        capture = cv2.VideoCapture(str(video_path))
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
            if fps > 0 and frame_count > 0:
                return max(1, int(frame_count / fps))
        finally:
            capture.release()
    except Exception:
        pass
    return 0


def _offset_time(start_iso: str, duration_seconds: int) -> str:
    try:
        dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        return (dt + timedelta(seconds=max(duration_seconds, 0))).isoformat().replace("+00:00", "Z")
    except Exception:
        return start_iso


def _link_or_copy(source: Path, target: Path) -> None:
    if target.exists():
        same_size = target.stat().st_size == source.stat().st_size
        if same_size:
            return
        target.unlink()
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def _require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(str(path))


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(str(value or default))
    except ValueError:
        return default


if __name__ == "__main__":
    raise SystemExit(main())
