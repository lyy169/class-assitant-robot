from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_PACKAGE_DIR = Path(
    r"C:\Users\lyy\Desktop\gradu\phase35_cloud_upload_package\phase35_local_imported_sav_full_classroom_20200908_17"
)

DEMO_FILENAME = "phase35_demo_classroom_101.mp4"
UPLOAD_JSON_FILENAME = "phase35_cloud_upload_result.json"
PACKAGE_MANIFEST_FILENAME = "package.json"
SUMMARY_FILENAME = "local_imported_full_classroom_summary.csv"
REPORT_FILENAME = "local_imported_full_classroom_validation_report.md"
EXPECTED_VIDEO_URL = f"/uploads/{DEMO_FILENAME}"
EXPECTED_FIELDS = {
    "source_dataset": "SAV",
    "source_type": "local_imported_video",
    "sample_type": "cloud_playback_demo_from_external_classroom_video",
    "is_pi_capture": False,
    "is_own_capture": False,
    "is_local_processed": True,
    "is_demo_playback_sample": True,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.5b local cloud upload package.")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    args = parser.parse_args()

    _refresh_windows_path()
    package_dir = args.package_dir.resolve()
    demo_video = package_dir / DEMO_FILENAME
    upload_json = package_dir / UPLOAD_JSON_FILENAME
    package_manifest = package_dir / PACKAGE_MANIFEST_FILENAME
    summary_csv = package_dir / SUMMARY_FILENAME
    report_md = package_dir / REPORT_FILENAME

    package_dir_present = package_dir.exists()
    demo_present = demo_video.exists()
    duration = _probe_duration_seconds(demo_video) if demo_present else None
    video_probe = _probe_video_stream(demo_video) if demo_present else {}
    browser_compatible = _browser_compatible(video_probe) if demo_present else False
    payload = _read_json(upload_json)
    manifest = _read_json(package_manifest)

    upload_json_present = upload_json.exists()
    v11_shape_ok = _v11_shape_ok(payload)
    video_url_ok = payload.get("video", {}).get("video_url") == EXPECTED_VIDEO_URL if isinstance(payload.get("video"), dict) else False
    classroom_id_present = bool(payload.get("classroom_id"))
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    source_host_present = bool(source.get("source_host"))
    source_marked = _source_marked(payload)
    not_pi_capture = _bool_false(payload.get("is_pi_capture")) and _bool_false(source.get("is_pi_capture"))
    not_own_capture = _bool_false(payload.get("is_own_capture")) and _bool_false(source.get("is_own_capture"))
    package_manifest_present = package_manifest.exists() and _manifest_ok(manifest)
    report_files_present = summary_csv.exists() and report_md.exists()
    ok = (
        package_dir_present
        and demo_present
        and _duration_ok(duration)
        and browser_compatible is True
        and upload_json_present
        and v11_shape_ok
        and video_url_ok
        and classroom_id_present
        and source_host_present
        and source_marked
        and not_pi_capture
        and not_own_capture
        and package_manifest_present
        and report_files_present
    )

    print(f"PHASE35B_LOCAL_PACKAGE_DIR_PRESENT={_bool_text(package_dir_present)}")
    print(f"PHASE35B_DEMO_VIDEO_PRESENT={_bool_text(demo_present)}")
    print(f"PHASE35B_DEMO_VIDEO_DURATION_SECONDS={_format_number(duration)}")
    print(f"PHASE35B_DEMO_VIDEO_BROWSER_COMPATIBLE={_tri_text(browser_compatible)}")
    print(f"PHASE35B_UPLOAD_JSON_PRESENT={_bool_text(upload_json_present)}")
    print(f"PHASE35B_UPLOAD_JSON_V11_SHAPE_OK={_bool_text(v11_shape_ok)}")
    print(f"PHASE35B_UPLOAD_JSON_VIDEO_URL_OK={_bool_text(video_url_ok)}")
    print(f"PHASE35B_UPLOAD_JSON_CLASSROOM_ID_PRESENT={_bool_text(classroom_id_present)}")
    print(f"PHASE35B_UPLOAD_JSON_SOURCE_HOST_PRESENT={_bool_text(source_host_present)}")
    print(f"PHASE35B_UPLOAD_JSON_SOURCE_MARKED={_bool_text(source_marked)}")
    print(f"PHASE35B_UPLOAD_JSON_NOT_PI_CAPTURE={_bool_text(not_pi_capture)}")
    print(f"PHASE35B_UPLOAD_JSON_NOT_OWN_CAPTURE={_bool_text(not_own_capture)}")
    print(f"PHASE35B_PACKAGE_MANIFEST_PRESENT={_bool_text(package_manifest_present)}")
    print(f"PHASE35B_REPORT_FILES_PRESENT={_bool_text(report_files_present)}")
    print(f"PHASE35B_LOCAL_CLOUD_UPLOAD_PACKAGE_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _v11_shape_ok(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    required = ("schema_version", "analysis_id", "classroom_id", "video_id", "source", "time", "summary", "teacher", "students", "timeline")
    if any(field not in payload for field in required):
        return False
    if payload.get("schema_version") != "v1.1":
        return False
    if not isinstance(payload.get("source"), dict):
        return False
    source = payload["source"]
    if not all(source.get(field) for field in ("source_kind", "source_host", "source_path")):
        return False
    teacher = payload.get("teacher")
    if not isinstance(teacher, dict) or not isinstance(teacher.get("question_events", []), list):
        return False
    timeline = payload.get("timeline")
    if not isinstance(timeline, dict):
        return False
    curves = [timeline.get(key) for key in ("attention_curve", "heat_curve", "activity_curve")]
    if not all(isinstance(curve, list) for curve in curves):
        return False
    return len({len(curve) for curve in curves}) == 1


def _source_marked(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    capture = payload.get("capture") if isinstance(payload.get("capture"), dict) else {}
    for container in (payload, source):
        for key, expected in EXPECTED_FIELDS.items():
            if container.get(key) != expected:
                return False
    for key in ("source_dataset", "source_type", "sample_type", "is_pi_capture", "is_own_capture", "is_local_processed"):
        if capture.get(key) != EXPECTED_FIELDS[key]:
            return False
    return True


def _manifest_ok(manifest: dict[str, Any]) -> bool:
    if not manifest:
        return False
    required = (
        "package_id",
        "analysis_id",
        "cloud_video_filename",
        "cloud_video_target_path",
        "cloud_video_url",
        "cloud_upload_json",
        "cloud_upload_api",
        "dashboard_url_after_upload",
        "teacher_report_url_after_upload",
        "source_dataset",
        "source_type",
        "sample_type",
        "is_pi_capture",
        "is_own_capture",
        "is_local_processed",
        "is_demo_playback_sample",
        "created_at",
        "manual_event_note",
    )
    if any(field not in manifest for field in required):
        return False
    return (
        manifest.get("cloud_video_filename") == DEMO_FILENAME
        and manifest.get("cloud_video_url") == EXPECTED_VIDEO_URL
        and manifest.get("source_dataset") == "SAV"
        and manifest.get("source_type") == "local_imported_video"
        and manifest.get("sample_type") == "cloud_playback_demo_from_external_classroom_video"
        and manifest.get("is_pi_capture") is False
        and manifest.get("is_own_capture") is False
    )


def _probe_duration_seconds(video_path: Path) -> float | None:
    if shutil.which("ffprobe") is None:
        return None
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
    if shutil.which("ffprobe") is None:
        return {}
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


def _browser_compatible(video_probe: dict[str, str]) -> bool | None:
    if not video_probe:
        return None
    return video_probe.get("codec_name") in {"h264", "avc1"} and video_probe.get("pix_fmt") == "yuv420p"


def _duration_ok(duration: float | None) -> bool:
    return duration is not None and 55.0 <= duration <= 65.0


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


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


def _bool_false(value: Any) -> bool:
    return value is False or str(value).lower() == "false"


def _format_number(value: float | None) -> str:
    return "unknown" if value is None else f"{value:.3f}".rstrip("0").rstrip(".")


def _tri_text(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return _bool_text(value)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
