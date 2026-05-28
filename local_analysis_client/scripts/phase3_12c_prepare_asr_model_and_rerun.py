from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
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
DEFAULT_AUDIO_PATH = DEFAULT_OUTPUT_DIR / "extracted_audio.wav"
DEFAULT_MODEL_DIR = REPO_ROOT.parent / "asr_models" / "faster-whisper-base"
DEFAULT_STATUS_PATH = DEFAULT_OUTPUT_DIR / "asr_model_status.json"
PHASE312_SCRIPT = REPO_ROOT / "scripts" / "phase3_12_extract_audio_and_run_asr.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare local faster-whisper model cache and rerun Phase 3.12 ASR.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--audio-path", type=Path, default=DEFAULT_AUDIO_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--status-path", type=Path, default=DEFAULT_STATUS_PATH)
    parser.add_argument("--repo-id", default="Systran/faster-whisper-base")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-rerun", action="store_true")
    args = parser.parse_args()

    model_dir = args.model_dir.resolve()
    audio_path = args.audio_path.resolve()
    output_dir = args.output_dir.resolve()
    status_path = args.status_path.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    status: dict[str, Any] = {
        "python_present": bool(sys.executable),
        "python_executable": sys.executable,
        "pip_present": shutil.which("pip") is not None,
        "faster_whisper_installed": module_available("faster_whisper"),
        "model_dir": str(model_dir),
        "model_dir_present": model_dir.exists(),
        "model_local_ready": False,
        "model_path": "none",
        "model_download_attempted": False,
        "model_download_success": False,
        "model_download_errors": [],
        "audio_wav_present": audio_path.exists() and audio_path.stat().st_size > 0 if audio_path.exists() else False,
        "asr_rerun_attempted": False,
        "asr_rerun_returncode": None,
        "transcript_json_present": False,
        "transcript_csv_present": False,
        "transcript_segment_count": 0,
        "transcript_has_timestamps": False,
        "transcript_has_text": False,
        "no_question_events_created": True,
        "local_asr_transcript_ready": False,
        "phase312": {},
    }

    try:
        model_dir.mkdir(parents=True, exist_ok=True)
        status["model_dir_present"] = model_dir.exists()
        status["model_local_ready"] = model_ready(model_dir)
        if status["model_local_ready"]:
            status["model_path"] = str(model_dir)

        if not status["model_local_ready"] and not args.skip_download:
            status["model_download_attempted"] = True
            download_success, errors = try_download_model(args.repo_id, model_dir)
            status["model_download_success"] = download_success
            status["model_download_errors"] = errors
            status["model_local_ready"] = model_ready(model_dir)
            if status["model_local_ready"]:
                status["model_path"] = str(model_dir)

        if status["model_local_ready"] and status["audio_wav_present"] and not args.skip_rerun:
            status["asr_rerun_attempted"] = True
            completed = run_phase312_asr(model_dir)
            status["asr_rerun_returncode"] = completed.returncode
            status["asr_rerun_stdout_tail"] = tail_text(completed.stdout)
            status["asr_rerun_stderr_tail"] = tail_text(completed.stderr)

        refresh_transcript_status(output_dir, status)
        refresh_phase312_status(output_dir, status)
        write_json(status_path, status)
        print_markers(status)
        return 0 if status["local_asr_transcript_ready"] else 1
    except Exception as exc:  # noqa: BLE001 - must emit status for validation.
        status["error_message"] = str(exc)
        refresh_transcript_status(output_dir, status)
        refresh_phase312_status(output_dir, status)
        write_json(status_path, status)
        print_markers(status)
        return 1


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def model_ready(model_dir: Path) -> bool:
    required_any_model = [
        "model.bin",
        "model.int8.bin",
        "model.onnx",
    ]
    required_metadata = [
        "config.json",
        "tokenizer.json",
    ]
    has_model = any((model_dir / name).exists() for name in required_any_model)
    has_metadata = all((model_dir / name).exists() for name in required_metadata)
    return has_model and has_metadata


def try_download_model(repo_id: str, model_dir: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    endpoints: list[str | None] = [None, "https://hf-mirror.com"]
    for endpoint in endpoints:
        env = os.environ.copy()
        if endpoint:
            env["HF_ENDPOINT"] = endpoint
        command = [
            sys.executable,
            "-c",
            (
                "from huggingface_hub import snapshot_download; "
                f"print(snapshot_download({repo_id!r}, local_dir={str(model_dir)!r}, local_dir_use_symlinks=False))"
            ),
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=900, env=env)
        if completed.returncode == 0 and model_ready(model_dir):
            return True, errors
        label = endpoint or "huggingface.co"
        errors.append(f"{label}: {tail_text(completed.stderr or completed.stdout)}")
    return False, errors


def run_phase312_asr(model_dir: Path) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(PHASE312_SCRIPT),
        "--engine",
        "faster-whisper",
        "--model",
        str(model_dir),
    ]
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=7200)


def refresh_transcript_status(output_dir: Path, status: dict[str, Any]) -> None:
    transcript_json = output_dir / "transcript.json"
    transcript_csv = output_dir / "transcript.csv"
    status["transcript_json_present"] = transcript_json.exists()
    status["transcript_csv_present"] = transcript_csv.exists()
    segments: list[dict[str, Any]] = []
    if transcript_json.exists():
        try:
            payload = json.loads(transcript_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        raw_segments = payload.get("segments") if isinstance(payload, dict) else []
        if isinstance(raw_segments, list):
            segments = [seg for seg in raw_segments if isinstance(seg, dict)]
        text = transcript_json.read_text(encoding="utf-8", errors="ignore")
        status["no_question_events_created"] = "question_events" not in text
    status["transcript_segment_count"] = len(segments)
    status["transcript_has_timestamps"] = bool(
        segments and all("start_sec" in seg and "end_sec" in seg for seg in segments)
    )
    status["transcript_has_text"] = bool(
        segments and all(str(seg.get("text") or "").strip() for seg in segments)
    )
    status["local_asr_transcript_ready"] = all(
        [
            status["transcript_json_present"],
            status["transcript_csv_present"],
            status["transcript_segment_count"] > 0,
            status["transcript_has_timestamps"],
            status["transcript_has_text"],
            status["no_question_events_created"],
        ]
    )


def refresh_phase312_status(output_dir: Path, status: dict[str, Any]) -> None:
    phase312_status_path = output_dir / "asr_status.json"
    phase312: dict[str, Any] = {}
    if phase312_status_path.exists():
        try:
            phase312 = json.loads(phase312_status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            phase312 = {}
    status["phase312"] = {
        "asr_engine_available": bool(phase312.get("asr_engine_available")),
        "asr_engine": phase312.get("asr_engine") or "none",
        "asr_model": phase312.get("asr_model") or "none",
        "asr_transcript_created": bool(phase312.get("transcript_created")),
        "transcript_segment_count": int(phase312.get("transcript_segment_count") or 0),
        "transcript_has_timestamps": bool(phase312.get("transcript_duration_seconds")),
        "local_asr_transcript_ready": bool(status.get("local_asr_transcript_ready")),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def tail_text(text: str, max_lines: int = 20) -> str:
    lines = (text or "").splitlines()
    return "\n".join(lines[-max_lines:])


def print_markers(status: dict[str, Any]) -> None:
    phase312 = status.get("phase312") or {}
    print(f"PHASE312C_PYTHON_PRESENT={bool_text(bool(status.get('python_present')))}")
    print(f"PHASE312C_FASTER_WHISPER_INSTALLED={bool_text(bool(status.get('faster_whisper_installed')))}")
    print(f"PHASE312C_MODEL_DIR_PRESENT={bool_text(bool(status.get('model_dir_present')))}")
    print(f"PHASE312C_MODEL_LOCAL_READY={bool_text(bool(status.get('model_local_ready')))}")
    print(f"PHASE312C_MODEL_PATH={status.get('model_path') or 'none'}")
    print(f"PHASE312C_MODEL_DOWNLOAD_ATTEMPTED={bool_text(bool(status.get('model_download_attempted')))}")
    print(f"PHASE312C_MODEL_DOWNLOAD_SUCCESS={bool_text(bool(status.get('model_download_success')))}")
    print(f"PHASE312C_AUDIO_WAV_PRESENT={bool_text(bool(status.get('audio_wav_present')))}")
    print(f"PHASE312C_ASR_RERUN_ATTEMPTED={bool_text(bool(status.get('asr_rerun_attempted')))}")
    print(f"PHASE312C_TRANSCRIPT_JSON_PRESENT={bool_text(bool(status.get('transcript_json_present')))}")
    print(f"PHASE312C_TRANSCRIPT_CSV_PRESENT={bool_text(bool(status.get('transcript_csv_present')))}")
    print(f"PHASE312C_TRANSCRIPT_SEGMENT_COUNT={int(status.get('transcript_segment_count') or 0)}")
    print(f"PHASE312C_TRANSCRIPT_HAS_TIMESTAMPS={bool_text(bool(status.get('transcript_has_timestamps')))}")
    print(f"PHASE312C_TRANSCRIPT_HAS_TEXT={bool_text(bool(status.get('transcript_has_text')))}")
    print(f"PHASE312C_NO_QUESTION_EVENTS_CREATED={bool_text(bool(status.get('no_question_events_created')))}")
    print(f"PHASE312C_LOCAL_ASR_TRANSCRIPT_READY={bool_text(bool(status.get('local_asr_transcript_ready')))}")
    print(f"PHASE312_ASR_ENGINE_AVAILABLE={bool_text(bool(phase312.get('asr_engine_available')))}")
    print(f"PHASE312_ASR_ENGINE={phase312.get('asr_engine') or 'none'}")
    print(f"PHASE312_ASR_MODEL={phase312.get('asr_model') or 'none'}")
    print(f"PHASE312_ASR_TRANSCRIPT_CREATED={bool_text(bool(phase312.get('asr_transcript_created')))}")
    print(f"PHASE312_TRANSCRIPT_SEGMENT_COUNT={int(phase312.get('transcript_segment_count') or 0)}")
    print(f"PHASE312_TRANSCRIPT_HAS_TIMESTAMPS={bool_text(bool(phase312.get('transcript_has_timestamps')))}")
    print(f"PHASE312_LOCAL_ASR_TRANSCRIPT_READY={bool_text(bool(phase312.get('local_asr_transcript_ready')))}")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
