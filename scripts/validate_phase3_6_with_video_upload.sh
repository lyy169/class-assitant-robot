#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
STAGING_DIR="${STAGING_DIR:-/root/video_project_src/cloud_backend/data/phase35_local_to_cloud_package/phase35_local_imported_sav_full_classroom_20200908_17}"
RESULT_JSON="${RESULT_JSON:-${STAGING_DIR}/phase35_cloud_upload_result.json}"
VIDEO_FILE="${VIDEO_FILE:-${STAGING_DIR}/phase35_demo_classroom_101.mp4}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase36-with-video-validation-$$"

mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

print_marker() {
  echo "$1=$2"
}

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

curl_status() {
  local method="$1"
  local url="$2"
  local output="$3"
  shift 3
  curl -sS -o "$output" -w "%{http_code}" -X "$method" --max-time 30 "$@" "$url" 2>/dev/null || echo "000"
}

json_success_ok() {
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

json_field() {
  local file="$1"
  local field="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$field" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
value = payload
for part in sys.argv[2].split("."):
    if not isinstance(value, dict):
        value = ""
        break
    value = value.get(part, "")
if value is None:
    value = ""
print(value)
PY
}

endpoint_present() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
paths = payload.get("paths") or {}
methods = paths.get("/api/interaction-results/with-video") or {}
sys.exit(0 if "post" in methods else 1)
PY
}

detail_video_url_matches() {
  local file="$1"
  local expected="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$expected" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
expected = sys.argv[2]
video = (payload.get("result") or {}).get("video") or {}
sys.exit(0 if video.get("video_url") == expected else 1)
PY
}

echo "[info] Phase 3.6 with-video upload smoke test"
echo "[info] This validates the multipart endpoint only. The 1-minute demo clip is not the final competition sample."
echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] STAGING_DIR=${STAGING_DIR}"

[ -d "$STAGING_DIR" ] && STAGING_DIR_PRESENT=true || STAGING_DIR_PRESENT=false
[ -f "$RESULT_JSON" ] && RESULT_JSON_PRESENT=true || RESULT_JSON_PRESENT=false
[ -f "$VIDEO_FILE" ] && VIDEO_FILE_PRESENT=true || VIDEO_FILE_PRESENT=false
if [ "$STAGING_DIR_PRESENT" = "true" ] && [ "$RESULT_JSON_PRESENT" = "true" ] && [ "$VIDEO_FILE_PRESENT" = "true" ]; then
  STAGING_PACKAGE_PRESENT=true
else
  STAGING_PACKAGE_PRESENT=false
fi

OPENAPI_OUT="$TMP_DIR/openapi.json"
STATUS="$(curl_status GET "${API_BASE_URL}/openapi.json" "$OPENAPI_OUT")"
if [ "$STATUS" = "200" ] && endpoint_present "$OPENAPI_OUT"; then
  WITH_VIDEO_ENDPOINT_PRESENT=true
else
  WITH_VIDEO_ENDPOINT_PRESENT=false
fi
print_marker "PHASE36_WITH_VIDEO_ENDPOINT_PRESENT" "$WITH_VIDEO_ENDPOINT_PRESENT"

HEALTH_OUT="$TMP_DIR/health.json"
STATUS="$(curl_status GET "${API_BASE_URL}/health" "$HEALTH_OUT")"
[ "$STATUS" = "200" ] && HEALTH_OK=true || HEALTH_OK=false
print_marker "PHASE36_HEALTH_OK" "$HEALTH_OK"

print_marker "PHASE36_STAGING_PACKAGE_PRESENT" "$STAGING_PACKAGE_PRESENT"

UPLOAD_OUT="$TMP_DIR/upload-response.json"
MULTIPART_UPLOAD_HTTP_OK=false
MULTIPART_UPLOAD_SUCCESS=false
RESPONSE_VIDEO_URL_PRESENT=false
CLOUD_VIDEO_SAVED=false
CLOUD_RAW_JSON_SAVED=false
STATIC_VIDEO_OK=false
TEACHER_DETAIL_OK=false
DETAIL_VIDEO_URL_MATCH=false
DASHBOARD_REACHABLE=false
NO_MANUAL_VIDEO_COPY_REQUIRED=false

AUTH_HEADER_ARGS=()
if [ -n "${CLOUD_API_KEY:-}" ]; then
  AUTH_HEADER_ARGS=(-H "X-API-Key: ${CLOUD_API_KEY}")
fi

if [ "$STAGING_PACKAGE_PRESENT" = "true" ]; then
  HTTP_STATUS="$(curl -sS -o "$UPLOAD_OUT" -w "%{http_code}" --max-time 60 -X POST \
    "${AUTH_HEADER_ARGS[@]}" \
    -F "result_json=@${RESULT_JSON};type=application/json" \
    -F "video_file=@${VIDEO_FILE};type=video/mp4" \
    "${API_BASE_URL}/api/interaction-results/with-video" 2>/dev/null || echo "000")"
  if [ "$HTTP_STATUS" = "200" ]; then
    MULTIPART_UPLOAD_HTTP_OK=true
  fi
  if [ "$HTTP_STATUS" != "404" ] && [ "$HTTP_STATUS" != "405" ]; then
    WITH_VIDEO_ENDPOINT_PRESENT=true
  fi
  json_success_ok "$UPLOAD_OUT" && MULTIPART_UPLOAD_SUCCESS=true || MULTIPART_UPLOAD_SUCCESS=false
fi

print_marker "PHASE36_MULTIPART_UPLOAD_HTTP_OK" "$MULTIPART_UPLOAD_HTTP_OK"
print_marker "PHASE36_MULTIPART_UPLOAD_SUCCESS" "$MULTIPART_UPLOAD_SUCCESS"

RESPONSE_VIDEO_URL="$(json_field "$UPLOAD_OUT" "video_url" 2>/dev/null || true)"
RESPONSE_VIDEO_PATH="$(json_field "$UPLOAD_OUT" "video_path" 2>/dev/null || true)"
RESPONSE_SAVED_PATH="$(json_field "$UPLOAD_OUT" "saved_path" 2>/dev/null || true)"
RESPONSE_ANALYSIS_ID="$(json_field "$UPLOAD_OUT" "analysis_id" 2>/dev/null || true)"

if [ -n "$RESPONSE_VIDEO_URL" ] && [[ "$RESPONSE_VIDEO_URL" == /uploads/* ]]; then
  RESPONSE_VIDEO_URL_PRESENT=true
fi
if [ -n "$RESPONSE_VIDEO_PATH" ] && [ -f "$RESPONSE_VIDEO_PATH" ]; then
  CLOUD_VIDEO_SAVED=true
fi
if [ -n "$RESPONSE_SAVED_PATH" ] && [ -f "$RESPONSE_SAVED_PATH" ]; then
  CLOUD_RAW_JSON_SAVED=true
fi

print_marker "PHASE36_CLOUD_VIDEO_SAVED" "$CLOUD_VIDEO_SAVED"
print_marker "PHASE36_CLOUD_RAW_JSON_SAVED" "$CLOUD_RAW_JSON_SAVED"
print_marker "PHASE36_RESPONSE_VIDEO_URL_PRESENT" "$RESPONSE_VIDEO_URL_PRESENT"

if [ "$RESPONSE_VIDEO_URL_PRESENT" = "true" ]; then
  STATIC_OUT="$TMP_DIR/static-video.bin"
  STATUS="$(curl_status GET "${API_BASE_URL}${RESPONSE_VIDEO_URL}" "$STATIC_OUT")"
  [ "$STATUS" = "200" ] && STATIC_VIDEO_OK=true || STATIC_VIDEO_OK=false
fi
print_marker "PHASE36_STATIC_VIDEO_OK" "$STATIC_VIDEO_OK"

TEACHER_COOKIE="$TMP_DIR/teacher.cookie"
TEACHER_LOGIN_OUT="$TMP_DIR/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$TEACHER_LOGIN_OUT" -c "$TEACHER_COOKIE" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
if [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_LOGIN_OUT" && [ -n "$RESPONSE_ANALYSIS_ID" ]; then
  DETAIL_OUT="$TMP_DIR/detail.json"
  STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESPONSE_ANALYSIS_ID}" "$DETAIL_OUT" -b "$TEACHER_COOKIE")"
  if [ "$STATUS" = "200" ] && json_success_ok "$DETAIL_OUT"; then
    TEACHER_DETAIL_OK=true
  fi
  detail_video_url_matches "$DETAIL_OUT" "$RESPONSE_VIDEO_URL" && DETAIL_VIDEO_URL_MATCH=true || DETAIL_VIDEO_URL_MATCH=false

  DASHBOARD_OUT="$TMP_DIR/dashboard.html"
  STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESPONSE_ANALYSIS_ID}" "$DASHBOARD_OUT" -b "$TEACHER_COOKIE")"
  [ "$STATUS" = "200" ] && DASHBOARD_REACHABLE=true || DASHBOARD_REACHABLE=false
fi

print_marker "PHASE36_TEACHER_DETAIL_OK" "$TEACHER_DETAIL_OK"
print_marker "PHASE36_DETAIL_VIDEO_URL_MATCH" "$DETAIL_VIDEO_URL_MATCH"
print_marker "PHASE36_DASHBOARD_REACHABLE" "$DASHBOARD_REACHABLE"

if [ "$MULTIPART_UPLOAD_SUCCESS" = "true" ] && [ "$CLOUD_VIDEO_SAVED" = "true" ] && [ "$STATIC_VIDEO_OK" = "true" ]; then
  NO_MANUAL_VIDEO_COPY_REQUIRED=true
fi
print_marker "PHASE36_NO_MANUAL_VIDEO_COPY_REQUIRED" "$NO_MANUAL_VIDEO_COPY_REQUIRED"

DEMO_CLIP_NOT_FINAL_SAMPLE=true
print_marker "PHASE36_DEMO_CLIP_NOT_FINAL_SAMPLE" "$DEMO_CLIP_NOT_FINAL_SAMPLE"

if [ "$WITH_VIDEO_ENDPOINT_PRESENT" = "true" ] \
  && [ "$HEALTH_OK" = "true" ] \
  && [ "$STAGING_PACKAGE_PRESENT" = "true" ] \
  && [ "$MULTIPART_UPLOAD_HTTP_OK" = "true" ] \
  && [ "$MULTIPART_UPLOAD_SUCCESS" = "true" ] \
  && [ "$CLOUD_VIDEO_SAVED" = "true" ] \
  && [ "$CLOUD_RAW_JSON_SAVED" = "true" ] \
  && [ "$RESPONSE_VIDEO_URL_PRESENT" = "true" ] \
  && [ "$STATIC_VIDEO_OK" = "true" ] \
  && [ "$TEACHER_DETAIL_OK" = "true" ] \
  && [ "$DETAIL_VIDEO_URL_MATCH" = "true" ] \
  && [ "$DASHBOARD_REACHABLE" = "true" ] \
  && [ "$NO_MANUAL_VIDEO_COPY_REQUIRED" = "true" ] \
  && [ "$DEMO_CLIP_NOT_FINAL_SAMPLE" = "true" ]; then
  LOCAL_AUTO_UPLOAD_CLOUD_READY=true
else
  LOCAL_AUTO_UPLOAD_CLOUD_READY=false
fi

print_marker "PHASE36_LOCAL_AUTO_UPLOAD_CLOUD_READY" "$LOCAL_AUTO_UPLOAD_CLOUD_READY"
