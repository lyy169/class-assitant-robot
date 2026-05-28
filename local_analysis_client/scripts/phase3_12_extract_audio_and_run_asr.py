from __future__ import annotations

import argparse
import csv
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
DEFAULT_VIDEO = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "videos"
    / "local_imported_sav_full_classroom_20200908_17.mp4"
)
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT.parent
    / "real_classroom_samples"
    / "asr_results"
    / DEFAULT_ANALYSIS_ID
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract full-classroom audio and run local offline ASR.")
    parser.add_argument("--video", type=Path, default=DEFAULT_VIDEO)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--analysis-id", default=DEFAULT_ANALYSIS_ID)
    parser.add_argument("--engine", default="auto", choices=["auto", "faster-whisper", "openai-whisper", "whisper-cli", "funasr"])
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="auto")
    parser.add_argument("--force-extract", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()

    video_path = args.video.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "extracted_audio.wav"
    status_path = output_dir / "asr_status.json"
    transcript_json_path = output_dir / "transcript.json"
    transcript_csv_path = output_dir / "transcript.csv"
    summary_path = output_dir / "asr_summary.md"

    status: dict[str, Any] = {
        "analysis_id": args.analysis_id,
        "input_video": str(video_path),
        "output_dir": str(output_dir),
        "input_video_present": video_path.exists(),
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "audio_extracted": False,
        "audio_path": str(audio_path),
        "asr_engine_available": False,
        "asr_engine": "none",
        "asr_model": "none",
        "transcript_created": False,
        "transcript_json": str(transcript_json_path),
        "transcript_csv": str(transcript_csv_path),
        "transcript_segment_count": 0,
        "transcript_duration_seconds": 0.0,
        "error_message": "",
        "engine_candidates": detect_engine_candidates(args.model),
        "note": "Phase 3.12 creates transcript only when a local ASR engine and local/cached model are available.",
    }

    try:
        if not status["input_video_present"]:
            raise RuntimeError(f"input video not found: {video_path}")
        if not status["ffmpeg_available"]:
            raise RuntimeError("ffmpeg is not available in PATH")
        extract_audio(video_path, audio_path, force=args.force_extract)
        status["audio_extracted"] = audio_path.exists() and audio_path.stat().st_size > 0
        if not status["audio_extracted"]:
            raise RuntimeError(f"audio extraction failed: {audio_path}")

        selected = select_engine(args.engine, args.model)
        if selected is None:
            status["error_message"] = build_no_engine_message(args.model)
            write_status(status_path, status)
            write_summary(summary_path, status)
            print_markers(status)
            return 0

        status["asr_engine_available"] = True
        status["asr_engine"] = selected["engine"]
        status["asr_model"] = selected["model_display"]
        segments = run_asr(selected, audio_path, args.language, args.device, args.compute_type)
        if not segments:
            raise RuntimeError("ASR completed but returned zero transcript segments")

        write_transcript_json(
            transcript_json_path=transcript_json_path,
            analysis_id=args.analysis_id,
            source_video=video_path,
            audio_path=audio_path,
            engine=selected["engine"],
            model=status["asr_model"],
            language=args.language,
            segments=segments,
        )
        write_transcript_csv(transcript_csv_path, segments)
        status["transcript_created"] = True
        status["transcript_segment_count"] = len(segments)
        status["transcript_duration_seconds"] = max((float(seg.get("end_sec") or 0.0) for seg in segments), default=0.0)
        write_status(status_path, status)
        write_summary(summary_path, status)
        print_markers(status)
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI must always emit status for validation.
        status["error_message"] = str(exc)
        status["audio_extracted"] = audio_path.exists() and audio_path.stat().st_size > 0
        write_status(status_path, status)
        write_summary(summary_path, status)
        print_markers(status)
        return 1


def extract_audio(video_path: Path, audio_path: Path, force: bool) -> None:
    if audio_path.exists() and audio_path.stat().st_size > 0 and not force:
        return
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr_tail = "\n".join(completed.stderr.splitlines()[-12:])
        raise RuntimeError(f"ffmpeg audio extraction failed: {stderr_tail}")


def detect_engine_candidates(model: str) -> dict[str, Any]:
    return {
        "faster_whisper_module": module_available("faster_whisper"),
        "faster_whisper_cached_model": str(resolve_faster_whisper_model(model) or ""),
        "openai_whisper_module": module_available("whisper"),
        "openai_whisper_cached_model": str(resolve_openai_whisper_model(model) or ""),
        "whisper_cli": shutil.which("whisper") or "",
        "funasr_module": module_available("funasr"),
        "funasr_local_model": str(Path(model).resolve()) if Path(model).exists() else "",
    }


def select_engine(engine: str, model: str) -> dict[str, str] | None:
    requested = ["faster-whisper", "openai-whisper", "whisper-cli", "funasr"] if engine == "auto" else [engine]
    for candidate in requested:
        if candidate == "faster-whisper" and module_available("faster_whisper"):
            model_path = resolve_faster_whisper_model(model)
            if model_path:
                return {"engine": candidate, "model_source": str(model_path), "model_display": model}
        if candidate == "openai-whisper" and module_available("whisper"):
            model_path = resolve_openai_whisper_model(model)
            if model_path:
                return {"engine": candidate, "model_source": str(model_path), "model_display": model}
        if candidate == "whisper-cli" and shutil.which("whisper"):
            model_path = resolve_openai_whisper_model(model)
            if model_path:
                return {"engine": candidate, "model_source": str(model_path), "model_display": model}
        if candidate == "funasr" and module_available("funasr") and Path(model).exists():
            return {"engine": candidate, "model_source": str(Path(model).resolve()), "model_display": str(Path(model).resolve())}
    return None


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def resolve_faster_whisper_model(model: str) -> Path | None:
    explicit = Path(model)
    if explicit.exists():
        return explicit.resolve()
    cache_roots = []
    if os.environ.get("HF_HOME"):
        cache_roots.append(Path(os.environ["HF_HOME"]) / "hub")
    cache_roots.append(Path.home() / ".cache" / "huggingface" / "hub")
    repo_dir_name = f"models--Systran--faster-whisper-{model}"
    for root in cache_roots:
        repo_dir = root / repo_dir_name
        snapshots = repo_dir / "snapshots"
        if not snapshots.exists():
            continue
        for snapshot in sorted(snapshots.iterdir(), reverse=True):
            if (snapshot / "model.bin").exists():
                return snapshot.resolve()
    return None


def resolve_openai_whisper_model(model: str) -> Path | None:
    explicit = Path(model)
    if explicit.exists():
        return explicit.resolve()
    cache_dir = Path.home() / ".cache" / "whisper"
    model_file = cache_dir / f"{model}.pt"
    return model_file.resolve() if model_file.exists() else None


def build_no_engine_message(model: str) -> str:
    return (
        "No runnable local ASR engine was found. Install one of: faster-whisper, openai-whisper, "
        "or whisper CLI, and prepare a local/cached model before running again. "
        f"Requested model: {model}. The script does not download models automatically."
    )


def run_asr(
    selected: dict[str, str],
    audio_path: Path,
    language: str,
    device: str,
    compute_type: str,
) -> list[dict[str, Any]]:
    engine = selected["engine"]
    if engine == "faster-whisper":
        return run_faster_whisper(selected["model_source"], audio_path, language, device, compute_type)
    if engine == "openai-whisper":
        return run_openai_whisper(selected["model_source"], audio_path, language)
    if engine == "whisper-cli":
        return run_whisper_cli(selected["model_display"], audio_path, language)
    if engine == "funasr":
        return run_funasr(selected["model_source"], audio_path)
    raise RuntimeError(f"unsupported ASR engine: {engine}")


def run_faster_whisper(
    model_source: str,
    audio_path: Path,
    language: str,
    device: str,
    compute_type: str,
) -> list[dict[str, Any]]:
    from faster_whisper import WhisperModel  # type: ignore[import-not-found]

    model = WhisperModel(model_source, device=device, compute_type=compute_type, local_files_only=True)
    kwargs: dict[str, Any] = {}
    if language != "auto":
        kwargs["language"] = language
    segments_iter, _info = model.transcribe(str(audio_path), **kwargs)
    return [
        normalize_segment(index, float(segment.start), float(segment.end), segment.text, None)
        for index, segment in enumerate(segments_iter, start=1)
    ]


def run_openai_whisper(model_source: str, audio_path: Path, language: str) -> list[dict[str, Any]]:
    import whisper  # type: ignore[import-not-found]

    model = whisper.load_model(model_source)
    kwargs: dict[str, Any] = {"fp16": False}
    if language != "auto":
        kwargs["language"] = language
    result = model.transcribe(str(audio_path), **kwargs)
    segments = result.get("segments") if isinstance(result, dict) else []
    return [
        normalize_segment(index, segment.get("start"), segment.get("end"), segment.get("text"), None)
        for index, segment in enumerate(segments, start=1)
        if isinstance(segment, dict)
    ]


def run_whisper_cli(model: str, audio_path: Path, language: str) -> list[dict[str, Any]]:
    cli_output_dir = audio_path.parent / "_whisper_cli_output"
    cli_output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "whisper",
        str(audio_path),
        "--model",
        model,
        "--output_dir",
        str(cli_output_dir),
        "--output_format",
        "json",
    ]
    if language != "auto":
        command.extend(["--language", language])
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr_tail = "\n".join(completed.stderr.splitlines()[-12:])
        raise RuntimeError(f"whisper CLI failed: {stderr_tail}")
    cli_json = cli_output_dir / f"{audio_path.stem}.json"
    payload = json.loads(cli_json.read_text(encoding="utf-8"))
    segments = payload.get("segments") if isinstance(payload, dict) else []
    return [
        normalize_segment(index, segment.get("start"), segment.get("end"), segment.get("text"), None)
        for index, segment in enumerate(segments, start=1)
        if isinstance(segment, dict)
    ]


def run_funasr(model_source: str, audio_path: Path) -> list[dict[str, Any]]:
    from funasr import AutoModel  # type: ignore[import-not-found]

    model = AutoModel(model=model_source, disable_update=True)
    result = model.generate(input=str(audio_path))
    segments: list[dict[str, Any]] = []
    if isinstance(result, list):
        for item in result:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if text:
                segments.append(normalize_segment(len(segments) + 1, 0.0, 0.0, text, None))
    return segments


def normalize_segment(index: int, start: Any, end: Any, text: Any, confidence: Any) -> dict[str, Any]:
    start_sec = round(float(start or 0.0), 3)
    end_sec = round(float(end or start_sec), 3)
    return {
        "segment_id": f"seg_{index:04d}",
        "start_sec": start_sec,
        "end_sec": end_sec,
        "text": str(text or "").strip(),
        "confidence": confidence,
        "speaker": "unknown",
        "speaker_role": "unknown",
    }


def write_transcript_json(
    transcript_json_path: Path,
    analysis_id: str,
    source_video: Path,
    audio_path: Path,
    engine: str,
    model: str,
    language: str,
    segments: list[dict[str, Any]],
) -> None:
    payload = {
        "analysis_id": analysis_id,
        "source_video": str(source_video),
        "audio_path": str(audio_path),
        "asr": {
            "engine": engine,
            "model": model,
            "language": language,
            "transcript_present": bool(segments),
            "speaker_diarization": False,
            "source": "local_post_process",
        },
        "segments": segments,
    }
    transcript_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_transcript_csv(transcript_csv_path: Path, segments: list[dict[str, Any]]) -> None:
    with transcript_csv_path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=["segment_id", "start_sec", "end_sec", "duration_sec", "text", "confidence", "speaker", "speaker_role"],
        )
        writer.writeheader()
        for segment in segments:
            row = dict(segment)
            row["duration_sec"] = round(float(segment["end_sec"]) - float(segment["start_sec"]), 3)
            writer.writerow(row)


def write_status(status_path: Path, status: dict[str, Any]) -> None:
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def write_summary(summary_path: Path, status: dict[str, Any]) -> None:
    summary = f"""# Phase 3.12 Local ASR Transcript Summary

## Runtime Result

- input_video_present: {bool_text(bool(status.get("input_video_present")))}
- ffmpeg_available: {bool_text(bool(status.get("ffmpeg_available")))}
- audio_extracted: {bool_text(bool(status.get("audio_extracted")))}
- asr_engine_available: {bool_text(bool(status.get("asr_engine_available")))}
- asr_engine: {status.get("asr_engine") or "none"}
- asr_model: {status.get("asr_model") or "none"}
- transcript_created: {bool_text(bool(status.get("transcript_created")))}
- transcript_segment_count: {status.get("transcript_segment_count", 0)}
- transcript_duration_seconds: {status.get("transcript_duration_seconds", 0.0)}
- error_message: {status.get("error_message") or ""}

## Output Paths

- audio_path: `{status.get("audio_path")}`
- transcript_json: `{status.get("transcript_json")}`
- transcript_csv: `{status.get("transcript_csv")}`
- status_json: `{summary_path.parent / "asr_status.json"}`

## Boundary

- 树莓派端不是完整课堂内容 ASR 主链路，只用于语音唤醒、语音指令和录像控制。
- 本地端负责完整课堂音频提取和离线 ASR 转写。
- 云端不跑 ASR，只展示本地端生成的 ASR 转写、视频和课堂行为分析。
- Phase 3.12 不生成 teacher.question_events；Phase 3.13 再基于 transcript 生成教师提问事件。
"""
    summary_path.write_text(summary, encoding="utf-8")


def print_markers(status: dict[str, Any]) -> None:
    transcript_json = Path(str(status.get("transcript_json") or ""))
    transcript_csv = Path(str(status.get("transcript_csv") or ""))
    output_dir = Path(str(status.get("output_dir") or ""))
    audio_path = Path(str(status.get("audio_path") or ""))
    print(f"PHASE312_OUTPUT_DIR_PRESENT={bool_text(output_dir.exists())}")
    print(f"PHASE312_INPUT_VIDEO_PRESENT={bool_text(bool(status.get('input_video_present')))}")
    print(f"PHASE312_FFMPEG_AVAILABLE={bool_text(bool(status.get('ffmpeg_available')))}")
    print(f"PHASE312_AUDIO_EXTRACTED={bool_text(bool(status.get('audio_extracted')))}")
    print(f"PHASE312_AUDIO_WAV_PRESENT={bool_text(audio_path.exists() and audio_path.stat().st_size > 0 if audio_path.exists() else False)}")
    print(f"PHASE312_ASR_ENGINE_AVAILABLE={bool_text(bool(status.get('asr_engine_available')))}")
    print(f"PHASE312_ASR_ENGINE={status.get('asr_engine') or 'none'}")
    print(f"PHASE312_ASR_MODEL={status.get('asr_model') or 'none'}")
    print(f"PHASE312_ASR_TRANSCRIPT_CREATED={bool_text(bool(status.get('transcript_created')))}")
    print(f"PHASE312_TRANSCRIPT_JSON_PRESENT={bool_text(transcript_json.exists())}")
    print(f"PHASE312_TRANSCRIPT_CSV_PRESENT={bool_text(transcript_csv.exists())}")
    print(f"PHASE312_TRANSCRIPT_SEGMENT_COUNT={int(status.get('transcript_segment_count') or 0)}")
    print(f"PHASE312_TRANSCRIPT_HAS_TIMESTAMPS={bool_text(bool(status.get('transcript_duration_seconds')))}")
    print("PHASE312_NO_QUESTION_EVENTS_CREATED=true")
    print("PHASE312_PI_ASR_NOT_USED_FOR_CONTENT=true")
    print("PHASE312_CLOUD_ASR_NOT_USED=true")
    ready = all(
        [
            status.get("audio_extracted"),
            status.get("asr_engine_available"),
            status.get("transcript_created"),
            int(status.get("transcript_segment_count") or 0) > 0,
        ]
    )
    print(f"PHASE312_LOCAL_ASR_TRANSCRIPT_READY={bool_text(bool(ready))}")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
