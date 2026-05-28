from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PACKAGE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\phase35_cloud_upload_package")
DEFAULT_REAL_SAMPLE_ROOT = Path(r"C:\Users\lyy\Desktop\gradu\real_classroom_samples")

PACKAGE_ID = "phase35_local_imported_sav_full_classroom_20200908_17"
ANALYSIS_ID = PACKAGE_ID
CLASSROOM_ID = "classroom_101"
SOURCE_VIDEO_ID = "20200908_17"
VIDEO_ID = "sav_20200908_17_phase35_demo"
DEMO_FILENAME = "phase35_demo_classroom_101.mp4"
UPLOAD_JSON_FILENAME = "phase35_cloud_upload_result.json"
PACKAGE_MANIFEST_FILENAME = "package.json"
SOURCE_RESULT_FILENAME = "local_imported_sav_full_classroom_20200908_17.json"
SOURCE_VIDEO_FILENAME = "local_imported_sav_full_classroom_20200908_17.mp4"
SOURCE_SUMMARY_FILENAME = "local_imported_full_classroom_summary.csv"
SOURCE_REPORT_FILENAME = "local_imported_full_classroom_validation_report.md"

DEMO_START_SECONDS = 16 * 60 + 20
DEMO_DURATION_SECONDS = 60
MANUAL_EVENT_NOTE = "16:27.5-16:30.5 contains many raised hands and a few standing students, manually observed."

SOURCE_DATASET = "SAV"
SOURCE_TYPE = "local_imported_video"
SAMPLE_TYPE = "cloud_playback_demo_from_external_classroom_video"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 3.5b local cloud upload package.")
    parser.add_argument("--package-root", type=Path, default=DEFAULT_PACKAGE_ROOT)
    parser.add_argument("--real-sample-root", type=Path, default=DEFAULT_REAL_SAMPLE_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    _refresh_windows_path()
    package_dir = args.package_root.resolve() / PACKAGE_ID
    sample_root = args.real_sample_root.resolve()
    input_video = sample_root / "videos" / SOURCE_VIDEO_FILENAME
    input_result = sample_root / "analysis_results" / SOURCE_RESULT_FILENAME
    input_summary = sample_root / "reports" / SOURCE_SUMMARY_FILENAME
    input_report = sample_root / "reports" / SOURCE_REPORT_FILENAME
    demo_video = package_dir / DEMO_FILENAME
    upload_json = package_dir / UPLOAD_JSON_FILENAME
    package_manifest = package_dir / PACKAGE_MANIFEST_FILENAME

    package_dir.mkdir(parents=True, exist_ok=True)
    _require_file(input_video)
    _require_file(input_result)
    _require_file(input_summary)
    _require_file(input_report)

    ffmpeg_available = _tool_available("ffmpeg", ["ffmpeg", "-version"])
    ffprobe_available = _tool_available("ffprobe", ["ffprobe", "-version"])
    if not ffmpeg_available:
        raise RuntimeError("ffmpeg_not_available")

    demo_status = _build_demo_video(input_video=input_video, demo_video=demo_video, overwrite=args.overwrite)
    demo_duration = _probe_duration_seconds(demo_video)
    video_probe = _probe_video_stream(demo_video)
    source_payload = _read_json(input_result)
    generated_at = _utc_now()
    payload = _build_upload_payload(
        source_payload=source_payload,
        generated_at=generated_at,
        demo_duration=demo_duration,
    )
    upload_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = _build_package_manifest(created_at=generated_at)
    package_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(input_summary, package_dir / SOURCE_SUMMARY_FILENAME)
    shutil.copy2(input_report, package_dir / SOURCE_REPORT_FILENAME)

    print(f"PHASE35B_FFMPEG_AVAILABLE={_bool_text(ffmpeg_available)}")
    print(f"PHASE35B_FFPROBE_AVAILABLE={_bool_text(ffprobe_available)}")
    print(f"PHASE35B_PACKAGE_DIR={package_dir}")
    print(f"PHASE35B_DEMO_VIDEO={demo_video}")
    print(f"PHASE35B_DEMO_VIDEO_STATUS={demo_status}")
    print(f"PHASE35B_DEMO_VIDEO_SIZE_BYTES={demo_video.stat().st_size if demo_video.exists() else 0}")
    print(f"PHASE35B_DEMO_VIDEO_DURATION_SECONDS={_format_number(demo_duration)}")
    print(f"PHASE35B_DEMO_VIDEO_CODEC={video_probe.get('codec_name', 'unknown')}")
    print(f"PHASE35B_DEMO_VIDEO_PIX_FMT={video_probe.get('pix_fmt', 'unknown')}")
    print(f"PHASE35B_UPLOAD_JSON={upload_json}")
    print(f"PHASE35B_PACKAGE_MANIFEST={package_manifest}")
    print(f"PHASE35B_LOCAL_EXPORT_PACKAGE_CREATED={_bool_text(demo_video.exists() and upload_json.exists() and package_manifest.exists())}")
    return 0


def _build_demo_video(*, input_video: Path, demo_video: Path, overwrite: bool) -> str:
    if demo_video.exists() and not overwrite:
        return "existing"
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(DEMO_START_SECONDS),
        "-i",
        str(input_video),
        "-t",
        str(DEMO_DURATION_SECONDS),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(demo_video),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    if result.returncode != 0 or not demo_video.exists():
        message = " ".join((result.stderr or result.stdout or "ffmpeg_failed").split())[:500]
        raise RuntimeError(message)
    return "created"


def _build_upload_payload(*, source_payload: dict[str, Any], generated_at: str, demo_duration: float | None) -> dict[str, Any]:
    payload = copy.deepcopy(source_payload)
    source_time = payload.get("time") if isinstance(payload.get("time"), dict) else {}
    captured_at = str(source_time.get("recorded_at") or source_time.get("generated_at") or generated_at)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    teacher = payload.get("teacher") if isinstance(payload.get("teacher"), dict) else {}
    students = payload.get("students") if isinstance(payload.get("students"), dict) else {}
    timeline = _normalize_timeline(payload.get("timeline"))
    teacher.setdefault("question_events", [])
    if not isinstance(teacher.get("question_events"), list):
        teacher["question_events"] = []

    payload.update(
        {
            "schema_version": "v1.1",
            "analysis_id": ANALYSIS_ID,
            "classroom_id": CLASSROOM_ID,
            "video_id": VIDEO_ID,
            "source": {
                "source_kind": "local_analyzer",
                "source_host": "local-pc-phase35",
                "source_path": SOURCE_RESULT_FILENAME,
                "source_dataset": SOURCE_DATASET,
                "source_type": SOURCE_TYPE,
                "sample_type": SAMPLE_TYPE,
                "is_pi_capture": False,
                "is_own_capture": False,
                "is_local_processed": True,
                "is_demo_playback_sample": True,
            },
            "time": {
                "recorded_at": captured_at,
                "generated_at": generated_at,
                "duration_seconds": int(round(demo_duration or DEMO_DURATION_SECONDS)),
            },
            "summary": summary,
            "teacher": teacher,
            "students": students,
            "timeline": timeline,
            "video": {
                "video_id": VIDEO_ID,
                "raw_video_path": SOURCE_VIDEO_FILENAME,
                "video_url": f"/uploads/{DEMO_FILENAME}",
                "duration_seconds": round(float(demo_duration or DEMO_DURATION_SECONDS), 3),
                "format": "mp4",
                "codec": "h264",
                "browser_compatible": True,
                "transcode_capability": "present",
                "standardized_video_path": DEMO_FILENAME,
                "transcode_status": "success",
                "transcode_error": "",
            },
            "capture": {
                "device_id": "external_sav_dataset",
                "device_name": "SAV public classroom video",
                "classroom_id": CLASSROOM_ID,
                "video_path": SOURCE_VIDEO_FILENAME,
                "captured_at": captured_at,
                "source_dataset": SOURCE_DATASET,
                "source_type": SOURCE_TYPE,
                "sample_type": SAMPLE_TYPE,
                "is_pi_capture": False,
                "is_own_capture": False,
                "is_local_processed": True,
            },
            "upload": {
                "target": "cloud_backend",
                "api": "/api/interaction-results",
                "client_version": "phase35-local-export",
                "uploaded_at": generated_at,
            },
            "source_dataset": SOURCE_DATASET,
            "source_type": SOURCE_TYPE,
            "sample_type": SAMPLE_TYPE,
            "is_pi_capture": False,
            "is_own_capture": False,
            "is_local_processed": True,
            "is_demo_playback_sample": True,
            "phase35b_boundary": {
                "manual_event_note": MANUAL_EVENT_NOTE,
                "cloud_export_only": True,
                "not_pi_capture": True,
                "not_own_capture": True,
                "not_full_sav_15_action_claim": True,
                "notes": [
                    "This package is generated locally and is not uploaded by this script.",
                    "SAV is an external public dataset, not Raspberry Pi capture and not own capture.",
                    "The demo clip is for cloud classroom playback validation.",
                ],
            },
        }
    )
    return payload


def _build_package_manifest(*, created_at: str) -> dict[str, Any]:
    return {
        "package_id": PACKAGE_ID,
        "analysis_id": ANALYSIS_ID,
        "cloud_video_filename": DEMO_FILENAME,
        "cloud_video_target_path": f"/root/video_project/uploads/{DEMO_FILENAME}",
        "cloud_video_url": f"/uploads/{DEMO_FILENAME}",
        "cloud_upload_json": UPLOAD_JSON_FILENAME,
        "cloud_upload_api": "/api/interaction-results",
        "dashboard_url_after_upload": f"/dashboard?result_id={ANALYSIS_ID}",
        "teacher_report_url_after_upload": f"/teacher/reports?result_id={ANALYSIS_ID}",
        "source_dataset": SOURCE_DATASET,
        "source_type": SOURCE_TYPE,
        "sample_type": SAMPLE_TYPE,
        "is_pi_capture": False,
        "is_own_capture": False,
        "is_local_processed": True,
        "is_demo_playback_sample": True,
        "created_at": created_at,
        "manual_event_note": MANUAL_EVENT_NOTE,
    }


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


def _as_float_list(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result: list[float] = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            result.append(0.0)
    return result


def _probe_duration_seconds(video_path: Path) -> float | None:
    try:
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
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def _probe_video_stream(video_path: Path) -> dict[str, str]:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,pix_fmt",
                "-of",
                "csv=p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode != 0:
        return {}
    parts = [part.strip() for part in result.stdout.strip().split(",")]
    return {"codec_name": parts[0], "pix_fmt": parts[1]} if len(parts) >= 2 else {}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def _require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(str(path))


def _tool_available(name: str, command: list[str]) -> bool:
    if shutil.which(name) is None:
        return False
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _refresh_windows_path() -> None:
    if os.name != "nt":
        return
    current_path = os.environ.get("PATH", "")
    try:
        import winreg

        user_path = _read_registry_path(winreg.HKEY_CURRENT_USER, r"Environment")
        system_path = _read_registry_path(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        )
    except OSError:
        return
    os.environ["PATH"] = ";".join(part for part in (current_path, system_path, user_path) if part)


def _read_registry_path(root: Any, subkey: str) -> str:
    import winreg

    try:
        with winreg.OpenKey(root, subkey) as key:
            value, _ = winreg.QueryValueEx(key, "Path")
            return str(value)
    except OSError:
        return ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _format_number(value: float | None) -> str:
    return "unknown" if value is None else f"{value:.3f}".rstrip("0").rstrip(".")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
