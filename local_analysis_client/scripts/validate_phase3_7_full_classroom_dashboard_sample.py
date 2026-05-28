from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_REAL_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")
DEFAULT_API_BASE_URL = "http://127.0.0.1:8011"

ANALYSIS_ID = "phase37_full_classroom_sav_20200908_17"
CLASSROOM_ID = "classroom_101"
SOURCE_VIDEO_NAME = "local_imported_sav_full_classroom_20200908_17.mp4"
SOURCE_JSON_NAME = "local_imported_sav_full_classroom_20200908_17.json"
UPLOAD_JSON_FILENAME = "phase37_full_classroom_sav_20200908_17.json"
UPLOAD_RESPONSE_FILENAME = "phase37_full_classroom_upload_response.json"
UPLOAD_STATE_FILENAME = "phase37_full_classroom_upload_state.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.7 full-classroom dashboard sample.")
    parser.add_argument("--real-sample-root", type=Path, default=DEFAULT_REAL_SAMPLE_ROOT)
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--teacher-username", default=os.environ.get("TEACHER_USERNAME", "teacher"))
    parser.add_argument("--teacher-password", default=os.environ.get("TEACHER_PASSWORD", ""))
    args = parser.parse_args()

    real_sample_root = args.real_sample_root.resolve()
    source_video = real_sample_root / "videos" / SOURCE_VIDEO_NAME
    source_json = real_sample_root / "analysis_results" / SOURCE_JSON_NAME
    upload_dir = real_sample_root / "cloud_upload"
    upload_payload = upload_dir / UPLOAD_JSON_FILENAME
    upload_response = upload_dir / UPLOAD_RESPONSE_FILENAME
    upload_state = upload_dir / UPLOAD_STATE_FILENAME
    upload_script = Path(__file__).resolve().parent / "phase3_6b_upload_full_classroom_to_cloud.py"

    script_present = upload_script.exists()
    video_present = source_video.exists()
    analysis_present = source_json.exists()
    payload_created = upload_payload.exists()
    response_payload = _read_json(upload_response)
    state = _read_json(upload_state)
    local_payload = _read_json(upload_payload)

    upload_http_ok = str(state.get("http_status") or "") == "200"
    upload_success = response_payload.get("success") is True
    response_video_url = str(response_payload.get("video_url") or "")
    video_url_present = response_video_url.startswith("/uploads/")
    full_video_uploaded = upload_success and video_url_present and bool(response_payload.get("video_path"))
    full_analysis_uploaded = upload_success and bool(response_payload.get("saved_path"))
    no_manual_copy_required = upload_success and video_url_present

    tmp = upload_dir / "_phase37_validation_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    if True:
        tmp_dir = Path(tmp)
        teacher_cookie = tmp_dir / "teacher.cookie"
        login_out = tmp_dir / "teacher-login.json"
        detail_out = tmp_dir / "detail.json"
        dashboard_out = tmp_dir / "dashboard.html"
        static_out = tmp_dir / "static-video.bin"

        login_status = _curl(
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
                f"{args.api_base_url.rstrip('/')}/api/auth/login",
            ]
        )
        teacher_login_ok = login_status == "200" and _json_success(login_out)

        detail_status = "000"
        dashboard_status = "000"
        static_status = "000"
        if teacher_login_ok:
            detail_status = _curl(
                [
                    "-o",
                    str(detail_out),
                    "-w",
                    "%{http_code}",
                    "-b",
                    str(teacher_cookie),
                    f"{args.api_base_url.rstrip('/')}/api/teacher/results/{ANALYSIS_ID}",
                ]
            )
            dashboard_status = _curl(
                [
                    "-o",
                    str(dashboard_out),
                    "-w",
                    "%{http_code}",
                    "-b",
                    str(teacher_cookie),
                    f"{args.api_base_url.rstrip('/')}/dashboard?result_id={ANALYSIS_ID}",
                ]
            )
        if video_url_present:
            static_status = _curl(
                [
                    "-r",
                    "0-0",
                    "-o",
                    str(static_out),
                    "-w",
                    "%{http_code}",
                    f"{args.api_base_url.rstrip('/')}{response_video_url}",
                ]
            )

        detail_payload = _read_json(detail_out)
        result = detail_payload.get("result") if isinstance(detail_payload.get("result"), dict) else {}
        raw_payload = _detail_raw_payload(result)
        detail_video = result.get("video") if isinstance(result.get("video"), dict) else {}

        detail_ok = detail_status == "200" and detail_payload.get("success") is True
        detail_video_url_match = detail_video.get("video_url") == response_video_url
        dashboard_reachable = dashboard_status == "200"
        static_video_ok = static_status in {"200", "206"}
        dashboard_video_signal = _file_contains(dashboard_out, response_video_url) or _file_contains(dashboard_out, 'data-marker="video-area"')

        duration_values = [
            _as_float(detail_video.get("duration_seconds")),
            _as_float((raw_payload.get("video") or {}).get("duration_seconds")),
            _as_float((raw_payload.get("time") or {}).get("duration_seconds")),
            _as_float((local_payload.get("time") or {}).get("duration_seconds")),
        ]
        duration_not_60 = any(value > 600 for value in duration_values)
        duration_aligned = _duration_aligned(raw_payload or local_payload)
        no_sav_as_pi = _no_sav_as_pi_capture(raw_payload or local_payload)
        no_demo_as_final = _no_demo_clip_as_final_sample(raw_payload or local_payload)
        final_ready = (
            script_present
            and video_present
            and analysis_present
            and payload_created
            and upload_http_ok
            and upload_success
            and no_manual_copy_required
            and full_video_uploaded
            and full_analysis_uploaded
            and video_url_present
            and duration_not_60
            and duration_aligned
            and detail_ok
            and detail_video_url_match
            and dashboard_reachable
            and static_video_ok
            and dashboard_video_signal
            and no_sav_as_pi
            and no_demo_as_final
        )

    print(f"PHASE36B_LOCAL_UPLOAD_SCRIPT_PRESENT={_bool_text(script_present)}")
    print(f"PHASE36B_FULL_CLASSROOM_VIDEO_PRESENT={_bool_text(video_present)}")
    print(f"PHASE36B_FULL_CLASSROOM_ANALYSIS_JSON_PRESENT={_bool_text(analysis_present)}")
    print(f"PHASE36B_CLOUD_PAYLOAD_CREATED={_bool_text(payload_created)}")
    print(f"PHASE36B_MULTIPART_UPLOAD_HTTP_OK={_bool_text(upload_http_ok)}")
    print(f"PHASE36B_MULTIPART_UPLOAD_SUCCESS={_bool_text(upload_success)}")
    print(f"PHASE36B_NO_MANUAL_COPY_REQUIRED={_bool_text(no_manual_copy_required)}")
    print(f"PHASE37_FINAL_ANALYSIS_ID={ANALYSIS_ID}")
    print(f"PHASE37_FULL_CLASS_VIDEO_UPLOADED={_bool_text(full_video_uploaded)}")
    print(f"PHASE37_FULL_CLASS_ANALYSIS_UPLOADED={_bool_text(full_analysis_uploaded)}")
    print(f"PHASE37_VIDEO_URL_PRESENT={_bool_text(video_url_present)}")
    print(f"PHASE37_VIDEO_DURATION_NOT_60S={_bool_text(duration_not_60)}")
    print(f"PHASE37_VIDEO_ANALYSIS_DURATION_ALIGNED={_bool_text(duration_aligned)}")
    print(f"PHASE37_DETAIL_API_OK={_bool_text(detail_ok)}")
    print(f"PHASE37_DASHBOARD_REACHABLE={_bool_text(dashboard_reachable)}")
    print(f"PHASE37_FINAL_DASHBOARD_SAMPLE_READY={_bool_text(final_ready)}")
    print(f"PHASE37_NO_SAV_AS_PI_CAPTURE={_bool_text(no_sav_as_pi)}")
    print(f"PHASE37_NO_DEMO_CLIP_AS_FINAL_SAMPLE={_bool_text(no_demo_as_final)}")
    print(f"PHASE37_RESPONSE_VIDEO_URL={response_video_url}")
    print(f"PHASE37_DASHBOARD_URL={args.api_base_url.rstrip('/')}/dashboard?result_id={ANALYSIS_ID}")
    return 0 if final_ready else 1


def _curl(args: list[str], timeout: int = 120) -> str:
    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("curl_not_available")
    command = [curl, "-sS", "--noproxy", "*", "--max-time", str(timeout), *args]
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 10)
    if result.returncode != 0:
        return "000"
    return result.stdout.strip()


def _detail_raw_payload(result: dict[str, Any]) -> dict[str, Any]:
    for key in ("raw_payload", "result", "payload_json"):
        value = result.get(key)
        if isinstance(value, dict):
            return value
    return {}


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
    capture = payload.get("capture") or {}
    return (
        payload.get("source_dataset") == "SAV"
        and capture.get("source_dataset") == "SAV"
        and payload.get("is_pi_capture") is False
        and capture.get("is_pi_capture") is False
        and payload.get("is_own_capture") is False
        and capture.get("is_own_capture") is False
    )


def _no_demo_clip_as_final_sample(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    capture = payload.get("capture") or {}
    return (
        payload.get("is_demo_playback_sample") is False
        and capture.get("is_demo_playback_sample") is False
        and payload.get("is_final_dashboard_sample") is True
        and capture.get("is_final_dashboard_sample") is True
    )


def _json_success(path: Path) -> bool:
    return _read_json(path).get("success") is True


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _file_contains(path: Path, needle: str) -> bool:
    if not needle or not path.exists():
        return False
    try:
        return needle in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
