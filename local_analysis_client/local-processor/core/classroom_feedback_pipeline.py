from __future__ import annotations

import copy
import json
import logging
import math
import shutil
import socket
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import cv2
import numpy as np
import requests

from yolo_interaction_processor import (
    build_default_processor,
    load_processor_config,
    resolve_config_path,
    validate_result_payload,
)


LOGGER = logging.getLogger("classroom_feedback_pipeline")
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DELIVERY_ROOT = REPO_ROOT / "captures_local_delivery"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "processed_results" / "classroom_feedback"
DEFAULT_PENDING_UPLOAD_DIR = REPO_ROOT / "processed_results" / "pending_upload"
DEFAULT_RUNTIME_FRAME_DIR = REPO_ROOT / "processed_results" / "runtime_frames"
SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a"}
UPLOAD_API_PATH = "/api/interaction-results"
UPLOAD_WITH_VIDEO_API_PATH = "/api/interaction-results/with-video"
LOCAL_ANALYZER_CLIENT_VERSION = "local-analyzer-v1"
MAX_PENDING_UPLOAD_RETRIES = 3
LOCAL_DELIVERY_METADATA_KEY = "_local_delivery"
PENDING_UPLOAD_METADATA_KEY = "pending_upload"
PHASE32_ANALYSIS_VERSION = "3.2"
PHASE32_RULESET = "classroom_behavior_v3_2"
PHASE32_SCORE_WEIGHTS = {
    "attention_score": 0.30,
    "activity_score": 0.20,
    "interaction_score": 0.20,
    "rhythm_score": 0.20,
    "evidence_score": 0.10,
}
PHASE33_GUIDANCE_SCORE_WEIGHTS = {
    "question_count_score": 0.30,
    "coverage_score": 0.25,
    "open_question_score": 0.15,
    "response_signal_score": 0.20,
    "source_confidence_score": 0.10,
}


def analyze_delivery_package(
    package_dir: str | Path,
    *,
    config_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    upload_mode: str = "auto",
    pending_upload_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Analyze a Raspberry Pi delivery package and emit classroom feedback JSON v1.1."""
    package_dir = Path(package_dir).resolve()
    delivery = _load_delivery_package(package_dir)
    metadata = dict(delivery["metadata"])
    metadata["package_dir"] = str(package_dir)
    capture_metadata = delivery.get("capture_metadata") or {}

    video_path: Path | None = delivery["video_path"]
    audio_path: Path | None = delivery["audio_path"]

    processor = build_default_processor(config_path or resolve_config_path())
    cloud_upload_enabled = bool(processor.config.cloud_push_enabled)
    processor.config.cloud_push_enabled = False
    processor.config.save_debug_json = False

    output_dir = Path(output_dir).resolve() if output_dir else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    pending_upload_dir = Path(pending_upload_dir).resolve() if pending_upload_dir else DEFAULT_PENDING_UPLOAD_DIR
    pending_upload_dir.mkdir(parents=True, exist_ok=True)

    local_source_host = str(metadata.get("local_source_host") or socket.gethostname() or processor.config.source_host)
    recorded_at = _resolve_recorded_at(metadata)
    duration_seconds = _resolve_duration_seconds(metadata, video_path, audio_path)
    analysis_id = str(metadata.get("analysis_id") or _generate_analysis_id(metadata, recorded_at))
    video_id = str(metadata.get("video_id") or _generate_video_id(metadata, video_path, analysis_id))
    classroom_id = str(metadata.get("classroom_id") or _extract_path_context(package_dir).get("classroom_id") or "unknown_classroom")

    teacher_question_input = _resolve_teacher_question_input(
        metadata=metadata,
        questions_payload=delivery.get("teacher_questions_payload"),
        transcript_payload=delivery.get("teacher_transcript_payload"),
    )
    teacher_signal_metadata = _build_teacher_signal_metadata(
        metadata=metadata,
        transcript_payload=delivery.get("teacher_transcript_payload"),
        question_input=teacher_question_input,
    )
    question_events = processor._build_teacher_question_events(teacher_signal_metadata)
    stage_distribution = processor._build_stage_distribution(teacher_signal_metadata)

    window_size_seconds = int(
        metadata.get("window_size_seconds")
        or metadata.get("timeline", {}).get("window_size_seconds")
        or 60
    )
    student_window_results = _analyze_student_video_windows(
        processor=processor,
        video_path=video_path,
        classroom_id=classroom_id,
        analysis_id=analysis_id,
        recorded_at=recorded_at,
        duration_seconds=duration_seconds,
        window_size_seconds=window_size_seconds,
        metadata=metadata,
    )
    audio_heat_curve = _analyze_audio_heat_curve(
        audio_path=audio_path,
        duration_seconds=duration_seconds,
        window_size_seconds=window_size_seconds,
        metadata=metadata,
    )

    zone_summary = _aggregate_zone_summary(student_window_results, metadata)
    hand_raise_event_count = int(sum(item["hand_raise_event_count"] for item in student_window_results))
    estimated_student_count = _resolve_estimated_student_count(metadata)
    avg_attention_ratio = _resolve_avg_attention_ratio(metadata, zone_summary)
    attention_curve = _build_attention_curve(metadata, student_window_results, avg_attention_ratio)
    activity_curve = _build_activity_curve(metadata, student_window_results)
    target_length = max(1, math.ceil(duration_seconds / max(window_size_seconds, 1))) if duration_seconds > 0 else max(
        len(attention_curve),
        len(activity_curve),
        len(audio_heat_curve),
        1,
    )
    attention_curve = _normalize_curve(attention_curve, target_length=target_length)
    activity_curve = _normalize_curve(activity_curve, target_length=target_length)
    heat_curve = _normalize_curve(audio_heat_curve, target_length=target_length)

    response_events = _enrich_question_events_with_response(
        question_events=question_events,
        activity_curve=activity_curve,
        heat_curve=heat_curve,
        student_window_results=student_window_results,
        window_size_seconds=window_size_seconds,
    )
    teacher_question_count = len(response_events)
    response_success_rate = _compute_response_success_rate(response_events)
    attention_score = round(avg_attention_ratio * 100, 2)
    response_score = _compute_response_score(response_events)
    avg_activity = (sum(activity_curve) / len(activity_curve)) if activity_curve else 0.0
    feedback_score = round(
        min(max((0.45 * attention_score) + (0.4 * response_score) + (0.15 * avg_activity * 100), 0.0), 100.0),
        2,
    )
    output_path = output_dir / f"{analysis_id}.json"
    video_capability = _audit_local_video_capability()
    capture_block = _extract_capture_block(capture_metadata)
    capture_video_block = _extract_capture_video_block(capture_metadata)
    video_metadata = _build_video_metadata(
        metadata=metadata,
        capture_block=capture_block,
        capture_video_block=capture_video_block,
        video_path=video_path,
        video_id=video_id,
        duration_seconds=duration_seconds,
        video_capability=video_capability,
    )
    upload_metadata = _build_upload_metadata(processor.config.cloud_push_url)
    generated_at = _utc_now_iso()
    phase32_enhancement = _build_phase3_2_enhancement(
        processor=processor,
        package_dir=package_dir,
        metadata=metadata,
        video_path=video_path,
        audio_path=audio_path,
        transcript_payload=delivery.get("teacher_transcript_payload"),
        student_window_results=student_window_results,
        response_events=response_events,
        stage_distribution=stage_distribution,
        attention_curve=attention_curve,
        activity_curve=activity_curve,
        heat_curve=heat_curve,
        window_size_seconds=window_size_seconds,
        duration_seconds=duration_seconds,
        video_metadata=video_metadata,
        estimated_student_count=estimated_student_count,
        generated_at=generated_at,
        target_window_count=target_length,
    )
    phase33_guidance = _build_phase3_3_question_guidance(
        question_input=teacher_question_input,
        response_events=response_events,
        attention_curve=attention_curve,
        activity_curve=activity_curve,
        student_window_results=student_window_results,
        stage_distribution=stage_distribution,
        duration_seconds=duration_seconds,
        window_size_seconds=window_size_seconds,
    )

    result = {
        "schema_version": "v1.1",
        "analysis_id": analysis_id,
        "classroom_id": classroom_id,
        "video_id": video_id,
        "source": {
            "source_kind": "local_analyzer",
            "source_path": str(output_path),
            "source_host": local_source_host,
        },
        "time": {
            "recorded_at": recorded_at,
            "generated_at": generated_at,
            "duration_seconds": int(duration_seconds),
        },
        "summary": {
            "feedback_score": feedback_score,
            "attention_score": attention_score,
            "response_score": response_score,
            "teacher_question_count": teacher_question_count,
            "avg_attention_ratio": round(avg_attention_ratio, 4),
            "response_success_rate": round(response_success_rate, 4),
            "summary_text": _build_summary_text(
                teacher_question_count=teacher_question_count,
                avg_attention_ratio=avg_attention_ratio,
                response_success_rate=response_success_rate,
                activity_curve=activity_curve,
            ),
        },
        "teacher": {
            "question_events": response_events,
            "stage_distribution": stage_distribution,
        },
        "students": {
            "estimated_student_count": estimated_student_count,
            "hand_raise_event_count": hand_raise_event_count,
            "zones": zone_summary,
        },
        "timeline": {
            "window_size_seconds": window_size_seconds,
            "attention_curve": attention_curve,
            "heat_curve": heat_curve,
            "activity_curve": activity_curve,
        },
    }
    result.update(phase32_enhancement)
    result.update(phase33_guidance)
    if capture_block:
        result["capture"] = capture_block
    teacher_cfg = metadata.get("teacher", {})
    if isinstance(teacher_cfg, dict) and "question_summary" in teacher_cfg:
        result["teacher"]["question_summary"] = teacher_cfg["question_summary"]
    result["video"] = video_metadata
    result["upload"] = upload_metadata

    validation = validate_result_payload(result)
    if not validation["is_valid"]:
        raise ValueError(f"课堂反馈 JSON 校验失败: {json.dumps(validation, ensure_ascii=False)}")

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Classroom feedback JSON written: %s", output_path)

    delivery_result = _deliver_result_json(
        result_data=result,
        output_path=output_path,
        upload_mode=upload_mode,
        pending_upload_dir=pending_upload_dir,
        cloud_push_enabled=cloud_upload_enabled,
        cloud_push_url=processor.config.cloud_push_url,
        timeout_seconds=processor.config.cloud_push_timeout,
        headers=processor.config.cloud_push_headers,
    )
    return {
        "analysis_id": analysis_id,
        "package_dir": str(package_dir),
        "metadata_path": str(delivery["metadata_path"]) if delivery["metadata_path"] else None,
        "capture_metadata_path": str(delivery["capture_metadata_path"]) if delivery.get("capture_metadata_path") else None,
        "capture_metadata_status": delivery.get("capture_metadata_status"),
        "output_path": str(output_path),
        "delivery": delivery_result,
        "validation": validation,
        "result": result,
    }


def _load_delivery_package(package_dir: Path) -> dict[str, Any]:
    if not package_dir.exists():
        raise FileNotFoundError(f"Delivery package directory not found: {package_dir}")

    metadata_path = package_dir / "metadata.json"
    teacher_questions_path = package_dir / "teacher_questions.json"
    teacher_transcript_path = package_dir / "teacher_transcript.json"
    metadata: dict[str, Any] = {}
    teacher_questions_payload: Any = None
    teacher_transcript_payload: Any = None
    if metadata_path.exists():
        metadata = _read_json_file(metadata_path)
    if teacher_questions_path.exists():
        teacher_questions_payload = _read_json_file(teacher_questions_path)
    if teacher_transcript_path.exists():
        teacher_transcript_payload = _read_json_file(teacher_transcript_path)

    preferred_video_path = package_dir / "video.mp4"
    preferred_audio_path = package_dir / "audio.wav"
    video_path = preferred_video_path if preferred_video_path.exists() else next(
        (path for path in sorted(package_dir.iterdir()) if path.suffix.lower() in SUPPORTED_VIDEO_SUFFIXES),
        None,
    )
    audio_path = preferred_audio_path if preferred_audio_path.exists() else next(
        (path for path in sorted(package_dir.iterdir()) if path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES),
        None,
    )
    capture_metadata, capture_metadata_path, capture_metadata_status = _load_capture_metadata(
        package_dir=package_dir,
        video_path=video_path,
        audio_path=audio_path,
    )
    return {
        "metadata": metadata,
        "video_path": video_path,
        "audio_path": audio_path,
        "metadata_path": metadata_path if metadata_path.exists() else None,
        "capture_metadata": capture_metadata,
        "capture_metadata_path": capture_metadata_path,
        "capture_metadata_status": capture_metadata_status,
        "teacher_questions_path": teacher_questions_path if teacher_questions_path.exists() else None,
        "teacher_questions_payload": teacher_questions_payload,
        "teacher_transcript_path": teacher_transcript_path if teacher_transcript_path.exists() else None,
        "teacher_transcript_payload": teacher_transcript_payload,
    }


def _load_capture_metadata(
    *,
    package_dir: Path,
    video_path: Path | None,
    audio_path: Path | None,
) -> tuple[dict[str, Any], Path | None, str]:
    candidate_dirs = [package_dir]
    for media_path in (video_path, audio_path):
        if media_path is not None:
            candidate_dirs.append(media_path.parent)
    candidate_dirs.extend([package_dir / "keyframes", package_dir.parent])

    seen: set[Path] = set()
    for candidate_dir in candidate_dirs:
        candidate_path = (candidate_dir / "capture_metadata.json").resolve()
        if candidate_path in seen:
            continue
        seen.add(candidate_path)
        if not candidate_path.exists():
            continue
        try:
            payload = _read_json_file(candidate_path)
        except Exception as exc:
            LOGGER.warning("Failed to read capture_metadata.json at %s: %s", candidate_path, exc)
            return {}, candidate_path, "invalid"
        if not isinstance(payload, dict):
            LOGGER.warning("capture_metadata.json at %s is not a JSON object.", candidate_path)
            return {}, candidate_path, "invalid"
        if not isinstance(payload.get("capture"), dict):
            LOGGER.warning("capture_metadata.json at %s does not contain a capture object.", candidate_path)
            return payload, candidate_path, "missing_capture"
        LOGGER.info("Loaded capture metadata: %s", candidate_path)
        return payload, candidate_path, "loaded"

    LOGGER.info("capture_metadata.json not found for package: %s", package_dir)
    return {}, None, "missing"


def _read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_recorded_at(metadata: dict[str, Any]) -> str:
    for key in ("recorded_at", "started_at", "start_time"):
        value = metadata.get(key)
        if value:
            return str(value)
    return _utc_now_iso()


def _resolve_duration_seconds(metadata: dict[str, Any], video_path: Path | None, audio_path: Path | None) -> int:
    if video_path is not None:
        capture = cv2.VideoCapture(str(video_path))
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
            if fps > 0 and frame_count > 0:
                return max(1, int(frame_count / fps))
        finally:
            capture.release()
    if audio_path is not None and audio_path.suffix.lower() == ".wav":
        with wave.open(str(audio_path), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            if frame_rate > 0:
                return max(1, int(frame_count / frame_rate))
    if metadata.get("duration_seconds") is not None:
        return int(metadata["duration_seconds"])
    return 0


def _generate_analysis_id(metadata: dict[str, Any], recorded_at: str) -> str:
    path_ctx = _extract_path_context(Path(metadata["package_dir"])) if metadata.get("package_dir") else {}
    classroom_id = str(metadata.get("classroom_id") or path_ctx.get("classroom_id") or "classroom")
    safe_date = recorded_at[:10].replace("-", "") if recorded_at else "unknown"
    session_id = str(metadata.get("session_id") or path_ctx.get("session_id") or "001").replace("-", "_")
    return f"cls_{safe_date}_{classroom_id}_{session_id}"


def _generate_video_id(metadata: dict[str, Any], video_path: Path | None, analysis_id: str) -> str:
    if video_path is not None:
        return f"video_{video_path.stem}"
    if metadata.get("session_id"):
        return f"video_{metadata['session_id']}"
    return f"video_{analysis_id}"


def _resolve_source_path(
    metadata: dict[str, Any],
    video_path: Path | None,
    audio_path: Path | None,
    package_dir: Path,
) -> str:
    if metadata.get("source_path"):
        return str(metadata["source_path"])
    preferred_source = video_path or audio_path or package_dir
    try:
        return str(preferred_source.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(preferred_source)


def _extract_capture_block(capture_metadata: dict[str, Any]) -> dict[str, Any]:
    capture_block = capture_metadata.get("capture") if isinstance(capture_metadata, dict) else None
    if not isinstance(capture_block, dict):
        return {}
    return dict(capture_block)


def _extract_capture_video_block(capture_metadata: dict[str, Any]) -> dict[str, Any]:
    video_block = capture_metadata.get("video") if isinstance(capture_metadata, dict) else None
    if not isinstance(video_block, dict):
        return {}
    return dict(video_block)


def _build_video_metadata(
    *,
    metadata: dict[str, Any],
    capture_block: dict[str, Any],
    capture_video_block: dict[str, Any],
    video_path: Path | None,
    video_id: str,
    duration_seconds: int,
    video_capability: dict[str, str],
) -> dict[str, Any]:
    standardized_video_path = str(
        capture_video_block.get("standardized_video_path")
        or capture_block.get("standardized_video_path")
        or metadata.get("standardized_video_path")
        or ""
    )
    raw_video_path = str(video_path) if video_path is not None else str(
        metadata.get("video_path") or capture_block.get("video_path") or standardized_video_path or ""
    )
    video_format = (video_path.suffix.lower().lstrip(".") if video_path is not None else "").lower()
    codec = _detect_video_codec(video_path)
    browser_compatible_value = capture_video_block.get("browser_compatible", metadata.get("browser_compatible"))
    if browser_compatible_value is None:
        browser_compatible = bool(video_format == "mp4" and codec.lower() in {"h264", "avc1"})
    else:
        browser_compatible = bool(browser_compatible_value)
    video_metadata = {
        "video_id": video_id,
        "raw_video_path": raw_video_path,
        "video_url": str(metadata.get("video_url") or ""),
        "duration_seconds": int(duration_seconds),
        "format": video_format,
        "codec": codec,
        "browser_compatible": browser_compatible,
        "transcode_capability": video_capability["transcode_capability"],
    }
    if standardized_video_path:
        video_metadata["standardized_video_path"] = standardized_video_path
    if "transcode_status" in capture_video_block or "transcode_status" in metadata:
        video_metadata["transcode_status"] = str(capture_video_block.get("transcode_status") or metadata.get("transcode_status") or "")
    if "transcode_error" in capture_video_block or "transcode_error" in metadata:
        video_metadata["transcode_error"] = str(capture_video_block.get("transcode_error") or metadata.get("transcode_error") or "")
    return video_metadata


def _detect_video_codec(video_path: Path | None) -> str:
    if video_path is None:
        return "unknown"
    capture = cv2.VideoCapture(str(video_path))
    try:
        fourcc = int(capture.get(cv2.CAP_PROP_FOURCC) or 0)
    finally:
        capture.release()
    if not fourcc:
        return "unknown"
    codec = "".join(chr((fourcc >> (8 * index)) & 0xFF) for index in range(4)).strip()
    return codec.lower() or "unknown"


def _build_upload_metadata(cloud_push_url: str | None = None) -> dict[str, Any]:
    return {
        "uploaded_at": _utc_now_iso(),
        "target": "cloud_backend",
        "api": _resolve_upload_api_path(cloud_push_url),
        "client_version": LOCAL_ANALYZER_CLIENT_VERSION,
    }


def _resolve_upload_api_path(cloud_push_url: str | None) -> str:
    if not cloud_push_url:
        return UPLOAD_API_PATH
    parsed = urlparse(str(cloud_push_url).strip())
    path = (parsed.path or "").strip()
    return path or UPLOAD_API_PATH


def _cloud_push_requires_video_upload(cloud_push_url: str | None) -> bool:
    path = _resolve_upload_api_path(cloud_push_url).rstrip("/")
    return path.endswith(UPLOAD_WITH_VIDEO_API_PATH)


def _prepare_upload_payload(result_data: dict[str, Any], cloud_push_url: str) -> dict[str, Any]:
    payload = _strip_local_delivery_metadata(result_data)
    payload["upload"] = _build_upload_metadata(cloud_push_url)
    if _cloud_push_requires_video_upload(cloud_push_url):
        video_block = payload.get("video")
        if isinstance(video_block, dict):
            video_block = dict(video_block)
            video_block.pop("video_url", None)
            payload["video"] = video_block
    return payload


def _resolve_upload_video_path(result_data: dict[str, Any]) -> Path | None:
    candidate_values: list[Any] = []
    video_block = result_data.get("video")
    if isinstance(video_block, dict):
        candidate_values.extend(
            [
                video_block.get("raw_video_path"),
                video_block.get("standardized_video_path"),
            ]
        )
    capture_block = result_data.get("capture")
    if isinstance(capture_block, dict):
        candidate_values.extend(
            [
                capture_block.get("video_path"),
                capture_block.get("standardized_video_path"),
            ]
        )
    for value in candidate_values:
        if not value:
            continue
        candidate = Path(str(value)).expanduser()
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _build_upload_video_filename(result_data: dict[str, Any], video_path: Path) -> str:
    analysis_id = str(result_data.get("analysis_id") or video_path.stem).strip() or video_path.stem
    suffix = video_path.suffix or ".mp4"
    return f"{analysis_id}{suffix}"


def _build_pending_upload_metadata(
    *,
    retry_count: int,
    attempted: bool,
    status: str,
    last_error: str | None,
    last_http_status: int | None,
) -> dict[str, Any]:
    return {
        "retry_count": max(int(retry_count), 0),
        "max_retries": MAX_PENDING_UPLOAD_RETRIES,
        "attempted": bool(attempted),
        "status": status,
        "last_error": str(last_error or ""),
        "last_http_status": last_http_status,
        "last_attempt_at": _utc_now_iso(),
    }


def _read_pending_upload_metadata(result_data: dict[str, Any]) -> dict[str, Any]:
    local_delivery = result_data.get(LOCAL_DELIVERY_METADATA_KEY)
    if not isinstance(local_delivery, dict):
        return {}
    pending_upload = local_delivery.get(PENDING_UPLOAD_METADATA_KEY)
    if not isinstance(pending_upload, dict):
        return {}
    return dict(pending_upload)


def _apply_pending_upload_metadata(
    result_data: dict[str, Any],
    *,
    retry_count: int,
    attempted: bool,
    status: str,
    last_error: str | None,
    last_http_status: int | None,
) -> dict[str, Any]:
    payload = copy.deepcopy(result_data)
    local_delivery = payload.get(LOCAL_DELIVERY_METADATA_KEY)
    if not isinstance(local_delivery, dict):
        local_delivery = {}
    else:
        local_delivery = dict(local_delivery)
    local_delivery[PENDING_UPLOAD_METADATA_KEY] = _build_pending_upload_metadata(
        retry_count=retry_count,
        attempted=attempted,
        status=status,
        last_error=last_error,
        last_http_status=last_http_status,
    )
    payload[LOCAL_DELIVERY_METADATA_KEY] = local_delivery
    return payload


def _strip_local_delivery_metadata(result_data: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(result_data)
    payload.pop(LOCAL_DELIVERY_METADATA_KEY, None)
    return payload


def _write_pending_result_json(
    *,
    pending_path: Path,
    result_data: dict[str, Any],
    retry_count: int,
    attempted: bool,
    status: str,
    last_error: str | None,
    last_http_status: int | None,
) -> None:
    pending_payload = _apply_pending_upload_metadata(
        result_data,
        retry_count=retry_count,
        attempted=attempted,
        status=status,
        last_error=last_error,
        last_http_status=last_http_status,
    )
    pending_path.write_text(json.dumps(pending_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_phase3_2_enhancement(
    *,
    processor: Any,
    package_dir: Path,
    metadata: dict[str, Any],
    video_path: Path | None,
    audio_path: Path | None,
    transcript_payload: Any,
    student_window_results: list[dict[str, Any]],
    response_events: list[dict[str, Any]],
    stage_distribution: dict[str, float],
    attention_curve: list[float],
    activity_curve: list[float],
    heat_curve: list[float],
    window_size_seconds: int,
    duration_seconds: int,
    video_metadata: dict[str, Any],
    estimated_student_count: int,
    generated_at: str,
    target_window_count: int,
) -> dict[str, Any]:
    """Build optional Phase 3.2 fields without changing the legacy v1.1 contract."""
    keyframe_count = _count_keyframes(package_dir)
    quality_metrics = _build_quality_metrics(
        video_path=video_path,
        keyframe_count=keyframe_count,
        student_window_results=student_window_results,
        target_window_count=target_window_count,
    )
    evidence_summary = _build_evidence_summary(
        video_path=video_path,
        audio_path=audio_path,
        transcript_payload=transcript_payload,
        video_metadata=video_metadata,
        keyframe_count=keyframe_count,
        quality_metrics=quality_metrics,
        response_events=response_events,
        estimated_student_count=estimated_student_count,
    )
    score_breakdown = _build_score_breakdown(
        attention_curve=attention_curve,
        activity_curve=activity_curve,
        response_events=response_events,
        stage_distribution=stage_distribution,
        quality_metrics=quality_metrics,
        evidence_summary=evidence_summary,
        duration_seconds=duration_seconds,
    )
    enhanced_events = _build_enhanced_events(
        attention_curve=attention_curve,
        response_events=response_events,
        window_size_seconds=window_size_seconds,
    )
    enhanced_issues = _build_enhanced_issues(
        attention_curve=attention_curve,
        response_events=response_events,
        stage_distribution=stage_distribution,
        quality_metrics=quality_metrics,
        duration_seconds=duration_seconds,
    )
    return {
        "analysis_version": PHASE32_ANALYSIS_VERSION,
        "algorithm_profile": _build_algorithm_profile(
            processor=processor,
            window_size_seconds=window_size_seconds,
            generated_at=generated_at,
        ),
        "quality_metrics": quality_metrics,
        "score_breakdown": score_breakdown,
        "curve_metadata": _build_curve_metadata(
            attention_curve=attention_curve,
            activity_curve=activity_curve,
            window_size_seconds=window_size_seconds,
        ),
        "evidence_summary": evidence_summary,
        "enhanced_events": enhanced_events,
        "enhanced_issues": enhanced_issues,
    }


def _build_algorithm_profile(*, processor: Any, window_size_seconds: int, generated_at: str) -> dict[str, Any]:
    return {
        "detector": "yolo",
        "detector_version": "ultralytics-8.3.163",
        "model_name": _safe_model_name(getattr(processor.config, "merged_model_path", None)),
        "ruleset": PHASE32_RULESET,
        "window_seconds": int(window_size_seconds),
        "confidence_policy": "window_aggregation",
        "generated_at": generated_at,
    }


def _safe_model_name(model_path: Path | None) -> str:
    if model_path is None:
        return "unknown"
    parts = model_path.parts
    if len(parts) >= 3:
        return f"{parts[-3]}/{parts[-1]}"
    return model_path.name or "unknown"


def _build_quality_metrics(
    *,
    video_path: Path | None,
    keyframe_count: int,
    student_window_results: list[dict[str, Any]],
    target_window_count: int,
) -> dict[str, Any]:
    frame_count = sum(int(item.get("sample_frame_count") or 0) for item in student_window_results)
    valid_frame_count = sum(int(item.get("valid_frame_count") or 0) for item in student_window_results)
    if video_path is not None and frame_count == 0 and target_window_count > 0:
        frame_count = target_window_count * 3

    valid_frame_ratio = round(valid_frame_count / frame_count, 4) if frame_count > 0 else 0.0
    missing_windows = max(int(target_window_count) - len(student_window_results), 0)
    low_confidence_windows = missing_windows
    for item in student_window_results:
        expected = int(item.get("sample_frame_count") or 0)
        valid = int(item.get("valid_frame_count") or 0)
        if expected > 0 and (valid / expected) < 0.67:
            low_confidence_windows += 1

    analysis_warnings: list[str] = []
    video_available = video_path is not None and video_path.exists()
    if not video_available:
        analysis_warnings.append("video_missing")
    if keyframe_count <= 0:
        analysis_warnings.append("keyframes_missing")
    if valid_frame_ratio < 0.85:
        analysis_warnings.append("valid_frame_ratio_below_high_threshold")
    if missing_windows > 0:
        analysis_warnings.append("missing_windows_detected")

    confidence_limit = max(1, math.ceil(max(target_window_count, 1) * 0.10))
    if video_available and valid_frame_ratio >= 0.85 and low_confidence_windows <= confidence_limit:
        data_confidence = "high"
    elif (video_available or keyframe_count > 0) and (valid_frame_ratio >= 0.60 or keyframe_count > 0):
        data_confidence = "medium"
    else:
        data_confidence = "low"

    return {
        "data_confidence": data_confidence,
        "video_available": video_available,
        "frame_count": int(frame_count),
        "valid_frame_count": int(valid_frame_count),
        "valid_frame_ratio": valid_frame_ratio,
        "low_confidence_windows": int(low_confidence_windows),
        "missing_windows": int(missing_windows),
        "analysis_warnings": analysis_warnings,
    }


def _build_score_breakdown(
    *,
    attention_curve: list[float],
    activity_curve: list[float],
    response_events: list[dict[str, Any]],
    stage_distribution: dict[str, float],
    quality_metrics: dict[str, Any],
    evidence_summary: dict[str, Any],
    duration_seconds: int,
) -> dict[str, Any]:
    attention_score = _compute_phase32_attention_score(attention_curve)
    activity_score = _compute_phase32_activity_score(activity_curve)
    interaction_score = _compute_phase32_interaction_score(
        response_events=response_events,
        stage_distribution=stage_distribution,
        duration_seconds=duration_seconds,
    )
    rhythm_score = _compute_phase32_rhythm_score(
        attention_curve=attention_curve,
        activity_curve=activity_curve,
        stage_distribution=stage_distribution,
    )
    evidence_score = _compute_phase32_evidence_score(
        quality_metrics=quality_metrics,
        evidence_summary=evidence_summary,
    )
    scores = {
        "attention_score": attention_score,
        "activity_score": activity_score,
        "interaction_score": interaction_score,
        "rhythm_score": rhythm_score,
        "evidence_score": evidence_score,
    }
    overall_score = round(sum(scores[key] * PHASE32_SCORE_WEIGHTS[key] for key in PHASE32_SCORE_WEIGHTS), 2)
    dominant_factor = min(scores, key=scores.get)
    return {
        **scores,
        "overall_score": overall_score,
        "dominant_factor": dominant_factor,
        "summary": _build_phase32_score_summary(overall_score, dominant_factor),
    }


def _compute_phase32_attention_score(attention_curve: list[float]) -> float:
    values = _moving_average_3(_to_percent_curve(attention_curve))
    if not values:
        return 0.0
    low_ratio = sum(1 for value in values if value < 50.0) / len(values)
    stability_penalty = min(_stddev(values), 30.0) * 0.30
    return _clamp_score(_mean(values) - (low_ratio * 20.0) - stability_penalty)


def _compute_phase32_activity_score(activity_curve: list[float]) -> float:
    values = _moving_average_3(_to_percent_curve(activity_curve))
    if not values:
        return 0.0
    mean_value = _mean(values)
    peak_value = max(values)
    zero_ratio = sum(1 for value in values if value < 2.0) / len(values)
    if mean_value < 5.0:
        range_score = mean_value * 10.0
    elif mean_value <= 35.0:
        range_score = 80.0 + min(mean_value, 20.0)
    else:
        range_score = max(30.0, 100.0 - ((mean_value - 35.0) * 1.5))
    peak_score = min(peak_value * 2.5, 100.0)
    continuity_score = (1.0 - zero_ratio) * 100.0
    return _clamp_score((range_score * 0.45) + (peak_score * 0.35) + (continuity_score * 0.20))


def _compute_phase32_interaction_score(
    *,
    response_events: list[dict[str, Any]],
    stage_distribution: dict[str, float],
    duration_seconds: int,
) -> float:
    question_ratio = float(stage_distribution.get("question_ratio") or 0.0)
    discussion_ratio = float(stage_distribution.get("discussion_ratio") or 0.0)
    interactive_ratio_score = min((question_ratio + discussion_ratio) / 0.25, 1.0) * 50.0
    expected_events = max(1.0, duration_seconds / 180.0) if duration_seconds > 0 else 1.0
    event_density_score = min(len(response_events) / expected_events, 1.0) * 30.0
    response_score = _compute_response_score(response_events) * 0.20
    return _clamp_score(interactive_ratio_score + event_density_score + response_score)


def _compute_phase32_rhythm_score(
    *,
    attention_curve: list[float],
    activity_curve: list[float],
    stage_distribution: dict[str, float],
) -> float:
    stage_values = [float(value) for value in stage_distribution.values() if isinstance(value, (int, float))]
    dominant_stage_ratio = max(stage_values) if stage_values else 1.0
    dominance_score = max(0.0, 100.0 - (dominant_stage_ratio * 60.0))
    attention_values = _moving_average_3(_to_percent_curve(attention_curve))
    activity_values = _moving_average_3(_to_percent_curve(activity_curve))
    attention_stability = max(0.0, 100.0 - min(_stddev(attention_values), 60.0))
    activity_stability = max(0.0, 100.0 - min(_stddev(activity_values) * 2.0, 60.0))
    return _clamp_score((dominance_score * 0.45) + (attention_stability * 0.35) + (activity_stability * 0.20))


def _compute_phase32_evidence_score(
    *,
    quality_metrics: dict[str, Any],
    evidence_summary: dict[str, Any],
) -> float:
    valid_frame_ratio = float(quality_metrics.get("valid_frame_ratio") or 0.0)
    score = valid_frame_ratio * 55.0
    if evidence_summary.get("video_path_present"):
        score += 20.0
    if int(evidence_summary.get("keyframe_count") or 0) > 0:
        score += 10.0
    if evidence_summary.get("audio_present"):
        score += 7.0
    if evidence_summary.get("transcript_present"):
        score += 8.0
    if quality_metrics.get("data_confidence") == "low":
        score -= 15.0
    return _clamp_score(score)


def _build_phase32_score_summary(overall_score: float, dominant_factor: str) -> str:
    labels = {
        "attention_score": "注意力稳定性",
        "activity_score": "学生活跃度",
        "interaction_score": "课堂互动",
        "rhythm_score": "课堂节奏",
        "evidence_score": "证据完整度",
    }
    factor_label = labels.get(dominant_factor, dominant_factor)
    return f"Phase 3.2 综合评分为 {overall_score:.2f}，当前主要受 {factor_label} 影响。"


def _build_curve_metadata(
    *,
    attention_curve: list[float],
    activity_curve: list[float],
    window_size_seconds: int,
) -> dict[str, Any]:
    point_count = max(len(attention_curve), len(activity_curve))
    valid_point_count = min(len(attention_curve), len(activity_curve))
    notes = ["legacy_timeline_curves_preserved", "score_breakdown_uses_moving_average_3"]
    return {
        "window_seconds": int(window_size_seconds),
        "smoothing": "moving_average_3",
        "point_count": int(point_count),
        "valid_point_count": int(valid_point_count),
        "source": "keyframe_window_aggregation",
        "notes": notes,
    }


def _build_evidence_summary(
    *,
    video_path: Path | None,
    audio_path: Path | None,
    transcript_payload: Any,
    video_metadata: dict[str, Any],
    keyframe_count: int,
    quality_metrics: dict[str, Any],
    response_events: list[dict[str, Any]],
    estimated_student_count: int,
) -> dict[str, Any]:
    evidence_level = str(quality_metrics.get("data_confidence") or "low")
    return {
        "video_path_present": bool(video_path is not None and video_path.exists()),
        "standardized_video_present": bool(video_metadata.get("standardized_video_path")),
        "keyframe_count": int(keyframe_count),
        "audio_present": bool(audio_path is not None and audio_path.exists()),
        "transcript_present": bool(_normalize_teacher_transcript_payload(transcript_payload)),
        "detected_student_count_avg": int(estimated_student_count),
        "detected_teacher_count_avg": 1.0 if response_events else 0.0,
        "evidence_level": evidence_level if evidence_level in {"high", "medium", "low"} else "low",
    }


def _build_enhanced_events(
    *,
    attention_curve: list[float],
    response_events: list[dict[str, Any]],
    window_size_seconds: int,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for start_index, end_index, average_value in _find_low_attention_segments(attention_curve):
        start_sec = start_index * window_size_seconds
        end_sec = (end_index + 1) * window_size_seconds
        events.append(
            {
                "event_id": f"evt_{len(events) + 1:03d}",
                "type": "low_attention",
                "label": "注意力下降",
                "time_range": _build_time_range(start_sec, end_sec),
                "severity": _severity_from_score(average_value, reverse=True),
                "confidence": round(max(0.50, min((50.0 - average_value) / 50.0 + 0.50, 0.95)), 2),
                "reason": "连续多个窗口专注表现低于阈值",
                "evidence": {"attention_avg": round(average_value, 2), "threshold": 50},
                "suggestion": "建议在该阶段加入提问、板演检查或短讨论。",
            }
        )

    for response_event in response_events[:5]:
        start_sec = float(response_event.get("start_sec") or 0.0)
        end_sec = float(response_event.get("end_sec") or start_sec + 10.0)
        response_type = str(response_event.get("response_type") or "none")
        events.append(
            {
                "event_id": f"evt_{len(events) + 1:03d}",
                "type": "teacher_question_response",
                "label": "教师提问与学生响应",
                "time_range": _build_time_range(start_sec, end_sec),
                "severity": "low" if response_type in {"strong", "medium"} else "medium",
                "confidence": 0.72,
                "reason": "基于教师提问事件和提问后学生行为变化生成",
                "evidence": {
                    "question_type": response_event.get("question_type"),
                    "response_type": response_type,
                    "delta_activity": response_event.get("delta_activity"),
                    "delta_heat": response_event.get("delta_heat"),
                },
                "suggestion": "结合该时间点查看课堂互动是否达到预期。",
            }
        )
    return events


def _build_enhanced_issues(
    *,
    attention_curve: list[float],
    response_events: list[dict[str, Any]],
    stage_distribution: dict[str, float],
    quality_metrics: dict[str, Any],
    duration_seconds: int,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    attention_values = _moving_average_3(_to_percent_curve(attention_curve))
    question_ratio = float(stage_distribution.get("question_ratio") or 0.0)
    discussion_ratio = float(stage_distribution.get("discussion_ratio") or 0.0)
    exposition_ratio = float(stage_distribution.get("exposition_ratio") or 0.0)

    if _find_low_attention_segments(attention_curve):
        issues.append(
            _build_issue(
                index=len(issues) + 1,
                issue_type="low_attention",
                label="注意力下降",
                severity="medium",
                affected_stage=_dominant_stage(stage_distribution),
                reason="存在连续多个窗口 attention 低于 50 分。",
                evidence={"low_attention_segments": len(_find_low_attention_segments(attention_curve))},
                suggestion="建议在低关注时间段安排提问、练习反馈或小组讨论。",
            )
        )

    expected_events = max(1.0, duration_seconds / 600.0) if duration_seconds > 0 else 1.0
    if (question_ratio < 0.08 and discussion_ratio < 0.10) or len(response_events) < expected_events:
        issues.append(
            _build_issue(
                index=len(issues) + 1,
                issue_type="low_interaction",
                label="互动引导不足",
                severity="medium",
                affected_stage=_dominant_stage(stage_distribution),
                reason="提问/讨论占比较低，或整节课可观测互动事件数量偏少。",
                evidence={
                    "question_ratio": round(question_ratio, 4),
                    "discussion_ratio": round(discussion_ratio, 4),
                    "interaction_event_count": len(response_events),
                },
                suggestion="建议设置 2-3 个检查性问题，并在关键概念后预留学生响应时间。",
            )
        )

    if exposition_ratio > 0.65 and (question_ratio + discussion_ratio) < 0.15:
        issues.append(
            _build_issue(
                index=len(issues) + 1,
                issue_type="single_rhythm",
                label="课堂节奏单一",
                severity="medium",
                affected_stage="exposition",
                reason="讲授占比较高，同时提问和讨论占比不足。",
                evidence={
                    "exposition_ratio": round(exposition_ratio, 4),
                    "question_discussion_ratio": round(question_ratio + discussion_ratio, 4),
                },
                suggestion="建议将连续讲授拆分为讲解、提问、练习反馈的短周期。",
            )
        )

    if _has_late_drop(attention_values):
        first_avg, last_avg = _first_last_third_avg(attention_values)
        issues.append(
            _build_issue(
                index=len(issues) + 1,
                issue_type="late_drop",
                label="后段课堂状态回落",
                severity="medium",
                affected_stage=_dominant_stage(stage_distribution),
                reason="后 1/3 注意力均值相比前 1/3 下降超过 15 分。",
                evidence={"first_third_attention": round(first_avg, 2), "last_third_attention": round(last_avg, 2)},
                suggestion="建议在课堂后段增加阶段总结、即时练习或学生展示。",
            )
        )

    if quality_metrics.get("data_confidence") == "low":
        issues.append(
            _build_issue(
                index=len(issues) + 1,
                issue_type="low_evidence",
                label="分析证据不足",
                severity="high",
                affected_stage="whole_class",
                reason="有效帧比例、视频/关键帧或窗口完整性不足，分析置信度为 low。",
                evidence={
                    "valid_frame_ratio": quality_metrics.get("valid_frame_ratio"),
                    "missing_windows": quality_metrics.get("missing_windows"),
                    "analysis_warnings": quality_metrics.get("analysis_warnings"),
                },
                suggestion="建议补齐视频、关键帧或重新执行采集后再复核分析结果。",
            )
        )

    return issues


def _build_issue(
    *,
    index: int,
    issue_type: str,
    label: str,
    severity: str,
    affected_stage: str,
    reason: str,
    evidence: dict[str, Any],
    suggestion: str,
) -> dict[str, Any]:
    return {
        "issue_id": f"issue_{index:03d}",
        "type": issue_type,
        "label": label,
        "severity": severity,
        "affected_stage": affected_stage,
        "reason": reason,
        "evidence": evidence,
        "suggestion": suggestion,
    }


def _count_keyframes(package_dir: Path) -> int:
    keyframe_dirs = [package_dir / "keyframes", package_dir / "frames"]
    image_suffixes = {".jpg", ".jpeg", ".png", ".bmp"}
    count = 0
    for keyframe_dir in keyframe_dirs:
        if not keyframe_dir.exists():
            continue
        count += sum(1 for path in keyframe_dir.rglob("*") if path.is_file() and path.suffix.lower() in image_suffixes)
    return count


def _to_percent_curve(curve: list[float]) -> list[float]:
    if not curve:
        return []
    values = [float(value) for value in curve]
    multiplier = 100.0 if max(values) <= 1.0 else 1.0
    return [_clamp_score(value * multiplier) for value in values]


def _moving_average_3(values: list[float]) -> list[float]:
    if len(values) <= 2:
        return [round(float(value), 4) for value in values]
    smoothed: list[float] = []
    for index in range(len(values)):
        start = max(0, index - 1)
        end = min(len(values), index + 2)
        smoothed.append(round(_mean(values[start:end]), 4))
    return smoothed


def _find_low_attention_segments(attention_curve: list[float]) -> list[tuple[int, int, float]]:
    values = _moving_average_3(_to_percent_curve(attention_curve))
    segments: list[tuple[int, int, float]] = []
    start_index: int | None = None
    for index, value in enumerate(values):
        if value < 50.0 and start_index is None:
            start_index = index
        if (value >= 50.0 or index == len(values) - 1) and start_index is not None:
            end_index = index - 1 if value >= 50.0 else index
            if end_index - start_index + 1 >= 2:
                segment_values = values[start_index:end_index + 1]
                segments.append((start_index, end_index, _mean(segment_values)))
            start_index = None
    return segments


def _has_late_drop(values: list[float]) -> bool:
    first_avg, last_avg = _first_last_third_avg(values)
    return bool(first_avg - last_avg >= 15.0)


def _first_last_third_avg(values: list[float]) -> tuple[float, float]:
    if len(values) < 3:
        return 0.0, 0.0
    segment_size = max(1, len(values) // 3)
    return _mean(values[:segment_size]), _mean(values[-segment_size:])


def _build_time_range(start_sec: float, end_sec: float) -> dict[str, Any]:
    return {
        "start": round(float(start_sec), 2),
        "end": round(float(end_sec), 2),
        "display": f"{_format_seconds(start_sec)}-{_format_seconds(end_sec)}",
    }


def _format_seconds(value: float) -> str:
    total_seconds = max(0, int(round(value)))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _severity_from_score(score: float, *, reverse: bool = False) -> str:
    value = 100.0 - score if reverse else score
    if value >= 70.0:
        return "high"
    if value >= 40.0:
        return "medium"
    return "low"


def _dominant_stage(stage_distribution: dict[str, float]) -> str:
    if not stage_distribution:
        return "whole_class"
    key = max(stage_distribution, key=lambda item: float(stage_distribution.get(item) or 0.0))
    return key.replace("_ratio", "") or "whole_class"


def _mean(values: list[float]) -> float:
    return (sum(values) / len(values)) if values else 0.0


def _stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    average = _mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def _clamp_score(value: float) -> float:
    return round(min(max(float(value), 0.0), 100.0), 2)


def _resolve_teacher_question_input(
    *,
    metadata: dict[str, Any],
    questions_payload: Any,
    transcript_payload: Any,
) -> dict[str, Any]:
    question_events, question_status = _extract_teacher_questions_events(questions_payload)
    if question_events:
        source = "demo_seed" if question_status == "demo" else "teacher_questions_json"
        status = "demo" if source == "demo_seed" else "available"
        for event in question_events:
            event["source"] = source
            event["question_source_status"] = status
        return {"status": status, "source": source, "events": question_events}

    transcript_segments = _normalize_teacher_transcript_payload(transcript_payload)
    if not transcript_segments:
        metadata_segments = metadata.get("teacher_transcript_segments") or metadata.get("teacher_segments") or []
        transcript_segments = [segment for segment in metadata_segments if isinstance(segment, dict)]

    transcript_events = []
    for index, segment in enumerate(transcript_segments, start=1):
        text = str(segment.get("text") or "").strip()
        if not text or not _looks_like_question_text(text):
            continue
        transcript_events.append(
            _normalize_question_source_event(
                index=index,
                event=segment,
                default_source="transcript_fallback",
            )
        )
    if transcript_events:
        return {"status": "available", "source": "transcript_fallback", "events": transcript_events}

    return {"status": "unavailable", "source": "teacher_transcript_empty", "events": []}


def _extract_teacher_questions_events(payload: Any) -> tuple[list[dict[str, Any]], str]:
    if payload is None:
        return [], "missing"
    status = "available"
    candidates: Any = None
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        status = str(payload.get("status") or payload.get("question_status") or "available").strip().lower()
        for key in ("questions", "teacher_question_events", "question_events", "events", "items", "segments"):
            if isinstance(payload.get(key), list):
                candidates = payload[key]
                break
        if candidates is None and payload.get("text"):
            candidates = [payload]
    if not isinstance(candidates, list):
        return [], status

    default_source = "demo_seed" if status == "demo" else "teacher_questions_json"
    events: list[dict[str, Any]] = []
    for index, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        event = _normalize_question_source_event(index=index, event=item, default_source=default_source)
        if event["text"]:
            events.append(event)
    return events, status


def _normalize_question_source_event(index: int, event: dict[str, Any], *, default_source: str) -> dict[str, Any]:
    time_range = event.get("time_range") if isinstance(event.get("time_range"), dict) else {}
    start_sec = _coerce_float(
        event.get("start_sec", event.get("start", event.get("start_time", time_range.get("start", event.get("timestamp", 0.0)))))
    )
    end_sec = _coerce_float(event.get("end_sec", event.get("end", event.get("end_time", time_range.get("end", start_sec)))))
    if end_sec < start_sec:
        end_sec = start_sec
    text = str(event.get("text") or event.get("question_text") or event.get("content") or event.get("utterance") or "").strip()
    question_type = _normalize_guidance_question_type(str(event.get("question_type") or event.get("type") or ""), text)
    confidence = _coerce_float(event.get("confidence", event.get("score", 0.75)))
    confidence = round(min(max(confidence, 0.0), 1.0), 2)
    question_id = str(event.get("question_id") or event.get("event_id") or event.get("id") or f"q_{index:03d}")
    return {
        "event_id": question_id,
        "question_id": question_id,
        "start_sec": round(start_sec, 2),
        "end_sec": round(end_sec, 2),
        "text": text,
        "question_type": question_type,
        "confidence": confidence,
        "source": str(event.get("source") or default_source),
    }


def _build_phase3_3_question_guidance(
    *,
    question_input: dict[str, Any],
    response_events: list[dict[str, Any]],
    attention_curve: list[float],
    activity_curve: list[float],
    student_window_results: list[dict[str, Any]],
    stage_distribution: dict[str, float],
    duration_seconds: int,
    window_size_seconds: int,
) -> dict[str, Any]:
    source_events = list(question_input.get("events") or [])
    status = str(question_input.get("status") or "unavailable")
    source = str(question_input.get("source") or "teacher_transcript_empty")
    base_events = response_events if response_events else source_events
    if not base_events:
        return {
            "teacher_question_events": [],
            "question_guidance_summary": _build_unavailable_question_guidance_summary(source=source),
        }

    guidance_events: list[dict[str, Any]] = []
    for index, event in enumerate(base_events, start=1):
        source_event = source_events[index - 1] if index - 1 < len(source_events) else {}
        start_sec = _coerce_float(event.get("start_sec", source_event.get("start_sec", 0.0)))
        end_sec = _coerce_float(event.get("end_sec", source_event.get("end_sec", start_sec)))
        if end_sec < start_sec:
            end_sec = start_sec
        text = str(event.get("text") or source_event.get("text") or "").strip()
        question_type = _normalize_guidance_question_type(str(event.get("question_type") or source_event.get("question_type") or ""), text)
        response_signal = _build_question_response_signal(
            question_start=start_sec,
            question_end=end_sec,
            attention_curve=attention_curve,
            activity_curve=activity_curve,
            response_events=response_events,
            student_window_results=student_window_results,
            duration_seconds=duration_seconds,
            window_size_seconds=window_size_seconds,
        )
        response_type = str(event.get("response_type") or "none")
        student_response_observed = bool(
            response_signal["activity_delta"] > 1.0
            or response_signal["attention_delta"] > 1.0
            or response_signal["nearby_event_count"] > 0
            or response_type in {"weak", "medium", "strong"}
        )
        question_id = str(source_event.get("question_id") or event.get("question_id") or event.get("event_id") or f"q_{index:03d}")
        guidance_events.append(
            {
                "question_id": question_id,
                "time_range": _build_time_range(start_sec, end_sec),
                "text": text,
                "question_type": question_type,
                "confidence": round(_coerce_float(source_event.get("confidence", event.get("confidence", 0.75))), 2),
                "source": source,
                "stage": _infer_question_stage(start_sec, duration_seconds, stage_distribution),
                "guidance_role": _infer_guidance_role(text, question_type),
                "student_response_observed": student_response_observed,
                "response_signal": response_signal,
            }
        )

    return {
        "teacher_question_events": guidance_events,
        "question_guidance_summary": _build_question_guidance_summary(
            events=guidance_events,
            status=status,
            source=source,
            duration_seconds=duration_seconds,
        ),
    }


def _build_question_response_signal(
    *,
    question_start: float,
    question_end: float,
    attention_curve: list[float],
    activity_curve: list[float],
    response_events: list[dict[str, Any]],
    student_window_results: list[dict[str, Any]],
    duration_seconds: int,
    window_size_seconds: int,
) -> dict[str, Any]:
    baseline_start = max(0.0, question_start - 30.0)
    baseline_end = question_start
    response_start = question_end
    response_end = min(max(float(duration_seconds), question_end + 60.0), question_end + 60.0)
    if response_end <= response_start:
        response_end = response_start + 30.0

    baseline_activity = _average_percent_over_interval(
        curve=activity_curve,
        interval_start=baseline_start,
        interval_end=baseline_end,
        window_size_seconds=window_size_seconds,
    )
    response_activity = _average_percent_over_interval(
        curve=activity_curve,
        interval_start=response_start,
        interval_end=response_end,
        window_size_seconds=window_size_seconds,
    )
    baseline_attention = _average_percent_over_interval(
        curve=attention_curve,
        interval_start=baseline_start,
        interval_end=baseline_end,
        window_size_seconds=window_size_seconds,
    )
    response_attention = _average_percent_over_interval(
        curve=attention_curve,
        interval_start=response_start,
        interval_end=response_end,
        window_size_seconds=window_size_seconds,
    )
    nearby_hand_raise_count = _count_hand_raise_in_interval(
        student_window_results=student_window_results,
        interval_start=max(0.0, question_start - 15.0),
        interval_end=response_end,
    )
    nearby_question_events = sum(
        1
        for event in response_events
        if abs(_coerce_float(event.get("start_sec", 0.0)) - question_start) <= 60.0
    )
    return {
        "activity_delta": round(response_activity - baseline_activity, 2),
        "attention_delta": round(response_attention - baseline_attention, 2),
        "nearby_event_count": int(nearby_hand_raise_count + max(nearby_question_events - 1, 0)),
    }


def _build_question_guidance_summary(
    *,
    events: list[dict[str, Any]],
    status: str,
    source: str,
    duration_seconds: int,
) -> dict[str, Any]:
    question_count = len(events)
    if question_count <= 0:
        return _build_unavailable_question_guidance_summary(source=source)

    open_count = sum(1 for event in events if event.get("question_type") == "open")
    closed_count = sum(1 for event in events if event.get("question_type") == "closed")
    check_count = sum(1 for event in events if event.get("question_type") == "check")
    effective_duration = max(float(duration_seconds), max((float(event["time_range"]["end"]) for event in events), default=0.0), 60.0)
    coverage = _compute_question_coverage(events, effective_duration)
    questions_per_10min = round(question_count / effective_duration * 600.0, 2)
    response_observed_count = sum(1 for event in events if event.get("student_response_observed") is True)
    score_parts = _compute_question_guidance_score_parts(
        question_count=question_count,
        open_count=open_count,
        coverage=coverage,
        response_observed_count=response_observed_count,
        source=source,
        duration_seconds=effective_duration,
        events=events,
    )
    guidance_score = _clamp_score(
        sum(score_parts[key] * PHASE33_GUIDANCE_SCORE_WEIGHTS[key] for key in PHASE33_GUIDANCE_SCORE_WEIGHTS)
    )
    main_issue, suggestion = _build_question_guidance_feedback(
        question_count=question_count,
        open_count=open_count,
        coverage=coverage,
        response_observed_count=response_observed_count,
    )
    return {
        "status": "demo" if status == "demo" or source == "demo_seed" else "available",
        "question_count": question_count,
        "open_question_count": open_count,
        "closed_question_count": closed_count,
        "check_question_count": check_count,
        "questions_per_10min": questions_per_10min,
        "coverage": coverage,
        "guidance_score": guidance_score,
        "main_issue": main_issue,
        "suggestion": suggestion,
        "source": source,
        "score_parts": score_parts,
    }


def _build_unavailable_question_guidance_summary(*, source: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "question_count": 0,
        "open_question_count": 0,
        "closed_question_count": 0,
        "check_question_count": 0,
        "questions_per_10min": 0.0,
        "coverage": {"early": 0, "middle": 0, "late": 0},
        "guidance_score": None,
        "main_issue": "教师提问转写不可用",
        "suggestion": "建议检查树莓派端语音识别配置或麦克风采集质量。",
        "source": source or "teacher_transcript_empty",
    }


def _compute_question_coverage(events: list[dict[str, Any]], duration_seconds: float) -> dict[str, int]:
    coverage = {"early": 0, "middle": 0, "late": 0}
    if duration_seconds <= 0:
        return coverage
    for event in events:
        start_sec = float(event.get("time_range", {}).get("start") or 0.0)
        if start_sec < duration_seconds / 3.0:
            coverage["early"] += 1
        elif start_sec < (duration_seconds * 2.0 / 3.0):
            coverage["middle"] += 1
        else:
            coverage["late"] += 1
    return coverage


def _compute_question_guidance_score_parts(
    *,
    question_count: int,
    open_count: int,
    coverage: dict[str, int],
    response_observed_count: int,
    source: str,
    duration_seconds: float,
    events: list[dict[str, Any]],
) -> dict[str, float]:
    expected_questions = max(2.0, duration_seconds / 180.0)
    question_count_score = min(question_count / expected_questions, 1.0) * 100.0
    coverage_score = (sum(1 for value in coverage.values() if value > 0) / 3.0) * 100.0
    open_ratio = open_count / question_count if question_count else 0.0
    open_question_score = min(open_ratio / 0.35, 1.0) * 100.0
    response_signal_score = (response_observed_count / question_count * 100.0) if question_count else 0.0
    source_base_score = {"teacher_questions_json": 100.0, "transcript_fallback": 80.0, "demo_seed": 60.0}.get(source, 40.0)
    avg_confidence = _mean([float(event.get("confidence") or 0.0) for event in events]) if events else 0.0
    source_confidence_score = source_base_score * max(min(avg_confidence, 1.0), 0.0)
    return {
        "question_count_score": _clamp_score(question_count_score),
        "coverage_score": _clamp_score(coverage_score),
        "open_question_score": _clamp_score(open_question_score),
        "response_signal_score": _clamp_score(response_signal_score),
        "source_confidence_score": _clamp_score(source_confidence_score),
    }


def _build_question_guidance_feedback(
    *,
    question_count: int,
    open_count: int,
    coverage: dict[str, int],
    response_observed_count: int,
) -> tuple[str, str]:
    covered_segments = sum(1 for value in coverage.values() if value > 0)
    open_ratio = open_count / question_count if question_count else 0.0
    response_ratio = response_observed_count / question_count if question_count else 0.0
    if question_count < 2:
        return "可观测提问偏少", "建议在关键知识点后增加检查性提问，形成稳定的师生互动节奏。"
    if coverage.get("late", 0) == 0:
        return "后半段提问较少", "建议在课堂后段加入总结性提问，检查学生理解。"
    if covered_segments < 2:
        return "提问时间分布不均", "建议将提问分布到导入、讲解和总结阶段，避免集中在单一时段。"
    if open_ratio < 0.25:
        return "开放性提问不足", "建议增加为什么、怎么想、能否解释等开放性问题，促进学生表达思路。"
    if response_ratio < 0.3:
        return "学生响应信号偏弱", "建议提问后延长等待时间，并通过举手、追问或同伴讨论增强反馈。"
    return "提问引导较均衡", "建议继续保持分阶段提问，并结合学生响应调整追问深度。"


def _average_percent_over_interval(
    *,
    curve: list[float],
    interval_start: float,
    interval_end: float,
    window_size_seconds: int,
) -> float:
    average = _average_curve_over_interval(
        curve=curve,
        interval_start=interval_start,
        interval_end=interval_end,
        window_size_seconds=window_size_seconds,
    )
    multiplier = 100.0 if curve and max(float(value) for value in curve) <= 1.0 else 1.0
    return round(average * multiplier, 2)


def _infer_question_stage(start_sec: float, duration_seconds: int, stage_distribution: dict[str, float]) -> str:
    if duration_seconds > 0:
        if start_sec < duration_seconds / 3.0:
            return "early"
        if start_sec < duration_seconds * 2.0 / 3.0:
            return "middle"
        return "late"
    return _dominant_stage(stage_distribution)


def _infer_guidance_role(text: str, question_type: str) -> str:
    normalized = text.strip()
    if question_type == "check" or any(keyword in normalized for keyword in ("是否正确", "对还是错", "同意", "判断")):
        return "concept_check"
    if any(keyword in normalized for keyword in ("为什么", "怎么", "说明", "想一想")):
        return "thinking_prompt"
    if any(keyword in normalized for keyword in ("总结", "回顾", "复习")):
        return "review_prompt"
    if any(keyword in normalized for keyword in ("举手", "安静", "坐好", "看这里")):
        return "classroom_management"
    if question_type == "closed":
        return "concept_check"
    return "unknown"


def _normalize_guidance_question_type(raw_type: str, text: str) -> str:
    normalized = raw_type.strip().lower()
    if normalized in {"open", "open_question", "thinking_prompt"}:
        return "open"
    if normalized in {"closed", "closed_question", "collective_response", "hand_raise_prompt", "call_response"}:
        return "closed"
    if normalized in {"check", "correctness_check", "concept_check"}:
        return "check"
    text_value = text.strip()
    if any(keyword in text_value for keyword in ("为什么", "怎么", "说明什么", "你认为")):
        return "open"
    if any(keyword in text_value for keyword in ("是否正确", "对还是错", "判断", "同意")):
        return "check"
    if any(keyword in text_value for keyword in ("是多少", "等于几", "知道吗", "举手", "吗", "么")):
        return "closed"
    return "unknown"


def _looks_like_question_text(text: str) -> bool:
    normalized = text.strip()
    question_markers = (
        "?",
        "？",
        "谁来回答",
        "为什么",
        "有没有同学知道",
        "你来说一下",
        "大家想一想",
        "大家说",
        "知道吗",
        "请举手",
        "举手",
        "是否正确",
        "对还是错",
        "是多少",
        "等于几",
        "怎么",
        "怎么来",
        "吗",
        "么",
    )
    return any(marker in normalized for marker in question_markers)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _audit_local_video_capability() -> dict[str, str]:
    local_paths = [
        REPO_ROOT / "local-processor",
        REPO_ROOT / "scripts",
    ]
    patterns = ("ffmpeg", "ffprobe", "moviepy", "VideoWriter", "transcode", "standardize")
    found = False
    for root in local_paths:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".ps1", ".sh", ".md"}:
                continue
            if path.name in {
                "classroom_feedback_pipeline.py",
                "validate_phase2_8_local_session_upload.sh",
                "upload_phase2_8_sample.sh",
            }:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(pattern in text for pattern in patterns):
                found = True
                break
        if found:
            break
    return {
        "transcode_capability": "present" if found else "absent",
        "browser_compatible": "unknown",
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _extract_path_context(package_dir: Path) -> dict[str, str]:
    parts = package_dir.resolve().parts
    if "captures_local_delivery" not in parts:
        return {}
    root_index = parts.index("captures_local_delivery")
    if len(parts) <= root_index + 3:
        return {}
    return {
        "classroom_id": parts[root_index + 1],
        "date": parts[root_index + 2],
        "session_id": parts[root_index + 3],
    }


def _build_teacher_signal_metadata(
    metadata: dict[str, Any],
    transcript_payload: Any,
    question_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if question_input and question_input.get("events") and question_input.get("source") in {"teacher_questions_json", "demo_seed"}:
        return {"teacher": {"question_events": list(question_input.get("events") or [])}}

    transcript_segments = _normalize_teacher_transcript_payload(transcript_payload)
    if transcript_segments:
        return {"teacher_transcript_segments": transcript_segments}

    metadata_segments = metadata.get("teacher_transcript_segments") or metadata.get("teacher_segments") or []
    normalized_metadata_segments = [segment for segment in metadata_segments if isinstance(segment, dict)]
    if normalized_metadata_segments:
        return {"teacher_transcript_segments": normalized_metadata_segments}

    teacher_cfg = metadata.get("teacher", {})
    if isinstance(teacher_cfg, dict) and teacher_cfg.get("question_events"):
        return {"teacher": {"question_events": list(teacher_cfg.get("question_events") or [])}}

    return {"teacher_transcript_segments": []}


def _normalize_teacher_transcript_payload(payload: Any) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [segment for segment in payload if isinstance(segment, dict)]
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("segments"), list):
        return [segment for segment in payload["segments"] if isinstance(segment, dict)]
    if isinstance(payload.get("teacher_transcript_segments"), list):
        return [segment for segment in payload["teacher_transcript_segments"] if isinstance(segment, dict)]
    return []


def _analyze_student_video_windows(
    *,
    processor: Any,
    video_path: Path | None,
    classroom_id: str,
    analysis_id: str,
    recorded_at: str,
    duration_seconds: int,
    window_size_seconds: int,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    if video_path is None or duration_seconds <= 0:
        return []

    results: list[dict[str, Any]] = []
    total_windows = max(1, math.ceil(duration_seconds / max(window_size_seconds, 1)))
    capture = cv2.VideoCapture(str(video_path))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 1.0)
    if fps <= 0:
        fps = 1.0

    temp_dir = DEFAULT_RUNTIME_FRAME_DIR / analysis_id
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        for window_index in range(total_windows):
            start_sec = window_index * window_size_seconds
            end_sec = min(duration_seconds, (window_index + 1) * window_size_seconds)
            frame_times = _sample_times_for_window(start_sec, end_sec)
            frame_paths: list[str] = []
            frame_timestamps: list[float] = []

            for sample_index, sample_time in enumerate(frame_times):
                frame_number = int(sample_time * fps)
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                frame_path = temp_dir / f"window_{window_index:03d}_{sample_index:02d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                frame_paths.append(str(frame_path))
                frame_timestamps.append(sample_time)

            if not frame_paths:
                continue

            window_metadata = {
                "classroom_id": classroom_id,
                "analysis_id": f"{analysis_id}_window_{window_index:03d}",
                "video_id": metadata.get("video_id") or (video_path.stem if video_path else analysis_id),
                "source_kind": "captured_video",
                "source_path": str(video_path),
                "source_host": metadata.get("source_host") or metadata.get("device_id") or processor.config.source_host,
                "recorded_at": recorded_at,
                "duration_seconds": max(end_sec - start_sec, 1),
                "students": metadata.get("students") or {},
            }
            window_result = processor.process_window(
                window_id=f"{analysis_id}_window_{window_index:03d}",
                frame_paths=frame_paths,
                window_timestamp=frame_times[0],
                frame_timestamps=frame_timestamps,
                metadata=window_metadata,
            )
            results.append(
                {
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "sample_frame_count": len(frame_times),
                    "valid_frame_count": len(frame_paths),
                    "hand_raise_event_count": int(window_result["students"]["hand_raise_event_count"]),
                    "zones": window_result["students"]["zones"],
                }
            )
    finally:
        capture.release()
        shutil.rmtree(temp_dir, ignore_errors=True)
    return results


def _sample_times_for_window(start_sec: int, end_sec: int) -> list[float]:
    if end_sec <= start_sec:
        return [float(start_sec)]
    sample_times = [float(start_sec)]
    midpoint = start_sec + ((end_sec - start_sec) / 2.0)
    if midpoint > start_sec:
        sample_times.append(float(midpoint))
    last_time = max(start_sec, end_sec - 1)
    if last_time not in sample_times:
        sample_times.append(float(last_time))
    return sorted(set(sample_times))


def _aggregate_zone_summary(
    student_window_results: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, dict[str, float]]:
    explicit_zones = {}
    students_cfg = metadata.get("students", {})
    if isinstance(students_cfg, dict):
        explicit_zones = students_cfg.get("zones") or {}

    zones = {}
    for zone_name in ("front", "middle", "back"):
        active_values = [
            float(item["zones"].get(zone_name, {}).get("active_ratio", 0.0))
            for item in student_window_results
        ]
        explicit_zone_cfg = explicit_zones.get(zone_name, {}) if isinstance(explicit_zones, dict) else {}
        attention_value = explicit_zone_cfg.get("avg_attention_ratio")
        if attention_value is None:
            attention_value = 0.0
        zones[zone_name] = {
            "avg_attention_ratio": round(float(attention_value), 4),
            "active_ratio": round((sum(active_values) / len(active_values)) if active_values else 0.0, 4),
        }
    return zones


def _resolve_estimated_student_count(metadata: dict[str, Any]) -> int:
    students_cfg = metadata.get("students", {})
    if isinstance(students_cfg, dict) and students_cfg.get("estimated_student_count") is not None:
        return int(students_cfg["estimated_student_count"])
    value = metadata.get("estimated_student_count")
    return int(value) if value is not None else 0


def _resolve_avg_attention_ratio(metadata: dict[str, Any], zone_summary: dict[str, dict[str, float]]) -> float:
    students_cfg = metadata.get("students", {})
    if isinstance(students_cfg, dict) and students_cfg.get("avg_attention_ratio") is not None:
        return float(students_cfg["avg_attention_ratio"])
    zone_values = [zone["avg_attention_ratio"] for zone in zone_summary.values()]
    return (sum(zone_values) / len(zone_values)) if zone_values else 0.0


def _build_attention_curve(
    metadata: dict[str, Any],
    student_window_results: list[dict[str, Any]],
    avg_attention_ratio: float,
) -> list[float]:
    timeline_cfg = metadata.get("timeline", {})
    if isinstance(timeline_cfg, dict) and timeline_cfg.get("attention_curve"):
        return [round(float(value), 4) for value in timeline_cfg["attention_curve"]]
    students_cfg = metadata.get("students", {})
    if isinstance(students_cfg, dict) and students_cfg.get("attention_windows"):
        return [round(float(value), 4) for value in students_cfg["attention_windows"]]
    window_count = max(1, len(student_window_results))
    return [round(float(avg_attention_ratio), 4)] * window_count


def _build_activity_curve(metadata: dict[str, Any], student_window_results: list[dict[str, Any]]) -> list[float]:
    timeline_cfg = metadata.get("timeline", {})
    if isinstance(timeline_cfg, dict) and timeline_cfg.get("activity_curve"):
        return [round(float(value), 4) for value in timeline_cfg["activity_curve"]]
    if not student_window_results:
        return [0.0]
    values = []
    for item in student_window_results:
        zone_values = [float(zone["active_ratio"]) for zone in item["zones"].values()]
        values.append(round((sum(zone_values) / len(zone_values)) if zone_values else 0.0, 4))
    return values or [0.0]


def _enrich_question_events_with_response(
    *,
    question_events: list[dict[str, Any]],
    activity_curve: list[float],
    heat_curve: list[float],
    student_window_results: list[dict[str, Any]],
    window_size_seconds: int,
) -> list[dict[str, Any]]:
    enriched_events: list[dict[str, Any]] = []

    for event in question_events:
        start_sec = float(event.get("start_sec") or 0.0)
        baseline_start = max(0.0, start_sec - 10.0)
        baseline_end = start_sec
        response_start = start_sec
        response_end = start_sec + 10.0

        baseline_activity = _average_curve_over_interval(
            curve=activity_curve,
            interval_start=baseline_start,
            interval_end=baseline_end,
            window_size_seconds=window_size_seconds,
        )
        response_activity = _average_curve_over_interval(
            curve=activity_curve,
            interval_start=response_start,
            interval_end=response_end,
            window_size_seconds=window_size_seconds,
        )
        baseline_heat = _average_curve_over_interval(
            curve=heat_curve,
            interval_start=baseline_start,
            interval_end=baseline_end,
            window_size_seconds=window_size_seconds,
        )
        response_heat = _average_curve_over_interval(
            curve=heat_curve,
            interval_start=response_start,
            interval_end=response_end,
            window_size_seconds=window_size_seconds,
        )

        delta_activity = round(response_activity - baseline_activity, 4)
        delta_heat = round(response_heat - baseline_heat, 4)
        response_hand_raise = _count_hand_raise_in_interval(
            student_window_results=student_window_results,
            interval_start=response_start,
            interval_end=response_end,
        )
        response_type = _classify_response_type(
            question_type=str(event.get("question_type") or "open_question"),
            hand_raise_count=response_hand_raise,
            delta_activity=delta_activity,
            delta_heat=delta_heat,
        )

        enriched_event = dict(event)
        enriched_event["response_type"] = response_type
        enriched_event["delta_activity"] = delta_activity
        enriched_event["delta_heat"] = delta_heat
        enriched_events.append(enriched_event)

    return enriched_events


def _average_curve_over_interval(
    *,
    curve: list[float],
    interval_start: float,
    interval_end: float,
    window_size_seconds: int,
) -> float:
    if not curve or interval_end <= interval_start or window_size_seconds <= 0:
        return 0.0

    weighted_sum = 0.0
    overlap_total = 0.0
    for index, value in enumerate(curve):
        window_start = index * window_size_seconds
        window_end = window_start + window_size_seconds
        overlap = max(0.0, min(interval_end, window_end) - max(interval_start, window_start))
        if overlap <= 0:
            continue
        weighted_sum += float(value) * overlap
        overlap_total += overlap

    if overlap_total <= 0:
        fallback_index = min(max(int(interval_start // max(window_size_seconds, 1)), 0), len(curve) - 1)
        return float(curve[fallback_index])
    return round(weighted_sum / overlap_total, 4)


def _count_hand_raise_in_interval(
    *,
    student_window_results: list[dict[str, Any]],
    interval_start: float,
    interval_end: float,
) -> int:
    hand_raise_count = 0
    for item in student_window_results:
        window_start = float(item.get("start_sec") or 0.0)
        window_end = float(item.get("end_sec") or window_start)
        overlap = max(0.0, min(interval_end, window_end) - max(interval_start, window_start))
        if overlap <= 0:
            continue
        hand_raise_count += int(item.get("hand_raise_event_count") or 0)
    return hand_raise_count


def _classify_response_type(
    *,
    question_type: str,
    hand_raise_count: int,
    delta_activity: float,
    delta_heat: float,
) -> str:
    normalized_type = question_type.strip().lower()

    if normalized_type == "hand_raise_prompt":
        if hand_raise_count >= 1:
            return "strong"
        if delta_activity >= 0.18:
            return "medium"
        if delta_activity >= 0.08:
            return "weak"
        return "none"

    if normalized_type in {"collective_response", "call_response"}:
        if hand_raise_count >= 1 and delta_heat >= 0.03:
            return "strong"
        if delta_heat >= 0.03:
            return "medium"
        if delta_heat >= 0.015:
            return "weak"
        return "none"

    if hand_raise_count >= 1:
        return "strong"
    if delta_activity >= 0.08 or delta_heat >= 0.03:
        return "medium"
    if delta_activity >= 0.03 or delta_heat >= 0.008:
        return "weak"
    return "none"


def _compute_response_success_rate(question_events: list[dict[str, Any]]) -> float:
    if not question_events:
        return 0.0
    successful_count = sum(1 for event in question_events if event.get("response_type") in {"strong", "medium"})
    return round(successful_count / len(question_events), 4)


def _compute_response_score(question_events: list[dict[str, Any]]) -> float:
    if not question_events:
        return 0.0
    weights = {
        "strong": 1.0,
        "medium": 0.6,
        "weak": 0.2,
        "none": 0.0,
    }
    weighted_total = sum(weights.get(str(event.get("response_type") or "none"), 0.0) for event in question_events)
    return round((weighted_total / len(question_events)) * 100, 2)


def _analyze_audio_heat_curve(
    *,
    audio_path: Path | None,
    duration_seconds: int,
    window_size_seconds: int,
    metadata: dict[str, Any],
) -> list[float]:
    timeline_cfg = metadata.get("timeline", {})
    if isinstance(timeline_cfg, dict) and timeline_cfg.get("heat_curve"):
        return [round(float(value), 4) for value in timeline_cfg["heat_curve"]]

    if audio_path is None or audio_path.suffix.lower() != ".wav" or duration_seconds <= 0:
        window_count = max(1, math.ceil(duration_seconds / max(window_size_seconds, 1))) if duration_seconds else 1
        return [0.0] * window_count

    with wave.open(str(audio_path), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        channels = wav_file.getnchannels()
        frames = wav_file.readframes(wav_file.getnframes())

    dtype = np.int16 if sample_width == 2 else np.uint8
    audio = np.frombuffer(frames, dtype=dtype)
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    audio = audio.astype(np.float32)
    max_abs = np.max(np.abs(audio)) if audio.size else 0.0
    if max_abs <= 0:
        window_count = max(1, math.ceil(duration_seconds / max(window_size_seconds, 1)))
        return [0.0] * window_count

    heat_curve: list[float] = []
    samples_per_window = max(int(frame_rate * window_size_seconds), 1)
    for start in range(0, len(audio), samples_per_window):
        window_samples = audio[start:start + samples_per_window]
        if window_samples.size == 0:
            continue
        rms = np.sqrt(np.mean(np.square(window_samples)))
        heat_curve.append(round(float(min(max(rms / max_abs, 0.0), 1.0)), 4))
    return heat_curve or [0.0]


def _normalize_curve(curve: list[float], *, target_length: int) -> list[float]:
    if not curve:
        curve = [0.0]
    if len(curve) >= target_length:
        return [round(float(value), 4) for value in curve[:target_length]]
    last_value = float(curve[-1])
    padded = [round(float(value), 4) for value in curve]
    padded.extend([round(last_value, 4)] * (target_length - len(padded)))
    return padded


def _build_summary_text(
    *,
    teacher_question_count: int,
    avg_attention_ratio: float,
    response_success_rate: float,
    activity_curve: list[float],
) -> str:
    peak_activity = max(activity_curve) if activity_curve else 0.0
    if teacher_question_count == 0:
        return "当前素材中未识别到明确提问事件，建议结合更完整转写继续复核。"
    if response_success_rate <= 0.0:
        return "检测到教师提问，但当前素材中未观察到明显学生响应。"
    if avg_attention_ratio < 0.4:
        return "课堂中段注意力信号偏弱，但提问后仍出现一定响应。"
    if peak_activity > 0.4:
        return "提问后课堂活跃度有明显提升，适合结合时间线继续查看。"
    return "课堂提问与响应链路已检测到，整体节奏较平稳。"


def _deliver_result_json(
    *,
    result_data: dict[str, Any],
    output_path: Path,
    upload_mode: str,
    pending_upload_dir: Path,
    cloud_push_enabled: bool,
    cloud_push_url: str | None,
    timeout_seconds: int,
    headers: dict[str, str],
) -> dict[str, Any]:
    if upload_mode not in {"auto", "http", "directory"}:
        raise ValueError(f"Unsupported upload_mode: {upload_mode}")

    can_http_upload = bool(cloud_push_enabled and cloud_push_url)
    if upload_mode == "http" and not can_http_upload:
        raise ValueError("Cloud upload is disabled or cloud.push_url is missing in config.")

    if upload_mode in {"auto", "http"} and can_http_upload:
        try:
            response = _attempt_http_upload(
                result_data=result_data,
                cloud_push_url=str(cloud_push_url),
                timeout_seconds=timeout_seconds,
                headers=headers,
            )
            return {
                "mode": "http",
                "status": "success",
                "target": str(cloud_push_url),
                "attempted": True,
                "http_status": response.status_code,
                "response_preview": _extract_response_preview(response),
            }
        except Exception as exc:
            LOGGER.warning("HTTP upload failed, falling back to directory delivery: %s", exc)
            http_status, response_preview = _extract_error_response(exc)
            if upload_mode == "http":
                raise
            pending_path = pending_upload_dir / output_path.name
            _write_pending_result_json(
                pending_path=pending_path,
                result_data=result_data,
                retry_count=1,
                attempted=True,
                status="pending",
                last_error=str(exc),
                last_http_status=http_status,
            )
            return {
                "mode": "directory",
                "status": "pending",
                "target": str(pending_path),
                "attempted": True,
                "http_status": http_status,
                "response_preview": response_preview,
                "fallback_reason": str(exc),
                "retry_count": 1,
                "max_retries": MAX_PENDING_UPLOAD_RETRIES,
            }

    pending_path = pending_upload_dir / output_path.name
    _write_pending_result_json(
        pending_path=pending_path,
        result_data=result_data,
        retry_count=0,
        attempted=False,
        status="pending",
        last_error=None,
        last_http_status=None,
    )
    return {
        "mode": "directory",
        "status": "pending",
        "target": str(pending_path),
        "attempted": False,
        "http_status": None,
        "fallback_reason": None if upload_mode == "directory" else "Cloud upload disabled or URL missing.",
        "retry_count": 0,
        "max_retries": MAX_PENDING_UPLOAD_RETRIES,
    }


def _attempt_http_upload(
    *,
    result_data: dict[str, Any],
    cloud_push_url: str,
    timeout_seconds: int,
    headers: dict[str, str],
) -> requests.Response:
    payload = _prepare_upload_payload(result_data, cloud_push_url)
    request_headers = dict(headers)
    if _cloud_push_requires_video_upload(cloud_push_url):
        video_path = _resolve_upload_video_path(result_data)
        if video_path is None:
            raise FileNotFoundError("Multipart cloud upload requires a local video file, but no existing video path was found.")
        upload_filename = _build_upload_video_filename(result_data, video_path)
        request_headers.pop("Content-Type", None)
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
        with video_path.open("rb") as video_stream:
            response = requests.post(
                cloud_push_url,
                files={
                    "result_json": ("result.json", payload_text.encode("utf-8"), "application/json"),
                    "video_file": (upload_filename, video_stream, "video/mp4"),
                },
                headers=request_headers,
                timeout=timeout_seconds,
            )
    else:
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
        request_headers["Content-Type"] = "application/json; charset=utf-8"
        response = requests.post(
            cloud_push_url,
            data=payload_text.encode("utf-8"),
            headers=request_headers,
            timeout=timeout_seconds,
        )
    response.raise_for_status()
    return response


def retry_pending_uploads(
    *,
    config_path: str | Path | None = None,
    pending_upload_dir: str | Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    config = load_processor_config(config_path or resolve_config_path())
    if not config.cloud_push_enabled or not config.cloud_push_url:
        raise ValueError("Cloud upload is disabled or cloud.push_url is missing in config.")

    pending_dir = Path(pending_upload_dir).resolve() if pending_upload_dir else DEFAULT_PENDING_UPLOAD_DIR
    pending_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        pending_dir.glob("*.json"),
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    if limit is not None and limit > 0:
        files = files[:limit]

    results: list[dict[str, Any]] = []
    uploaded_count = 0
    failed_count = 0
    invalid_count = 0
    max_retry_skipped_count = 0

    for json_path in files:
        try:
            result_data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            failed_count += 1
            results.append(
                {
                    "file": str(json_path),
                    "status": "read_failed",
                    "http_status": None,
                    "error": str(exc),
                }
            )
            continue

        pending_metadata = _read_pending_upload_metadata(result_data)
        retry_count = int(pending_metadata.get("retry_count") or 0)
        max_retries = int(pending_metadata.get("max_retries") or MAX_PENDING_UPLOAD_RETRIES)
        pending_status = str(pending_metadata.get("status") or "pending")

        if retry_count >= max_retries or pending_status == "max_retries_exceeded":
            max_retry_skipped_count += 1
            results.append(
                {
                    "file": str(json_path),
                    "status": "max_retries_exceeded",
                    "http_status": pending_metadata.get("last_http_status"),
                    "retry_count": retry_count,
                    "max_retries": max_retries,
                    "error": pending_metadata.get("last_error"),
                }
            )
            continue

        upload_payload = _strip_local_delivery_metadata(result_data)
        validation = validate_result_payload(upload_payload)
        if not validation["is_valid"]:
            invalid_count += 1
            results.append(
                {
                    "file": str(json_path),
                    "status": "invalid",
                    "http_status": None,
                    "validation": validation,
                }
            )
            continue

        try:
            response = _attempt_http_upload(
                result_data=result_data,
                cloud_push_url=str(config.cloud_push_url),
                timeout_seconds=config.cloud_push_timeout,
                headers=config.cloud_push_headers,
            )
            http_status = response.status_code
            response_preview = _extract_response_preview(response)
            json_path.unlink()
            uploaded_count += 1
            results.append(
                {
                    "file": str(json_path),
                    "status": "uploaded",
                    "http_status": http_status,
                    "response_preview": response_preview,
                    "retry_count": retry_count,
                    "max_retries": max_retries,
                }
            )
        except Exception as exc:
            http_status, response_preview = _extract_error_response(exc)
            next_retry_count = retry_count + 1
            next_status = "max_retries_exceeded" if next_retry_count >= max_retries else "pending"
            result_data["upload"] = _build_upload_metadata(str(config.cloud_push_url))
            _write_pending_result_json(
                pending_path=json_path,
                result_data=result_data,
                retry_count=next_retry_count,
                attempted=True,
                status=next_status,
                last_error=str(exc),
                last_http_status=http_status,
            )
            failed_count += 1
            results.append(
                {
                    "file": str(json_path),
                    "status": next_status,
                    "http_status": http_status,
                    "response_preview": response_preview,
                    "retry_count": next_retry_count,
                    "max_retries": max_retries,
                    "error": str(exc),
                }
            )

    return {
        "pending_dir": str(pending_dir),
        "target_url": str(config.cloud_push_url),
        "scanned_count": len(files),
        "uploaded_count": uploaded_count,
        "failed_count": failed_count,
        "invalid_count": invalid_count,
        "max_retry_skipped_count": max_retry_skipped_count,
        "remaining_count": len(list(pending_dir.glob("*.json"))),
        "results": results,
    }


def _extract_response_preview(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        payload = response.text[:300]
    return {
        "ok": response.ok,
        "body": payload,
    }


def _extract_error_response(exc: Exception) -> tuple[int | None, dict[str, Any] | None]:
    response = getattr(exc, "response", None)
    if response is None:
        return None, None
    return response.status_code, _extract_response_preview(response)
