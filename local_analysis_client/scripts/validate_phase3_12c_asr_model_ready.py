from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYSIS_ID = "phase312_asr_full_classroom_sav_20200908_17"
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "asr_results"
    / DEFAULT_ANALYSIS_ID
)
DEFAULT_MODEL_DIR = REPO_ROOT.parent / "asr_models" / "faster-whisper-base"
DEFAULT_STATUS_PATH = DEFAULT_OUTPUT_DIR / "asr_model_status.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.12c ASR model cache and transcript readiness.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--status-path", type=Path, default=DEFAULT_STATUS_PATH)
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    output_dir = args.output_dir.resolve()
    status_path = args.status_path.resolve()
    status = read_json(status_path)
    transcript_json = output_dir / "transcript.json"
    transcript_csv = output_dir / "transcript.csv"
    audio_wav = output_dir / "extracted_audio.wav"

    segments: list[dict[str, Any]] = []
    no_question_events = True
    if transcript_json.exists():
        transcript_text = transcript_json.read_text(encoding="utf-8", errors="ignore")
        no_question_events = "question_events" not in transcript_text
        transcript = read_json(transcript_json)
        raw_segments = transcript.get("segments") if isinstance(transcript, dict) else []
        if isinstance(raw_segments, list):
            segments = [seg for seg in raw_segments if isinstance(seg, dict)]

    transcript_has_timestamps = bool(segments and all("start_sec" in seg and "end_sec" in seg for seg in segments))
    transcript_has_text = bool(segments and all(str(seg.get("text") or "").strip() for seg in segments))
    local_ready = all(
        [
            transcript_json.exists(),
            transcript_csv.exists(),
            len(segments) > 0,
            transcript_has_timestamps,
            transcript_has_text,
            no_question_events,
        ]
    )
    phase312 = status.get("phase312") if isinstance(status.get("phase312"), dict) else {}

    print(f"PHASE312C_PYTHON_PRESENT={bool_text(True)}")
    print(f"PHASE312C_FASTER_WHISPER_INSTALLED={bool_text(importlib.util.find_spec('faster_whisper') is not None)}")
    print(f"PHASE312C_MODEL_DIR_PRESENT={bool_text(model_dir.exists())}")
    print(f"PHASE312C_MODEL_LOCAL_READY={bool_text(model_ready(model_dir))}")
    print(f"PHASE312C_MODEL_PATH={str(model_dir) if model_ready(model_dir) else 'none'}")
    print(f"PHASE312C_MODEL_DOWNLOAD_ATTEMPTED={bool_text(bool(status.get('model_download_attempted')))}")
    print(f"PHASE312C_MODEL_DOWNLOAD_SUCCESS={bool_text(bool(status.get('model_download_success')))}")
    print(f"PHASE312C_AUDIO_WAV_PRESENT={bool_text(audio_wav.exists() and audio_wav.stat().st_size > 0 if audio_wav.exists() else False)}")
    print(f"PHASE312C_ASR_RERUN_ATTEMPTED={bool_text(bool(status.get('asr_rerun_attempted')))}")
    print(f"PHASE312C_TRANSCRIPT_JSON_PRESENT={bool_text(transcript_json.exists())}")
    print(f"PHASE312C_TRANSCRIPT_CSV_PRESENT={bool_text(transcript_csv.exists())}")
    print(f"PHASE312C_TRANSCRIPT_SEGMENT_COUNT={len(segments)}")
    print(f"PHASE312C_TRANSCRIPT_HAS_TIMESTAMPS={bool_text(transcript_has_timestamps)}")
    print(f"PHASE312C_TRANSCRIPT_HAS_TEXT={bool_text(transcript_has_text)}")
    print(f"PHASE312C_NO_QUESTION_EVENTS_CREATED={bool_text(no_question_events)}")
    print(f"PHASE312C_LOCAL_ASR_TRANSCRIPT_READY={bool_text(local_ready)}")
    print(f"PHASE312_ASR_ENGINE_AVAILABLE={bool_text(bool(phase312.get('asr_engine_available')))}")
    print(f"PHASE312_ASR_ENGINE={phase312.get('asr_engine') or 'none'}")
    print(f"PHASE312_ASR_MODEL={phase312.get('asr_model') or 'none'}")
    print(f"PHASE312_ASR_TRANSCRIPT_CREATED={bool_text(bool(phase312.get('asr_transcript_created')))}")
    print(f"PHASE312_TRANSCRIPT_SEGMENT_COUNT={int(phase312.get('transcript_segment_count') or 0)}")
    print(f"PHASE312_TRANSCRIPT_HAS_TIMESTAMPS={bool_text(bool(phase312.get('transcript_has_timestamps')))}")
    print(f"PHASE312_LOCAL_ASR_TRANSCRIPT_READY={bool_text(bool(phase312.get('local_asr_transcript_ready')))}")
    return 0 if status_path.exists() else 1


def model_ready(model_dir: Path) -> bool:
    has_model = any((model_dir / name).exists() for name in ("model.bin", "model.int8.bin", "model.onnx"))
    has_metadata = all((model_dir / name).exists() for name in ("config.json", "tokenizer.json"))
    return has_model and has_metadata


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
