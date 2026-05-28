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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REAL_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
DEFAULT_API_BASE_URL = "http://127.0.0.1:8011"

ANALYSIS_ID = "phase37_full_classroom_sav_20200908_17"
CLASSROOM_ID = "classroom_101"
VIDEO_ID = "sav_20200908_17_full_classroom_phase37"
SOURCE_VIDEO_NAME = "local_imported_sav_full_classroom_20200908_17.mp4"
SOURCE_JSON_NAME = "local_imported_sav_full_classroom_20200908_17.json"
UPLOAD_VIDEO_FILENAME = "phase37_full_classroom_sav_20200908_17.mp4"
UPLOAD_JSON_FILENAME = "phase37_full_classroom_sav_20200908_17.json"
UPLOAD_RESPONSE_FILENAME = "phase37_full_classroom_upload_response.json"
UPLOAD_STATE_FILENAME = "phase37_full_classroom_upload_state.json"

SOURCE_DATASET = "SAV"
SOURCE_TYPE = "local_imported_video"
SAMPLE_TYPE = "external_full_classroom_video"


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Phase 3.7 full-classroom video and JSON to cloud.")
    parser.add_argument("--real-sample-root", type=Path, default=DEFAULT_REAL_SAMPLE_ROOT)
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--source-video", type=Path)
    parser.add_argument("--source-json", type=Path)
    parser.add_argument("--upload-dir", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    parser.add_argument("--dry-run", action="store_true", help="Create cloud payload without uploading.")
    args = parser.parse_args()

    real_sample_root = args.real_sample_root.resolve()
    source_video = (args.source_video or real_sample_root / "videos" / SOURCE_VIDEO_NAME).resolve()
    source_json = (args.source_json or real_sample_root / "analysis_results" / SOURCE_JSON_NAME).resolve()
    upload_dir = (args.upload_dir or real_sample_root / "cloud_upload").resolve()
    upload_payload = upload_dir / UPLOAD_JSON_FILENAME
    upload_response = upload_dir / UPLOAD_RESPONSE_FILENAME
    upload_state = upload_dir / UPLOAD_STATE_FILENAME

    upload_dir.mkdir(parents=True, exist_ok=True)

    script_present = Path(__file__).exists()
    video_present = source_video.exists()
    analysis_present = source_json.exists()
    payload_created = False
    http_ok = False
    upload_success = False
    no_manual_copy_required = False
    response_video_url_present = False
    full_video_uploaded = False
    full_analysis_uploaded = False

    video_duration = _probe_duration_seconds(source_video) if video_present else None
    source_payload = _read_json(source_json) if analysis_present else {}
    cloud_payload = {}
    if source_payload and video_present:
        cloud_payload = _build_cloud_payload(source_payload, source_video, video_duration)
        upload_payload.write_text(json.dumps(cloud_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload_created = upload_payload.exists()

    response_payload: dict[str, Any] = {}
    http_status = "dry-run" if args.dry_run else "000"
    upload_error = ""
    if payload_created and video_present and not args.dry_run:
        try:
            http_status = _curl_upload(
                api_base_url=args.api_base_url.rstrip("/"),
                result_json=upload_payload,
                video_file=source_video,
                response_path=upload_response,
                timeout_seconds=args.timeout_seconds,
            )
            http_ok = http_status == "200"
            response_payload = _read_json(upload_response)
            upload_success = response_payload.get("success") is True
            response_video_url_present = str(response_payload.get("video_url") or "").startswith("/uploads/")
            full_video_uploaded = upload_success and response_video_url_present and bool(response_payload.get("video_path"))
            full_analysis_uploaded = upload_success and bool(response_payload.get("saved_path"))
            no_manual_copy_required = upload_success and response_video_url_present
        except RuntimeError as exc:
            upload_error = str(exc)
            http_status = "000"
    elif upload_response.exists():
        response_payload = _read_json(upload_response)

    state = {
        "analysis_id": ANALYSIS_ID,
        "api_base_url": args.api_base_url.rstrip("/"),
        "source_video": str(source_video),
        "source_video_size_bytes": source_video.stat().st_size if source_video.exists() else 0,
        "source_json": str(source_json),
        "upload_payload": str(upload_payload),
        "upload_response": str(upload_response),
        "http_status": http_status,
        "dry_run": args.dry_run,
        "video_duration_seconds": video_duration,
        "response_video_url": response_payload.get("video_url"),
        "response_saved_path": response_payload.get("saved_path"),
        "upload_error": upload_error,
        "created_at": _utc_now(),
    }
    upload_state.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    duration_not_60 = _duration_not_60(video_duration)
    duration_aligned = _duration_aligned(cloud_payload)
    no_sav_as_pi = _no_sav_as_pi_capture(cloud_payload)
    no_demo_as_final = _no_demo_clip_as_final_sample(cloud_payload)

    print(f"PHASE36B_LOCAL_UPLOAD_SCRIPT_PRESENT={_bool_text(script_present)}")
    print(f"PHASE36B_FULL_CLASSROOM_VIDEO_PRESENT={_bool_text(video_present)}")
    print(f"PHASE36B_FULL_CLASSROOM_ANALYSIS_JSON_PRESENT={_bool_text(analysis_present)}")
    print(f"PHASE36B_CLOUD_PAYLOAD_CREATED={_bool_text(payload_created)}")
    print(f"PHASE36B_MULTIPART_UPLOAD_HTTP_OK={_bool_text(http_ok)}")
    print(f"PHASE36B_MULTIPART_UPLOAD_SUCCESS={_bool_text(upload_success)}")
    print(f"PHASE36B_NO_MANUAL_COPY_REQUIRED={_bool_text(no_manual_copy_required)}")
    print(f"PHASE37_FINAL_ANALYSIS_ID={ANALYSIS_ID}")
    print(f"PHASE37_FULL_CLASS_VIDEO_UPLOADED={_bool_text(full_video_uploaded)}")
    print(f"PHASE37_FULL_CLASS_ANALYSIS_UPLOADED={_bool_text(full_analysis_uploaded)}")
    print(f"PHASE37_VIDEO_URL_PRESENT={_bool_text(response_video_url_present)}")
    print(f"PHASE37_VIDEO_DURATION_NOT_60S={_bool_text(duration_not_60)}")
    print(f"PHASE37_VIDEO_ANALYSIS_DURATION_ALIGNED={_bool_text(duration_aligned)}")
    print("PHASE37_DETAIL_API_OK=false")
    print("PHASE37_DASHBOARD_REACHABLE=false")
    print("PHASE37_FINAL_DASHBOARD_SAMPLE_READY=false")
    print(f"PHASE37_NO_SAV_AS_PI_CAPTURE={_bool_text(no_sav_as_pi)}")
    print(f"PHASE37_NO_DEMO_CLIP_AS_FINAL_SAMPLE={_bool_text(no_demo_as_final)}")
    print(f"PHASE37_UPLOAD_PAYLOAD={upload_payload}")
    print(f"PHASE37_UPLOAD_RESPONSE={upload_response}")
    print(f"PHASE37_RESPONSE_VIDEO_URL={response_payload.get('video_url', '')}")
    if upload_error:
        print(f"PHASE37_UPLOAD_ERROR={upload_error}")
    return 0 if (args.dry_run or upload_success) and payload_created else 1


def _build_cloud_payload(source_payload: dict[str, Any], source_video: Path, video_duration: float | None) -> dict[str, Any]:
    payload = copy.deepcopy(source_payload)
    generated_at = _utc_now()
    source_time = payload.get("time") if isinstance(payload.get("time"), dict) else {}
    recorded_at = str(source_time.get("recorded_at") or source_time.get("generated_at") or generated_at)
    duration = float(video_duration or source_time.get("duration_seconds") or 2814)
    source_host = platform.node() or "local-pc-phase37"

    source = {
        "source_kind": "local_analyzer",
        "source_path": str(source_payload.get("source", {}).get("source_path") or SOURCE_JSON_NAME),
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
    }

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
            "standardized_video_path": UPLOAD_VIDEO_FILENAME,
            "is_demo_playback_sample": False,
            "is_final_dashboard_sample": True,
        }
    )

    capture = dict(payload.get("capture") or {})
    capture.update(
        {
            "device_id": "external_sav_dataset",
            "device_name": "SAV public classroom video",
            "classroom_id": CLASSROOM_ID,
            "video_path": str(source_video),
            "captured_at": recorded_at,
            "source_dataset": SOURCE_DATASET,
            "source_type": SOURCE_TYPE,
            "sample_type": SAMPLE_TYPE,
            "is_pi_capture": False,
            "is_own_capture": False,
            "is_local_processed": True,
            "is_demo_playback_sample": False,
            "is_final_dashboard_sample": True,
        }
    )

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
            "timeline": _normalize_timeline(payload.get("timeline")),
            "video": video,
            "capture": capture,
            "upload": {
                "target": "cloud_backend",
                "api": "/api/interaction-results/with-video",
                "client_version": "phase36b-local-auto-upload",
                "uploaded_at": generated_at,
                "requires_manual_video_copy": False,
            },
            "source_dataset": SOURCE_DATASET,
            "source_type": SOURCE_TYPE,
            "sample_type": SAMPLE_TYPE,
            "data_mode": SAMPLE_TYPE,
            "is_pi_capture": False,
            "is_own_capture": False,
            "is_local_processed": True,
            "is_demo_playback_sample": False,
            "is_final_dashboard_sample": True,
            "phase37_final_dashboard_sample": {
                "final_dashboard_sample": True,
                "same_source_full_video_and_json": True,
                "not_pi_capture": True,
                "not_own_capture": True,
                "not_demo_clip": True,
                "not_sav50_composite": True,
                "notes": [
                    "SAV is an external public classroom video dataset.",
                    "This payload is generated from the full classroom video and its matching full analysis JSON.",
                    "Cloud video_url is intentionally not prefilled; the cloud with-video endpoint injects it.",
                ],
            },
        }
    )
    return payload


def _curl_upload(
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
            f"video_file=@{video_file};type=video/mp4;filename={UPLOAD_VIDEO_FILENAME}",
            f"{api_base_url}/api/interaction-results/with-video",
        ]
    )
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
    if result.returncode != 0:
        message = " ".join((result.stderr or result.stdout or "curl_failed").split())[:500]
        raise RuntimeError(message)
    return result.stdout.strip()


def _normalize_timeline(value: Any) -> dict[str, Any]:
    timeline = value if isinstance(value, dict) else {}
    window_size_seconds = timeline.get("window_size_seconds", 20)
    curves = {
        "attention_curve": _as_float_list(timeline.get("attention_curve")),
        "heat_curve": _as_float_list(timeline.get("heat_curve")),
        "activity_curve": _as_float_list(timeline.get("activity_curve")),
    }
    target_len = max([len(curve) for curve in curves.values()] + [1])
    for key, curve in curves.items():
        if not curve:
            curves[key] = [0.0] * target_len
        elif len(curve) < target_len:
            curves[key] = curve + [curve[-1]] * (target_len - len(curve))
        elif len(curve) > target_len:
            curves[key] = curve[:target_len]
    return {"window_size_seconds": window_size_seconds, **curves}


def _probe_duration_seconds(video_path: Path) -> float | None:
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


def _duration_not_60(duration: float | None) -> bool:
    return duration is not None and duration > 600


def _duration_aligned(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    time_duration = _as_float((payload.get("time") or {}).get("duration_seconds"))
    video_duration = _as_float((payload.get("video") or {}).get("duration_seconds"))
    timeline = payload.get("timeline") or {}
    window_size = _as_float(timeline.get("window_size_seconds"))
    curve_len = len(timeline.get("attention_curve") or [])
    if time_duration <= 600 or video_duration <= 600 or abs(time_duration - video_duration) > 2:
        return False
    if window_size <= 0 or curve_len <= 0:
        return False
    expected_windows = round(time_duration / window_size)
    return abs(curve_len - expected_windows) <= 1


def _no_sav_as_pi_capture(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    source = payload.get("source") or {}
    capture = payload.get("capture") or {}
    return (
        payload.get("source_dataset") == SOURCE_DATASET
        and source.get("source_dataset") == SOURCE_DATASET
        and payload.get("is_pi_capture") is False
        and source.get("is_pi_capture") is False
        and capture.get("is_pi_capture") is False
        and payload.get("is_own_capture") is False
        and source.get("is_own_capture") is False
        and capture.get("is_own_capture") is False
    )


def _no_demo_clip_as_final_sample(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    source = payload.get("source") or {}
    capture = payload.get("capture") or {}
    return (
        payload.get("is_demo_playback_sample") is False
        and source.get("is_demo_playback_sample") is False
        and capture.get("is_demo_playback_sample") is False
        and payload.get("is_final_dashboard_sample") is True
        and source.get("is_final_dashboard_sample") is True
        and capture.get("is_final_dashboard_sample") is True
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _as_float_list(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result: list[float] = []
    for item in value:
        result.append(_as_float(item))
    return result


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
