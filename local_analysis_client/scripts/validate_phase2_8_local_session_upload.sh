#!/usr/bin/env bash
set -u

if [ $# -lt 1 ]; then
  echo "Usage: bash scripts/validate_phase2_8_local_session_upload.sh <path-to-result-json>" >&2
  exit 2
fi

RESULT_JSON="$1"
export RESULT_JSON

python - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["RESULT_JSON"])
repo_root = Path.cwd()

def marker(name: str, value: object) -> None:
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    print(f"{name}={text}")

def audit_video_capability() -> tuple[str, str]:
    roots = [repo_root / "local-processor", repo_root / "scripts"]
    patterns = ("ffmpeg", "ffprobe", "moviepy", "VideoWriter", "transcode", "standardize")
    found = False
    for root in roots:
        if not root.exists():
            continue
        for candidate in root.rglob("*"):
            if not candidate.is_file() or candidate.suffix.lower() not in {".py", ".ps1", ".sh", ".md"}:
                continue
            if candidate.name in {
                "classroom_feedback_pipeline.py",
                "validate_phase2_8_local_session_upload.sh",
                "upload_phase2_8_sample.sh",
            }:
                continue
            try:
                text = candidate.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(pattern in text for pattern in patterns):
                found = True
                break
        if found:
            break
    return ("present" if found else "absent", "unknown")

transcode_capability, browser_compatible = audit_video_capability()

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
    valid_json = isinstance(payload, dict)
except Exception:
    payload = {}
    valid_json = False

teacher = payload.get("teacher") if isinstance(payload.get("teacher"), dict) else {}
source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
capture = payload.get("capture") if isinstance(payload.get("capture"), dict) else {}
video = payload.get("video") if isinstance(payload.get("video"), dict) else {}
upload = payload.get("upload") if isinstance(payload.get("upload"), dict) else {}

capture_required_present = all(capture.get(key) for key in ("device_id", "classroom_id", "captured_at"))
source_present = all(source.get(key) for key in ("source_kind", "source_host", "source_path"))
upload_present = all(upload.get(key) for key in ("uploaded_at", "api"))

marker("LOCAL_SESSION_JSON_VALID", valid_json)
marker("LOCAL_SOURCE_PRESENT", bool(source_present))
marker("LOCAL_CAPTURE_PRESENT", bool(capture_required_present))
marker("LOCAL_VIDEO_PRESENT", bool(video))
marker("LOCAL_UPLOAD_PRESENT", bool(upload_present))
marker("LOCAL_TEACHER_QUESTION_EVENTS_PRESERVED", bool(teacher.get("question_events")))
marker("LOCAL_VIDEO_TRANSCODE_CAPABILITY", transcode_capability)
marker("LOCAL_VIDEO_OUTPUT_BROWSER_COMPATIBLE", browser_compatible)
PY
