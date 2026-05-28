from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REAL_SAMPLE_ROOT = REPO_ROOT.parent / "real_classroom_samples"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8011"

ANALYSIS_ID = "phase314_asr_full_classroom_sav_20200908_17"
CLASSROOM_ID = "classroom_101"
VIDEO_ID = "sav_20200908_17_full_classroom_phase314_asr"
SOURCE_DATASET = "SAV"
SOURCE_TYPE = "local_imported_video"
SAMPLE_TYPE = "external_full_classroom_video_with_asr"

SOURCE_PAYLOAD = (
    DEFAULT_REAL_SAMPLE_ROOT
    / "asr_enriched_results"
    / "phase313_asr_enriched_full_classroom_sav_20200908_17"
    / "phase313_asr_enriched_full_classroom_sav_20200908_17.json"
)
SOURCE_VIDEO = DEFAULT_REAL_SAMPLE_ROOT / "videos" / "local_imported_sav_full_classroom_20200908_17.mp4"
DEFAULT_OUTPUT_DIR = DEFAULT_REAL_SAMPLE_ROOT / "cloud_upload" / ANALYSIS_ID


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Phase 3.14 ASR-enriched full classroom sample to cloud.")
    parser.add_argument("--source-payload", type=Path, default=SOURCE_PAYLOAD)
    parser.add_argument("--source-video", type=Path, default=SOURCE_VIDEO)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_payload_path = args.source_payload.resolve()
    source_video = args.source_video.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cloud_payload_path = output_dir / f"{ANALYSIS_ID}.json"
    response_path = output_dir / "phase314_asr_full_classroom_upload_response.json"
    status_path = output_dir / "phase314_asr_full_classroom_upload_status.json"
    summary_path = output_dir / "phase314_asr_full_classroom_summary.md"

    source_payload = read_json(source_payload_path)
    video_duration = probe_duration_seconds(source_video) if source_video.exists() else None
    precheck = inspect_payload(source_payload, source_payload_path, source_video, video_duration)

    cloud_payload: dict[str, Any] = {}
    payload_created = False
    if source_payload and precheck["safe_to_upload"]:
        cloud_payload = build_cloud_payload(source_payload, source_video, video_duration)
        cloud_payload_path.write_text(json.dumps(cloud_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload_created = cloud_payload_path.exists()

    response_payload: dict[str, Any] = {}
    http_status = "dry-run" if args.dry_run else "000"
    upload_error = ""
    if payload_created and source_video.exists() and not args.dry_run:
        try:
            http_status = curl_upload(
                api_base_url=args.api_base_url.rstrip("/"),
                result_json=cloud_payload_path,
                video_file=source_video,
                response_path=response_path,
                timeout_seconds=args.timeout_seconds,
            )
            response_payload = read_json(response_path)
        except RuntimeError as exc:
            upload_error = str(exc)
    elif response_path.exists():
        response_payload = read_json(response_path)

    upload_http_ok = http_status == "200"
    upload_success = response_payload.get("success") is True
    video_url = str(response_payload.get("video_url") or "")
    cloud_video_url_present = video_url.startswith("/uploads/")

    status = {
        "analysis_id": ANALYSIS_ID,
        "api_base_url": args.api_base_url.rstrip("/"),
        "source_payload": str(source_payload_path),
        "source_video": str(source_video),
        "cloud_payload": str(cloud_payload_path),
        "upload_response": str(response_path),
        "http_status": http_status,
        "upload_success": upload_success,
        "video_url": video_url,
        "saved_path": response_payload.get("saved_path"),
        "video_path": response_payload.get("video_path"),
        "upload_error": upload_error,
        "precheck": precheck,
        "created_at": utc_now(),
    }
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(build_summary(status), encoding="utf-8")

    print_markers(
        source_payload_path=source_payload_path,
        cloud_payload_path=cloud_payload_path,
        source_video=source_video,
        payload=cloud_payload or source_payload,
        precheck=precheck,
        upload_http_ok=upload_http_ok,
        upload_success=upload_success,
        cloud_video_url_present=cloud_video_url_present,
        detail_api_ok=False,
        detail_has_transcript=False,
        detail_has_question_events=False,
        detail_has_interaction_alignment=False,
        detail_asr_quality_ok=False,
        dashboard_reachable=False,
    )
    print(f"PHASE314_RESPONSE_VIDEO_URL={video_url}")
    print(f"PHASE314_DASHBOARD_URL={args.api_base_url.rstrip()}/dashboard?result_id={ANALYSIS_ID}")
    if upload_error:
        print(f"PHASE314_UPLOAD_ERROR={upload_error}")
    return 0 if (args.dry_run or upload_success) and payload_created else 1


def build_cloud_payload(source_payload: dict[str, Any], source_video: Path, video_duration: float | None) -> dict[str, Any]:
    payload = copy.deepcopy(source_payload)
    generated_at = utc_now()
    source_time = payload.get("time") if isinstance(payload.get("time"), dict) else {}
    duration = float(video_duration or source_time.get("duration_seconds") or 2814)
    recorded_at = str(source_time.get("recorded_at") or source_time.get("generated_at") or generated_at)
    source_host = platform.node() or "local-pc-phase314"

    source = dict(payload.get("source") or {})
    source.update(
        {
            "source_kind": "local_analyzer",
            "source_host": source_host,
            "source_dataset": SOURCE_DATASET,
            "source_type": SOURCE_TYPE,
            "sample_type": SAMPLE_TYPE,
            "data_mode": SAMPLE_TYPE,
            "is_pi_capture": False,
            "is_own_capture": False,
            "is_local_processed": True,
            "is_demo_playback_sample": False,
            "is_final_dashboard_sample": True,
            "has_asr_transcript": True,
            "has_question_events": True,
            "has_visual_response_alignment": True,
        }
    )

    capture = dict(payload.get("capture") or {})
    capture.update(
        {
            "device_id": "external_sav_dataset",
            "device_name": "SAV public classroom video with local ASR enrichment",
            "classroom_id": CLASSROOM_ID,
            "video_path": str(source_video),
            "captured_at": recorded_at,
            "source_dataset": SOURCE_DATASET,
            "source_type": SOURCE_TYPE,
            "sample_type": SAMPLE_TYPE,
            "data_mode": SAMPLE_TYPE,
            "is_pi_capture": False,
            "is_own_capture": False,
            "is_local_processed": True,
            "is_demo_playback_sample": False,
            "is_final_dashboard_sample": True,
            "has_asr_transcript": True,
            "has_question_events": True,
            "has_visual_response_alignment": True,
        }
    )

    video = dict(payload.get("video") or {})
    video.pop("video_url", None)
    video.update(
        {
            "video_id": VIDEO_ID,
            "raw_video_path": str(source_video),
            "duration_seconds": round(duration, 3),
            "format": "mp4",
            "codec": "h264",
            "browser_compatible": True,
            "is_demo_playback_sample": False,
            "is_final_dashboard_sample": True,
        }
    )

    upload = dict(payload.get("upload") or {})
    upload.update(
        {
            "target": "cloud_backend",
            "api": "/api/interaction-results/with-video",
            "client_version": "phase314-asr-enriched-local-upload",
            "uploaded_at": generated_at,
            "requires_manual_video_copy": False,
        }
    )

    evidence_summary = dict(payload.get("evidence_summary") or {})
    evidence_summary.update(
        {
            "transcript_present": True,
            "question_event_source": "asr_rule_detection",
            "interaction_alignment_present": True,
        }
    )

    asr_quality = dict(payload.get("asr_quality") or {})
    asr_quality.update(
        {
            "speaker_diarization": False,
            "teacher_identity_confidence": "low_without_diarization",
            "question_event_type": "teacher_question_candidates",
        }
    )
    note = str(asr_quality.get("note") or "")
    if not note:
        asr_quality["note"] = "Question events are ASR rule-based candidates aligned with visual response windows; speaker identity is not assigned."

    payload.update(
        {
            "schema_version": "v1.1",
            "analysis_id": ANALYSIS_ID,
            "classroom_id": CLASSROOM_ID,
            "video_id": VIDEO_ID,
            "source": source,
            "time": {
                "recorded_at": recorded_at,
                "generated_at": generated_at,
                "duration_seconds": round(duration, 3),
            },
            "video": video,
            "capture": capture,
            "upload": upload,
            "evidence_summary": evidence_summary,
            "asr_quality": asr_quality,
            "source_dataset": SOURCE_DATASET,
            "source_type": SOURCE_TYPE,
            "sample_type": SAMPLE_TYPE,
            "data_mode": SAMPLE_TYPE,
            "is_pi_capture": False,
            "is_own_capture": False,
            "is_local_processed": True,
            "is_demo_playback_sample": False,
            "is_final_dashboard_sample": True,
            "has_asr_transcript": True,
            "has_question_events": True,
            "has_visual_response_alignment": True,
            "phase314_asr_final_dashboard_sample": {
                "final_dashboard_sample": True,
                "asr_enriched": True,
                "same_source_full_video_and_json": True,
                "not_pi_capture": True,
                "not_own_capture": True,
                "not_demo_clip": True,
                "question_events_are_candidates": True,
                "speaker_diarization": False,
                "notes": [
                    "SAV is an external public classroom video dataset.",
                    "Question events are ASR rule-based candidates and visual-response-aligned.",
                    "Cloud video_url is intentionally not prefilled; the cloud with-video endpoint injects it.",
                ],
            },
        }
    )
    return payload


def inspect_payload(
    payload: dict[str, Any],
    source_payload_path: Path,
    source_video: Path,
    video_duration: float | None,
) -> dict[str, Any]:
    transcript = payload.get("transcript") if isinstance(payload.get("transcript"), list) else []
    teacher = payload.get("teacher") if isinstance(payload.get("teacher"), dict) else {}
    question_events = teacher.get("question_events") if isinstance(teacher.get("question_events"), list) else []
    alignments = payload.get("interaction_alignment") if isinstance(payload.get("interaction_alignment"), list) else []
    response_detected_count = sum(1 for item in alignments if isinstance(item, dict) and item.get("response_detected"))
    asr_quality = payload.get("asr_quality") if isinstance(payload.get("asr_quality"), dict) else {}
    duration = float(video_duration or ((payload.get("time") or {}).get("duration_seconds") or 0))
    payload_text = json.dumps(payload, ensure_ascii=False)
    no_overclaim = not any(
        term in payload_text
        for term in [
            "teacher_identity_confidence\": \"high",
            "speaker_diarization\": true",
            "精准识别教师身份",
            "自动教师身份识别",
        ]
    )
    precheck = {
        "source_payload_present": source_payload_path.exists(),
        "source_video_present": source_video.exists(),
        "transcript_present": bool(transcript),
        "transcript_segment_count": len(transcript),
        "question_events_present": bool(question_events),
        "question_event_count": len(question_events),
        "interaction_alignment_present": bool(alignments),
        "alignment_count": len(alignments),
        "response_detected_count": response_detected_count,
        "asr_quality_ok": asr_quality.get("speaker_diarization") is False,
        "no_teacher_identity_overclaim": no_overclaim,
        "video_duration_not_60": duration > 600,
        "safe_to_upload": False,
    }
    precheck["safe_to_upload"] = all(
        [
            precheck["source_payload_present"],
            precheck["source_video_present"],
            precheck["transcript_present"],
            precheck["question_events_present"],
            precheck["interaction_alignment_present"],
            precheck["asr_quality_ok"],
            precheck["no_teacher_identity_overclaim"],
            precheck["video_duration_not_60"],
        ]
    )
    return precheck


def curl_upload(
    *,
    api_base_url: str,
    result_json: Path,
    video_file: Path,
    response_path: Path,
    timeout_seconds: int,
) -> str:
    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("curl_not_available")
    command = [
        curl,
        "-sS",
        "--noproxy",
        "*",
        "-o",
        str(response_path),
        "-w",
        "%{http_code}",
        "-X",
        "POST",
    ]
    api_key = os.environ.get("CLOUD_API_KEY", "")
    if api_key:
        command.extend(["-H", f"X-API-Key: {api_key}"])
    command.extend(
        [
            "-F",
            f"result_json=@{result_json};type=application/json",
            "-F",
            f"video_file=@{video_file};type=video/mp4;filename={ANALYSIS_ID}.mp4",
            f"{api_base_url}/api/interaction-results/with-video",
        ]
    )
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
    if result.returncode != 0:
        message = " ".join((result.stderr or result.stdout or "curl_failed").split())[:500]
        raise RuntimeError(message)
    return result.stdout.strip()


def build_summary(status: dict[str, Any]) -> str:
    precheck = status.get("precheck") or {}
    return f"""# Phase 3.14 ASR Cloud Dashboard Sample Summary

## Upload

- analysis_id: {ANALYSIS_ID}
- source_payload: `{status.get('source_payload')}`
- cloud_payload: `{status.get('cloud_payload')}`
- source_video: `{status.get('source_video')}`
- http_status: {status.get('http_status')}
- upload_success: {status.get('upload_success')}
- video_url: {status.get('video_url') or ''}

## ASR Enrichment

- transcript_segment_count: {precheck.get('transcript_segment_count', 0)}
- question_event_count: {precheck.get('question_event_count', 0)}
- alignment_count: {precheck.get('alignment_count', 0)}
- response_detected_count: {precheck.get('response_detected_count', 0)}

## Boundary

- This sample is SAV external public classroom video, not Raspberry Pi capture and not own capture.
- Question events are ASR rule-based teacher question candidates with visual response alignment.
- No speaker diarization claim is made.
- No core visual algorithm or cloud code is modified in Phase 3.14.
"""


def print_markers(
    *,
    source_payload_path: Path,
    cloud_payload_path: Path,
    source_video: Path,
    payload: dict[str, Any],
    precheck: dict[str, Any],
    upload_http_ok: bool,
    upload_success: bool,
    cloud_video_url_present: bool,
    detail_api_ok: bool,
    detail_has_transcript: bool,
    detail_has_question_events: bool,
    detail_has_interaction_alignment: bool,
    detail_asr_quality_ok: bool,
    dashboard_reachable: bool,
) -> None:
    duration_not_60 = bool(precheck.get("video_duration_not_60"))
    no_sav_as_pi = no_sav_as_pi_capture(payload)
    no_sav_as_own = no_sav_as_own_capture(payload)
    ready = all(
        [
            source_payload_path.exists(),
            cloud_payload_path.exists(),
            source_video.exists(),
            precheck.get("transcript_present"),
            precheck.get("question_events_present"),
            precheck.get("interaction_alignment_present"),
            precheck.get("asr_quality_ok"),
            upload_http_ok,
            upload_success,
            cloud_video_url_present,
            detail_api_ok,
            detail_has_transcript,
            detail_has_question_events,
            detail_has_interaction_alignment,
            detail_asr_quality_ok,
            dashboard_reachable,
            duration_not_60,
            no_sav_as_pi,
            no_sav_as_own,
        ]
    )
    print(f"PHASE314_ASR_ENRICHED_SOURCE_PAYLOAD_PRESENT={bool_text(source_payload_path.exists())}")
    print(f"PHASE314_CLOUD_PAYLOAD_CREATED={bool_text(cloud_payload_path.exists())}")
    print(f"PHASE314_FULL_CLASSROOM_VIDEO_PRESENT={bool_text(source_video.exists())}")
    print(f"PHASE314_TRANSCRIPT_PRESENT={bool_text(bool(precheck.get('transcript_present')))}")
    print(f"PHASE314_TRANSCRIPT_SEGMENT_COUNT={int(precheck.get('transcript_segment_count') or 0)}")
    print(f"PHASE314_QUESTION_EVENTS_PRESENT={bool_text(bool(precheck.get('question_events_present')))}")
    print(f"PHASE314_QUESTION_EVENT_COUNT={int(precheck.get('question_event_count') or 0)}")
    print(f"PHASE314_INTERACTION_ALIGNMENT_PRESENT={bool_text(bool(precheck.get('interaction_alignment_present')))}")
    print(f"PHASE314_ALIGNMENT_COUNT={int(precheck.get('alignment_count') or 0)}")
    print(f"PHASE314_RESPONSE_DETECTED_COUNT={int(precheck.get('response_detected_count') or 0)}")
    print(f"PHASE314_NO_SPEAKER_DIARIZATION_CLAIM={bool_text(bool(precheck.get('asr_quality_ok')))}")
    print(f"PHASE314_NO_TEACHER_IDENTITY_OVERCLAIM={bool_text(bool(precheck.get('no_teacher_identity_overclaim')))}")
    print(f"PHASE314_MULTIPART_UPLOAD_HTTP_OK={bool_text(upload_http_ok)}")
    print(f"PHASE314_MULTIPART_UPLOAD_SUCCESS={bool_text(upload_success)}")
    print(f"PHASE314_CLOUD_VIDEO_URL_PRESENT={bool_text(cloud_video_url_present)}")
    print(f"PHASE314_DETAIL_API_OK={bool_text(detail_api_ok)}")
    print(f"PHASE314_DETAIL_HAS_TRANSCRIPT={bool_text(detail_has_transcript)}")
    print(f"PHASE314_DETAIL_HAS_QUESTION_EVENTS={bool_text(detail_has_question_events)}")
    print(f"PHASE314_DETAIL_HAS_INTERACTION_ALIGNMENT={bool_text(detail_has_interaction_alignment)}")
    print(f"PHASE314_DETAIL_ASR_QUALITY_OK={bool_text(detail_asr_quality_ok)}")
    print(f"PHASE314_DASHBOARD_REACHABLE={bool_text(dashboard_reachable)}")
    print(f"PHASE314_VIDEO_DURATION_NOT_60S={bool_text(duration_not_60)}")
    print(f"PHASE314_NO_SAV_AS_PI_CAPTURE={bool_text(no_sav_as_pi)}")
    print(f"PHASE314_NO_SAV_AS_OWN_CAPTURE={bool_text(no_sav_as_own)}")
    print(f"PHASE314_ASR_FINAL_DASHBOARD_SAMPLE_READY={bool_text(ready)}")


def no_sav_as_pi_capture(payload: dict[str, Any]) -> bool:
    capture = payload.get("capture") if isinstance(payload.get("capture"), dict) else {}
    # Cloud detail preserves root and capture flags, while nested source extra fields may be schema-trimmed.
    return (
        payload.get("source_dataset") == SOURCE_DATASET
        and capture.get("source_dataset") == SOURCE_DATASET
        and payload.get("is_pi_capture") is False
        and capture.get("is_pi_capture") is False
    )


def no_sav_as_own_capture(payload: dict[str, Any]) -> bool:
    capture = payload.get("capture") if isinstance(payload.get("capture"), dict) else {}
    return payload.get("is_own_capture") is False and capture.get("is_own_capture") is False


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def probe_duration_seconds(video_path: Path) -> float | None:
    if not video_path.exists() or shutil.which("ffprobe") is None:
        return None
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
