#!/bin/bash
set -u

DEFAULT_STAGING_DIR="/root/video_project_src/cloud_backend/data/phase35_local_to_cloud_package/phase35_local_imported_sav_full_classroom_20200908_17"
API_BASE_URL="http://127.0.0.1:8011"
STAGING_DIR="$DEFAULT_STAGING_DIR"
OVERWRITE_VIDEO=false

VIDEO_NAME="phase35_demo_classroom_101.mp4"
JSON_NAME="phase35_cloud_upload_result.json"
PACKAGE_NAME="package.json"
TARGET_VIDEO_DIR="/root/video_project/uploads"
TARGET_VIDEO_PATH="${TARGET_VIDEO_DIR}/${VIDEO_NAME}"
EXPECTED_VIDEO_URL="/uploads/${VIDEO_NAME}"
UPLOAD_RESPONSE_NAME="phase35_cloud_upload_response.json"

print_marker() {
  echo "$1=$2"
}

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/phase3_5_send_local_package_to_cloud.sh [--staging-dir DIR] [--api-base-url URL] [--overwrite-video]

This script assumes the Phase 3.5b local export package has already been manually copied to the cloud staging directory.
It copies the staged MP4 into /root/video_project/uploads and POSTs the staged JSON to /api/interaction-results.
It does not start services, restart services, edit systemd, modify database schema, or commit git changes.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --staging-dir)
      shift
      STAGING_DIR="${1:-}"
      ;;
    --api-base-url)
      shift
      API_BASE_URL="${1:-}"
      ;;
    --overwrite-video)
      OVERWRITE_VIDEO=true
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
  shift
done

find_python() {
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  echo ""
}

PYTHON_BIN="$(find_python)"

json_check_video_url() {
  local file="$1"
  local expected="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$expected" <<'PY'
import json, sys
path, expected = sys.argv[1], sys.argv[2]
payload = json.load(open(path, encoding="utf-8"))
video = payload.get("video") or {}
value = video.get("video_url") or payload.get("video_url") or (payload.get("source") or {}).get("video_url")
sys.exit(0 if value == expected else 1)
PY
}

json_check_source_marked() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
fields = []
for obj_name in ("dataset", "source", "metadata"):
    obj = payload.get(obj_name) or {}
    if isinstance(obj, dict):
        fields.extend(str(v).lower() for v in obj.values())
for key in ("analysis_id", "lesson_title", "classroom_id"):
    fields.append(str(payload.get(key, "")).lower())
text = " ".join(fields)
markers = ("phase35", "local", "sav", "demo")
sys.exit(0 if any(marker in text for marker in markers) else 1)
PY
}

json_check_not_pi_capture() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
source = payload.get("source") or {}
dataset = payload.get("dataset") or {}
values = [
    source.get("source_kind", ""),
    source.get("source_host", ""),
    source.get("source_path", ""),
    dataset.get("source", ""),
    dataset.get("purpose", ""),
]
text = " ".join(str(v).lower() for v in values)
blocked = ("raspberry", "raspberry_pi", "pi_capture", "picamera", "pi-camera")
sys.exit(0 if not any(item in text for item in blocked) else 1)
PY
}

json_check_not_own_capture() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
source = payload.get("source") or {}
dataset = payload.get("dataset") or {}
values = [
    source.get("source_kind", ""),
    source.get("source_host", ""),
    source.get("source_path", ""),
    dataset.get("source", ""),
    dataset.get("purpose", ""),
]
text = " ".join(str(v).lower() for v in values)
blocked = ("own_capture", "self_capture", "self-captured", "own-captured")
sys.exit(0 if not any(item in text for item in blocked) else 1)
PY
}

json_success() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if payload.get("success") is True else 1)
PY
}

saved_path_present() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, os, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
saved_path = payload.get("saved_path") or ""
sys.exit(0 if saved_path and os.path.exists(saved_path) else 1)
PY
}

http_status() {
  local url="$1"
  curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000"
}

echo "[info] Phase 3.5c local-to-cloud send script"
echo "[info] This script does not pull files from Windows. The package must already exist in staging."
echo "[info] STAGING_DIR=${STAGING_DIR}"
echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] TARGET_VIDEO_PATH=${TARGET_VIDEO_PATH}"
echo "[info] EXPECTED_VIDEO_URL=${EXPECTED_VIDEO_URL}"

PACKAGE_JSON="${STAGING_DIR}/${PACKAGE_NAME}"
DEMO_VIDEO="${STAGING_DIR}/${VIDEO_NAME}"
UPLOAD_JSON="${STAGING_DIR}/${JSON_NAME}"
UPLOAD_RESPONSE="${STAGING_DIR}/${UPLOAD_RESPONSE_NAME}"

[ -d "$STAGING_DIR" ] && STAGING_DIR_PRESENT=true || STAGING_DIR_PRESENT=false
[ -f "$PACKAGE_JSON" ] && PACKAGE_JSON_PRESENT=true || PACKAGE_JSON_PRESENT=false
[ -f "$DEMO_VIDEO" ] && DEMO_VIDEO_PRESENT=true || DEMO_VIDEO_PRESENT=false
[ -f "$UPLOAD_JSON" ] && UPLOAD_JSON_PRESENT=true || UPLOAD_JSON_PRESENT=false

json_check_video_url "$UPLOAD_JSON" "$EXPECTED_VIDEO_URL" && UPLOAD_JSON_VIDEO_URL_OK=true || UPLOAD_JSON_VIDEO_URL_OK=false
json_check_source_marked "$UPLOAD_JSON" && UPLOAD_JSON_SOURCE_MARKED=true || UPLOAD_JSON_SOURCE_MARKED=false
json_check_not_pi_capture "$UPLOAD_JSON" && UPLOAD_JSON_NOT_PI_CAPTURE=true || UPLOAD_JSON_NOT_PI_CAPTURE=false
json_check_not_own_capture "$UPLOAD_JSON" && UPLOAD_JSON_NOT_OWN_CAPTURE=true || UPLOAD_JSON_NOT_OWN_CAPTURE=false

[ -d "$TARGET_VIDEO_DIR" ] && VIDEO_TARGET_DIR_PRESENT=true || VIDEO_TARGET_DIR_PRESENT=false
VIDEO_COPIED=false
VIDEO_EXISTING_REUSED=false

if [ "$VIDEO_TARGET_DIR_PRESENT" = "true" ] && [ "$DEMO_VIDEO_PRESENT" = "true" ]; then
  if [ -f "$TARGET_VIDEO_PATH" ] && [ "$OVERWRITE_VIDEO" != "true" ]; then
    VIDEO_EXISTING_REUSED=true
  else
    if cp ${OVERWRITE_VIDEO:+-f} "$DEMO_VIDEO" "$TARGET_VIDEO_PATH"; then
      VIDEO_COPIED=true
    fi
  fi
fi

STATIC_STATUS="$(http_status "${API_BASE_URL}${EXPECTED_VIDEO_URL}")"
[ "$STATIC_STATUS" = "200" ] && VIDEO_URL_STATIC_OK=true || VIDEO_URL_STATIC_OK=false

CLOUD_UPLOAD_HTTP_OK=false
CLOUD_UPLOAD_SUCCESS=false
CLOUD_UPLOAD_SAVED_PATH_PRESENT=false

if [ "$UPLOAD_JSON_PRESENT" = "true" ]; then
  HTTP_STATUS="$(curl -sS -o "$UPLOAD_RESPONSE" -w "%{http_code}" --max-time 30 -X POST \
    -H "Content-Type: application/json" \
    --data-binary "@${UPLOAD_JSON}" \
    "${API_BASE_URL}/api/interaction-results" 2>/dev/null || echo "000")"
  [ "$HTTP_STATUS" = "200" ] && CLOUD_UPLOAD_HTTP_OK=true
  json_success "$UPLOAD_RESPONSE" && CLOUD_UPLOAD_SUCCESS=true || CLOUD_UPLOAD_SUCCESS=false
  saved_path_present "$UPLOAD_RESPONSE" && CLOUD_UPLOAD_SAVED_PATH_PRESENT=true || CLOUD_UPLOAD_SAVED_PATH_PRESENT=false
fi

if [ "$STAGING_DIR_PRESENT" = "true" ] \
  && [ "$PACKAGE_JSON_PRESENT" = "true" ] \
  && [ "$DEMO_VIDEO_PRESENT" = "true" ] \
  && [ "$UPLOAD_JSON_PRESENT" = "true" ] \
  && [ "$UPLOAD_JSON_VIDEO_URL_OK" = "true" ] \
  && [ "$UPLOAD_JSON_SOURCE_MARKED" = "true" ] \
  && [ "$UPLOAD_JSON_NOT_PI_CAPTURE" = "true" ] \
  && [ "$UPLOAD_JSON_NOT_OWN_CAPTURE" = "true" ] \
  && [ "$VIDEO_TARGET_DIR_PRESENT" = "true" ] \
  && { [ "$VIDEO_COPIED" = "true" ] || [ "$VIDEO_EXISTING_REUSED" = "true" ]; } \
  && [ "$VIDEO_URL_STATIC_OK" = "true" ] \
  && [ "$CLOUD_UPLOAD_HTTP_OK" = "true" ] \
  && [ "$CLOUD_UPLOAD_SUCCESS" = "true" ] \
  && [ "$CLOUD_UPLOAD_SAVED_PATH_PRESENT" = "true" ]; then
  LOCAL_TO_CLOUD_SEND_OK=true
else
  LOCAL_TO_CLOUD_SEND_OK=false
fi

print_marker "PHASE35C_STAGING_DIR_PRESENT" "$STAGING_DIR_PRESENT"
print_marker "PHASE35C_PACKAGE_JSON_PRESENT" "$PACKAGE_JSON_PRESENT"
print_marker "PHASE35C_DEMO_VIDEO_PRESENT" "$DEMO_VIDEO_PRESENT"
print_marker "PHASE35C_UPLOAD_JSON_PRESENT" "$UPLOAD_JSON_PRESENT"
print_marker "PHASE35C_UPLOAD_JSON_VIDEO_URL_OK" "$UPLOAD_JSON_VIDEO_URL_OK"
print_marker "PHASE35C_UPLOAD_JSON_SOURCE_MARKED" "$UPLOAD_JSON_SOURCE_MARKED"
print_marker "PHASE35C_UPLOAD_JSON_NOT_PI_CAPTURE" "$UPLOAD_JSON_NOT_PI_CAPTURE"
print_marker "PHASE35C_UPLOAD_JSON_NOT_OWN_CAPTURE" "$UPLOAD_JSON_NOT_OWN_CAPTURE"
print_marker "PHASE35C_VIDEO_TARGET_DIR_PRESENT" "$VIDEO_TARGET_DIR_PRESENT"
print_marker "PHASE35C_VIDEO_COPIED" "$VIDEO_COPIED"
print_marker "PHASE35C_VIDEO_EXISTING_REUSED" "$VIDEO_EXISTING_REUSED"
print_marker "PHASE35C_VIDEO_URL_STATIC_OK" "$VIDEO_URL_STATIC_OK"
print_marker "PHASE35C_CLOUD_UPLOAD_HTTP_OK" "$CLOUD_UPLOAD_HTTP_OK"
print_marker "PHASE35C_CLOUD_UPLOAD_SUCCESS" "$CLOUD_UPLOAD_SUCCESS"
print_marker "PHASE35C_CLOUD_UPLOAD_SAVED_PATH_PRESENT" "$CLOUD_UPLOAD_SAVED_PATH_PRESENT"
print_marker "PHASE35C_LOCAL_TO_CLOUD_SEND_OK" "$LOCAL_TO_CLOUD_SEND_OK"

