from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REAL_SAMPLE_ROOT = REPO_ROOT.parent / "real_classroom_samples"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8011"
ANALYSIS_ID = "phase314_asr_full_classroom_sav_20200908_17"
SOURCE_DATASET = "SAV"
DEFAULT_OUTPUT_DIR = DEFAULT_REAL_SAMPLE_ROOT / "cloud_upload" / ANALYSIS_ID
SOURCE_PAYLOAD = (
    DEFAULT_REAL_SAMPLE_ROOT
    / "asr_enriched_results"
    / "phase313_asr_enriched_full_classroom_sav_20200908_17"
    / "phase313_asr_enriched_full_classroom_sav_20200908_17.json"
)
SOURCE_VIDEO = DEFAULT_REAL_SAMPLE_ROOT / "videos" / "local_imported_sav_full_classroom_20200908_17.mp4"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.14 ASR-enriched cloud dashboard sample.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--source-payload", type=Path, default=SOURCE_PAYLOAD)
    parser.add_argument("--source-video", type=Path, default=SOURCE_VIDEO)
    parser.add_argument("--teacher-username", default=os.environ.get("TEACHER_USERNAME", "teacher"))
    parser.add_argument("--teacher-password", default=os.environ.get("TEACHER_PASSWORD", ""))
    args = parser.parse_args()

    api_base_url = args.api_base_url.rstrip("/")
    output_dir = args.output_dir.resolve()
    source_payload_path = args.source_payload.resolve()
    source_video = args.source_video.resolve()
    cloud_payload_path = output_dir / f"{ANALYSIS_ID}.json"
    response_path = output_dir / "phase314_asr_full_classroom_upload_response.json"
    status_path = output_dir / "phase314_asr_full_classroom_upload_status.json"
    validation_path = output_dir / "phase314_asr_full_classroom_cloud_validation.json"

    local_payload = read_json(cloud_payload_path) or read_json(source_payload_path)
    status = read_json(status_path)
    response_payload = read_json(response_path)
    precheck = status.get("precheck") if isinstance(status.get("precheck"), dict) else inspect_payload(local_payload, source_video)

    upload_http_ok = str(status.get("http_status") or "") == "200"
    upload_success = response_payload.get("success") is True
    video_url = str(response_payload.get("video_url") or status.get("video_url") or "")
    cloud_video_url_present = video_url.startswith("/uploads/")

    tmp_dir = output_dir / "_phase314_validation_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    teacher_cookie = tmp_dir / "teacher.cookie"
    login_out = tmp_dir / "teacher-login.json"
    detail_out = tmp_dir / "detail.json"
    dashboard_out = tmp_dir / "dashboard.html"
    static_out = tmp_dir / "static-video.bin"

    login_status = curl(
        [
            "-o",
            str(login_out),
            "-w",
            "%{http_code}",
            "-c",
            str(teacher_cookie),
            "-H",
            "Content-Type: application/json",
            "--data",
            json.dumps({"username": args.teacher_username, "password": args.teacher_password}),
            f"{api_base_url}/api/auth/login",
        ],
        timeout=120,
    )
    teacher_login_ok = login_status == "200" and read_json(login_out).get("success") is True

    detail_status = "000"
    dashboard_status = "000"
    static_status = "000"
    if teacher_login_ok:
        detail_status = curl(
            [
                "-o",
                str(detail_out),
                "-w",
                "%{http_code}",
                "-b",
                str(teacher_cookie),
                f"{api_base_url}/api/teacher/results/{ANALYSIS_ID}",
            ],
            timeout=180,
        )
        dashboard_status = curl(
            [
                "-o",
                str(dashboard_out),
                "-w",
                "%{http_code}",
                "-b",
                str(teacher_cookie),
                f"{api_base_url}/dashboard?result_id={ANALYSIS_ID}",
            ],
            timeout=180,
        )
    if cloud_video_url_present:
        static_status = curl(
            ["-r", "0-0", "-o", str(static_out), "-w", "%{http_code}", f"{api_base_url}{video_url}"],
            timeout=180,
        )

    detail_payload = read_json(detail_out)
    result = detail_payload.get("result") if isinstance(detail_payload.get("result"), dict) else {}
    raw_payload = detail_raw_payload(result)
    detail_source = raw_payload or result

    detail_api_ok = detail_status == "200" and detail_payload.get("success") is True
    detail_has_transcript = has_list(detail_source, "transcript") or has_list(raw_payload, "transcript")
    detail_has_question_events = bool(
        ((detail_source.get("teacher") or {}) if isinstance(detail_source.get("teacher"), dict) else {}).get("question_events")
    )
    detail_has_interaction_alignment = has_list(detail_source, "interaction_alignment")
    detail_asr_quality = detail_source.get("asr_quality") if isinstance(detail_source.get("asr_quality"), dict) else {}
    detail_asr_quality_ok = detail_asr_quality.get("speaker_diarization") is False
    evidence = detail_source.get("evidence_summary") if isinstance(detail_source.get("evidence_summary"), dict) else {}
    detail_evidence_transcript = evidence.get("transcript_present") is True
    dashboard_reachable = dashboard_status == "200"
    duration_not_60 = any(
        value > 600
        for value in [
            as_float((detail_source.get("time") or {}).get("duration_seconds") if isinstance(detail_source.get("time"), dict) else None),
            as_float((detail_source.get("video") or {}).get("duration_seconds") if isinstance(detail_source.get("video"), dict) else None),
            as_float((local_payload.get("time") or {}).get("duration_seconds") if isinstance(local_payload.get("time"), dict) else None),
        ]
    )
    no_sav_as_pi = no_sav_as_pi_capture(detail_source or local_payload)
    no_sav_as_own = no_sav_as_own_capture(detail_source or local_payload)
    final_flag_ok = (detail_source or local_payload).get("is_final_dashboard_sample") is True
    static_video_ok = static_status in {"200", "206"}

    validation = {
        "analysis_id": ANALYSIS_ID,
        "api_base_url": api_base_url,
        "video_url": video_url,
        "teacher_login_ok": teacher_login_ok,
        "detail_status": detail_status,
        "dashboard_status": dashboard_status,
        "static_status": static_status,
        "detail_api_ok": detail_api_ok,
        "detail_has_transcript": detail_has_transcript,
        "detail_has_question_events": detail_has_question_events,
        "detail_has_interaction_alignment": detail_has_interaction_alignment,
        "detail_evidence_transcript": detail_evidence_transcript,
        "detail_asr_quality_ok": detail_asr_quality_ok,
        "dashboard_reachable": dashboard_reachable,
        "static_video_ok": static_video_ok,
        "duration_not_60": duration_not_60,
        "no_sav_as_pi": no_sav_as_pi,
        "no_sav_as_own": no_sav_as_own,
        "final_flag_ok": final_flag_ok,
        "precheck": precheck,
    }
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

    print_markers(
        source_payload_path=source_payload_path,
        cloud_payload_path=cloud_payload_path,
        source_video=source_video,
        payload=local_payload,
        precheck=precheck,
        upload_http_ok=upload_http_ok,
        upload_success=upload_success,
        cloud_video_url_present=cloud_video_url_present,
        detail_api_ok=detail_api_ok,
        detail_has_transcript=detail_has_transcript,
        detail_has_question_events=detail_has_question_events,
        detail_has_interaction_alignment=detail_has_interaction_alignment,
        detail_asr_quality_ok=detail_asr_quality_ok and detail_evidence_transcript,
        dashboard_reachable=dashboard_reachable,
        duration_not_60=duration_not_60,
        no_sav_as_pi=no_sav_as_pi,
        no_sav_as_own=no_sav_as_own,
    )
    print(f"PHASE314_RESPONSE_VIDEO_URL={video_url}")
    print(f"PHASE314_DASHBOARD_URL={api_base_url}/dashboard?result_id={ANALYSIS_ID}")
    return 0 if validation_ready(validation, precheck, upload_http_ok, upload_success, cloud_video_url_present) else 1


def validation_ready(validation: dict[str, Any], precheck: dict[str, Any], upload_http_ok: bool, upload_success: bool, video_url_present: bool) -> bool:
    return all(
        [
            precheck.get("transcript_present"),
            precheck.get("question_events_present"),
            precheck.get("interaction_alignment_present"),
            precheck.get("asr_quality_ok"),
            precheck.get("no_teacher_identity_overclaim"),
            upload_http_ok,
            upload_success,
            video_url_present,
            validation.get("detail_api_ok"),
            validation.get("detail_has_transcript"),
            validation.get("detail_has_question_events"),
            validation.get("detail_has_interaction_alignment"),
            validation.get("detail_evidence_transcript"),
            validation.get("detail_asr_quality_ok"),
            validation.get("dashboard_reachable"),
            validation.get("duration_not_60"),
            validation.get("no_sav_as_pi"),
            validation.get("no_sav_as_own"),
            validation.get("final_flag_ok"),
        ]
    )


def inspect_payload(payload: dict[str, Any], source_video: Path) -> dict[str, Any]:
    transcript = payload.get("transcript") if isinstance(payload.get("transcript"), list) else []
    teacher = payload.get("teacher") if isinstance(payload.get("teacher"), dict) else {}
    question_events = teacher.get("question_events") if isinstance(teacher.get("question_events"), list) else []
    alignments = payload.get("interaction_alignment") if isinstance(payload.get("interaction_alignment"), list) else []
    response_detected_count = sum(1 for item in alignments if isinstance(item, dict) and item.get("response_detected"))
    asr_quality = payload.get("asr_quality") if isinstance(payload.get("asr_quality"), dict) else {}
    payload_text = json.dumps(payload, ensure_ascii=False)
    duration = as_float((payload.get("time") or {}).get("duration_seconds") if isinstance(payload.get("time"), dict) else None)
    return {
        "source_video_present": source_video.exists(),
        "transcript_present": bool(transcript),
        "transcript_segment_count": len(transcript),
        "question_events_present": bool(question_events),
        "question_event_count": len(question_events),
        "interaction_alignment_present": bool(alignments),
        "alignment_count": len(alignments),
        "response_detected_count": response_detected_count,
        "asr_quality_ok": asr_quality.get("speaker_diarization") is False,
        "no_teacher_identity_overclaim": not any(
            term in payload_text
            for term in ["teacher_identity_confidence\": \"high", "speaker_diarization\": true", "精准识别教师身份", "自动教师身份识别"]
        ),
        "video_duration_not_60": duration > 600,
    }


def curl(args: list[str], timeout: int) -> str:
    curl_path = shutil.which("curl")
    if not curl_path:
        return "000"
    command = [curl_path, "-sS", "--noproxy", "*", "--max-time", str(timeout), *args]
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 10)
    if result.returncode != 0:
        return "000"
    return result.stdout.strip()


def detail_raw_payload(result: dict[str, Any]) -> dict[str, Any]:
    for key in ("raw_payload", "result", "payload_json"):
        value = result.get(key)
        if isinstance(value, dict):
            return value
    return {}


def has_list(payload: dict[str, Any], key: str) -> bool:
    return isinstance(payload.get(key), list) and len(payload.get(key)) > 0


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
    duration_not_60: bool,
    no_sav_as_pi: bool,
    no_sav_as_own: bool,
) -> None:
    ready = all(
        [
            source_payload_path.exists(),
            cloud_payload_path.exists(),
            source_video.exists(),
            precheck.get("transcript_present"),
            precheck.get("question_events_present"),
            precheck.get("interaction_alignment_present"),
            precheck.get("asr_quality_ok"),
            precheck.get("no_teacher_identity_overclaim"),
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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
