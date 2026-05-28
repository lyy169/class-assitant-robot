from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from classroom_feedback_pipeline import analyze_delivery_package


DEFAULT_OUTPUT_DIR = REPO_ROOT / "processed_results" / "classroom_feedback"
DEFAULT_PENDING_UPLOAD_DIR = REPO_ROOT / "processed_results" / "pending_upload"
DEFAULT_ENRICHMENT_ROOT = REPO_ROOT / "processed_results" / "delivery_enrichment"
DEFAULT_LOCAL_ASR_MODEL = REPO_ROOT.parent / "asr_models" / "faster-whisper-base"
DEFAULT_ASR_MODEL = str(DEFAULT_LOCAL_ASR_MODEL) if DEFAULT_LOCAL_ASR_MODEL.exists() else "base"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enrich a delivery package with transcript/question files when missing, then run local analysis."
    )
    parser.add_argument("package_dir", type=Path, help="Delivery package directory.")
    parser.add_argument("--config-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pending-upload-dir", type=Path, default=DEFAULT_PENDING_UPLOAD_DIR)
    parser.add_argument("--enrichment-root", type=Path, default=DEFAULT_ENRICHMENT_ROOT)
    parser.add_argument("--upload-mode", choices=["auto", "http", "directory"], default="directory")
    parser.add_argument("--engine", default="auto", choices=["auto", "faster-whisper", "openai-whisper", "whisper-cli", "funasr"])
    parser.add_argument("--model", default=DEFAULT_ASR_MODEL)
    parser.add_argument("--language", default="auto")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--force-transcript", action="store_true")
    parser.add_argument("--force-questions", action="store_true")
    parser.add_argument("--transcript-json", type=Path, default=None, help="Optional precomputed transcript.json to import.")
    parser.add_argument("--question-csv", type=Path, default=None, help="Optional precomputed question_events.csv to import.")
    args = parser.parse_args()

    package_dir = args.package_dir.resolve()
    output_dir = args.output_dir.resolve()
    pending_upload_dir = args.pending_upload_dir.resolve()
    enrichment_root = args.enrichment_root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    pending_upload_dir.mkdir(parents=True, exist_ok=True)
    enrichment_root.mkdir(parents=True, exist_ok=True)

    package_id = package_dir.name
    enrichment_dir = enrichment_root / package_id
    enrichment_dir.mkdir(parents=True, exist_ok=True)

    phase312 = _load_script_module("phase312_asr", REPO_ROOT / "scripts" / "phase3_12_extract_audio_and_run_asr.py")
    phase313 = _load_script_module("phase313_questions", REPO_ROOT / "scripts" / "phase3_13_generate_question_events_from_asr.py")

    metadata_path = package_dir / "metadata.json"
    metadata = _read_json(metadata_path) if metadata_path.exists() else {}
    transcript_path = package_dir / "teacher_transcript.json"
    questions_path = package_dir / "teacher_questions.json"
    video_path = package_dir / "video.mp4"
    audio_path = package_dir / "audio.wav"

    transcript_action = "existing"
    question_action = "existing"
    transcript_error = ""
    question_error = ""

    transcript_payload = _read_json(transcript_path) if transcript_path.exists() else {}
    question_payload = _read_json(questions_path) if questions_path.exists() else {}

    if args.force_transcript or not _transcript_payload_has_segments(transcript_payload):
        transcript_payload, transcript_action, transcript_error = _ensure_transcript_payload(
            phase312=phase312,
            package_dir=package_dir,
            metadata=metadata,
            transcript_path=transcript_path,
            video_path=video_path,
            audio_path=audio_path,
            enrichment_dir=enrichment_dir,
            explicit_transcript_json=args.transcript_json.resolve() if args.transcript_json else None,
            engine=args.engine,
            model=args.model,
            language=args.language,
            device=args.device,
            compute_type=args.compute_type,
        )

    if args.force_questions or not _question_payload_has_events(question_payload):
        question_payload, question_action, question_error = _ensure_question_payload(
            phase313=phase313,
            metadata=metadata,
            transcript_payload=transcript_payload,
            questions_path=questions_path,
            explicit_question_csv=args.question_csv.resolve() if args.question_csv else None,
        )

    analyze_result = analyze_delivery_package(
        package_dir,
        config_path=args.config_path,
        output_dir=output_dir,
        pending_upload_dir=pending_upload_dir,
        upload_mode=args.upload_mode,
    )

    status_payload = {
        "package_dir": str(package_dir),
        "transcript_action": transcript_action,
        "question_action": question_action,
        "transcript_error": transcript_error,
        "question_error": question_error,
        "transcript_segment_count": _count_transcript_segments(transcript_payload),
        "question_event_count": _count_question_events(question_payload),
        "analysis_id": analyze_result.get("analysis_id"),
        "output_path": analyze_result.get("output_path"),
        "delivery": analyze_result.get("delivery"),
    }
    status_path = enrichment_dir / "enrich_and_analyze_status.json"
    status_path.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PHASE35C_ENRICH_PACKAGE_DIR={package_dir}")
    print(f"PHASE35C_ENRICH_TRANSCRIPT_ACTION={transcript_action}")
    print(f"PHASE35C_ENRICH_QUESTION_ACTION={question_action}")
    print(f"PHASE35C_ENRICH_TRANSCRIPT_SEGMENT_COUNT={_count_transcript_segments(transcript_payload)}")
    print(f"PHASE35C_ENRICH_QUESTION_EVENT_COUNT={_count_question_events(question_payload)}")
    print(f"PHASE35C_ENRICH_STATUS_JSON={status_path}")
    print(f"PHASE35C_ENRICH_ANALYSIS_ID={analyze_result.get('analysis_id', '')}")
    print(f"PHASE35C_ENRICH_OUTPUT_JSON={analyze_result.get('output_path', '')}")
    if transcript_error:
        print(f"PHASE35C_ENRICH_TRANSCRIPT_ERROR={transcript_error}")
    if question_error:
        print(f"PHASE35C_ENRICH_QUESTION_ERROR={question_error}")
    print(
        "PHASE35C_ENRICH_AND_ANALYZE_OK="
        + _bool_text(bool(analyze_result.get("output_path")) and (_transcript_payload_has_segments(transcript_payload) or transcript_action != "generated_unavailable"))
    )
    return 0


def _ensure_transcript_payload(
    *,
    phase312: Any,
    package_dir: Path,
    metadata: dict[str, Any],
    transcript_path: Path,
    video_path: Path,
    audio_path: Path,
    enrichment_dir: Path,
    explicit_transcript_json: Path | None,
    engine: str,
    model: str,
    language: str,
    device: str,
    compute_type: str,
) -> tuple[dict[str, Any], str, str]:
    external_candidates = [
        explicit_transcript_json,
        _coerce_existing_path(metadata.get("transcript_path")),
    ]
    for candidate in external_candidates:
        if candidate and candidate.exists():
            payload = _read_json(candidate)
            if _transcript_payload_has_segments(payload):
                transcript_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                return payload, "imported", ""

    if not video_path.exists():
        return {}, "generated_unavailable", f"video_missing: {video_path}"

    if not audio_path.exists() or audio_path.stat().st_size <= 0:
        try:
            phase312.extract_audio(video_path, audio_path, force=False)
        except Exception as exc:  # noqa: BLE001
            return {}, "generated_unavailable", f"audio_extract_failed: {exc}"

    selected = phase312.select_engine(engine, model)
    if selected is None:
        return {}, "generated_unavailable", phase312.build_no_engine_message(model)

    try:
        segments = phase312.run_asr(selected, audio_path, language, device, compute_type)
    except Exception as exc:  # noqa: BLE001
        return {}, "generated_unavailable", f"asr_failed: {exc}"

    if not segments:
        return {}, "generated_unavailable", "asr_returned_zero_segments"

    transcript_json_path = enrichment_dir / "transcript.json"
    transcript_csv_path = enrichment_dir / "transcript.csv"
    analysis_id = str(metadata.get("analysis_id") or package_dir.name)
    phase312.write_transcript_json(
        transcript_json_path=transcript_json_path,
        analysis_id=analysis_id,
        source_video=video_path,
        audio_path=audio_path,
        engine=selected["engine"],
        model=selected["model_display"],
        language=language,
        segments=segments,
    )
    phase312.write_transcript_csv(transcript_csv_path, segments)
    payload = _read_json(transcript_json_path)
    transcript_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload, "generated", ""


def _ensure_question_payload(
    *,
    phase313: Any,
    metadata: dict[str, Any],
    transcript_payload: dict[str, Any],
    questions_path: Path,
    explicit_question_csv: Path | None,
) -> tuple[dict[str, Any], str, str]:
    external_candidates = [
        explicit_question_csv,
        _coerce_existing_path(metadata.get("question_event_path")),
    ]
    for candidate in external_candidates:
        if candidate and candidate.exists():
            if candidate.suffix.lower() == ".csv":
                payload = _question_payload_from_csv(candidate)
            else:
                payload = _read_json(candidate)
            if _question_payload_has_events(payload):
                questions_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                return payload, "imported", ""

    segments = transcript_payload.get("segments") if isinstance(transcript_payload, dict) else None
    if not isinstance(segments, list) or not segments:
        return {}, "generated_unavailable", "transcript_missing_or_empty"

    normalized_segments = [
        phase313.normalize_segment(segment)
        for segment in segments
        if isinstance(segment, dict)
    ]
    raw_candidates = [
        candidate
        for segment in normalized_segments
        if (candidate := phase313.detect_question_candidate(segment))
    ]
    question_events = phase313.merge_question_candidates(raw_candidates)
    question_events = [
        {
            **event,
            "event_id": f"q_{index:03d}",
            "question_id": f"q_{index:03d}",
        }
        for index, event in enumerate(question_events, start=1)
    ]
    if not question_events:
        payload = {
            "status": "unavailable",
            "questions": [],
            "summary": {"question_count": 0},
            "reason": "no_question_candidates_detected_from_transcript",
        }
        questions_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload, "generated", ""

    payload = {
        "status": "available",
        "source": "asr_rule_detection",
        "questions": question_events,
        "summary": {
            "question_count": len(question_events),
            "notes": "Generated from local transcript using the existing Phase 3.13 question-candidate rules.",
        },
    }
    questions_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload, "generated", ""


def _question_payload_from_csv(path: Path) -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            questions.append(
                {
                    "event_id": str(row.get("event_id") or row.get("question_id") or ""),
                    "question_id": str(row.get("event_id") or row.get("question_id") or ""),
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
        "source": "imported_question_csv",
        "questions": questions,
        "summary": {
            "question_count": len(questions),
            "notes": "Imported from precomputed question_events.csv.",
        },
    }


def _load_script_module(module_name: str, file_path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot_load_module: {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _transcript_payload_has_segments(payload: dict[str, Any]) -> bool:
    segments = payload.get("segments") if isinstance(payload, dict) else None
    return isinstance(segments, list) and any(isinstance(item, dict) and str(item.get("text") or "").strip() for item in segments)


def _question_payload_has_events(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    for key in ("questions", "teacher_question_events", "question_events", "events", "items", "segments"):
        items = payload.get(key)
        if isinstance(items, list) and any(isinstance(item, dict) for item in items):
            return True
    return False


def _count_transcript_segments(payload: dict[str, Any]) -> int:
    segments = payload.get("segments") if isinstance(payload, dict) else None
    return len([item for item in segments if isinstance(item, dict)]) if isinstance(segments, list) else 0


def _count_question_events(payload: dict[str, Any]) -> int:
    if not isinstance(payload, dict):
        return 0
    for key in ("questions", "teacher_question_events", "question_events", "events", "items", "segments"):
        items = payload.get(key)
        if isinstance(items, list):
            return len([item for item in items if isinstance(item, dict)])
    return 0


def _coerce_existing_path(value: Any) -> Path | None:
    if not value:
        return None
    try:
        path = Path(str(value)).resolve()
    except OSError:
        return None
    return path if path.exists() else None


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(str(value or default))
    except ValueError:
        return default


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
