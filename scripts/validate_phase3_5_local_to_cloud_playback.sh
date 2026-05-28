#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-phase35_local_imported_sav_full_classroom_20200908_17}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
EXPECTED_VIDEO_URL="${EXPECTED_VIDEO_URL:-/uploads/phase35_demo_classroom_101.mp4}"
TMP_DIR="${TMPDIR:-/tmp}/phase35c-playback-validation-$$"

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
  curl -sS -o "$output" -w "%{http_code}" -X "$method" --max-time 15 "$@" "$url" 2>/dev/null || echo "000"
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

detail_video_playable() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
video = (payload.get("result") or {}).get("video") or {}
sys.exit(0 if video.get("status") == "playable" else 1)
PY
}

detail_video_url_ok() {
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

admin_video_status_visible() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
text = json.dumps(payload, ensure_ascii=False).lower()
has_section = bool(payload.get("video_summary") or payload.get("recent_ingestions"))
has_video_signal = "video" in text and any(term in text for term in ("playable", "present", "compatible", "success", "standardized", "video_url"))
sys.exit(0 if payload.get("success") is True and has_section and has_video_signal else 1)
PY
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] RESULT_ID=${RESULT_ID}"
echo "[info] CLASSROOM_ID=${CLASSROOM_ID}"
echo "[info] EXPECTED_VIDEO_URL=${EXPECTED_VIDEO_URL}"

HEALTH_OUT="$TMP_DIR/health.json"
STATUS="$(curl_status GET "${API_BASE_URL}/health" "$HEALTH_OUT")"
[ "$STATUS" = "200" ] && HEALTH_OK=true || HEALTH_OK=false
print_marker "PHASE35C_HEALTH_OK" "$HEALTH_OK"

STATIC_OUT="$TMP_DIR/static-video.bin"
STATUS="$(curl_status GET "${API_BASE_URL}${EXPECTED_VIDEO_URL}" "$STATIC_OUT")"
[ "$STATUS" = "200" ] && STATIC_VIDEO_OK=true || STATIC_VIDEO_OK=false
print_marker "PHASE35C_STATIC_VIDEO_OK" "$STATIC_VIDEO_OK"

TEACHER_COOKIE="$TMP_DIR/teacher.cookie"
TEACHER_LOGIN_OUT="$TMP_DIR/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$TEACHER_LOGIN_OUT" -c "$TEACHER_COOKIE" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
if [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_LOGIN_OUT"; then
  TEACHER_LOGIN_OK=true
else
  TEACHER_LOGIN_OK=false
fi
print_marker "PHASE35C_TEACHER_LOGIN_OK" "$TEACHER_LOGIN_OK"

DETAIL_OUT="$TMP_DIR/detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESULT_ID}" "$DETAIL_OUT" -b "$TEACHER_COOKIE")"
if [ "$STATUS" = "200" ] && json_success_ok "$DETAIL_OUT"; then
  TEACHER_DETAIL_OK=true
else
  TEACHER_DETAIL_OK=false
fi
print_marker "PHASE35C_TEACHER_DETAIL_OK" "$TEACHER_DETAIL_OK"

detail_video_playable "$DETAIL_OUT" && DETAIL_VIDEO_PLAYABLE=true || DETAIL_VIDEO_PLAYABLE=false
print_marker "PHASE35C_DETAIL_VIDEO_PLAYABLE" "$DETAIL_VIDEO_PLAYABLE"

detail_video_url_ok "$DETAIL_OUT" "$EXPECTED_VIDEO_URL" && DETAIL_VIDEO_URL_OK=true || DETAIL_VIDEO_URL_OK=false
print_marker "PHASE35C_DETAIL_VIDEO_URL_OK" "$DETAIL_VIDEO_URL_OK"

DASHBOARD_OUT="$TMP_DIR/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "$DASHBOARD_OUT" -b "$TEACHER_COOKIE")"
[ "$STATUS" = "200" ] && DASHBOARD_OK=true || DASHBOARD_OK=false
print_marker "PHASE35C_DASHBOARD_OK" "$DASHBOARD_OK"

if grep -q 'data-marker="video-area"' "$DASHBOARD_OUT"; then
  DASHBOARD_VIDEO_AREA_PRESENT=true
else
  DASHBOARD_VIDEO_AREA_PRESENT=false
fi
print_marker "PHASE35C_DASHBOARD_VIDEO_AREA_PRESENT" "$DASHBOARD_VIDEO_AREA_PRESENT"

REPORTS_OUT="$TMP_DIR/reports.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/reports?result_id=${RESULT_ID}" "$REPORTS_OUT" -b "$TEACHER_COOKIE")"
[ "$STATUS" = "200" ] && REPORTS_OK=true || REPORTS_OK=false
print_marker "PHASE35C_REPORTS_OK" "$REPORTS_OK"

ADMIN_COOKIE="$TMP_DIR/admin.cookie"
ADMIN_LOGIN_OUT="$TMP_DIR/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$ADMIN_LOGIN_OUT" -c "$ADMIN_COOKIE" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
if [ "$STATUS" = "200" ] && json_success_ok "$ADMIN_LOGIN_OUT"; then
  ADMIN_LOGIN_OK=true
else
  ADMIN_LOGIN_OK=false
fi
print_marker "PHASE35C_ADMIN_LOGIN_OK" "$ADMIN_LOGIN_OK"

ADMIN_INGESTION_PAGE_OUT="$TMP_DIR/admin-ingestion.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/ingestion" "$ADMIN_INGESTION_PAGE_OUT" -b "$ADMIN_COOKIE")"
[ "$STATUS" = "200" ] && ADMIN_INGESTION_PAGE_OK=true || ADMIN_INGESTION_PAGE_OK=false
print_marker "PHASE35C_ADMIN_INGESTION_PAGE_OK" "$ADMIN_INGESTION_PAGE_OK"

ADMIN_INGESTION_API_OUT="$TMP_DIR/admin-ingestion.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/ingestion?classroom_id=${CLASSROOM_ID}" "$ADMIN_INGESTION_API_OUT" -b "$ADMIN_COOKIE")"
if [ "$STATUS" = "200" ] && json_success_ok "$ADMIN_INGESTION_API_OUT"; then
  ADMIN_INGESTION_API_OK=true
else
  ADMIN_INGESTION_API_OK=false
fi
print_marker "PHASE35C_ADMIN_INGESTION_API_OK" "$ADMIN_INGESTION_API_OK"

admin_video_status_visible "$ADMIN_INGESTION_API_OUT" && ADMIN_VIDEO_STATUS_VISIBLE=true || ADMIN_VIDEO_STATUS_VISIBLE=false
print_marker "PHASE35C_ADMIN_VIDEO_STATUS_VISIBLE" "$ADMIN_VIDEO_STATUS_VISIBLE"

if [ "$HEALTH_OK" = "true" ] \
  && [ "$STATIC_VIDEO_OK" = "true" ] \
  && [ "$TEACHER_LOGIN_OK" = "true" ] \
  && [ "$TEACHER_DETAIL_OK" = "true" ] \
  && [ "$DETAIL_VIDEO_PLAYABLE" = "true" ] \
  && [ "$DETAIL_VIDEO_URL_OK" = "true" ] \
  && [ "$DASHBOARD_OK" = "true" ] \
  && [ "$DASHBOARD_VIDEO_AREA_PRESENT" = "true" ] \
  && [ "$REPORTS_OK" = "true" ] \
  && [ "$ADMIN_LOGIN_OK" = "true" ] \
  && [ "$ADMIN_INGESTION_PAGE_OK" = "true" ] \
  && [ "$ADMIN_INGESTION_API_OK" = "true" ] \
  && [ "$ADMIN_VIDEO_STATUS_VISIBLE" = "true" ]; then
  CLOUD_VIDEO_PLAYBACK_INTEGRATION_OK=true
else
  CLOUD_VIDEO_PLAYBACK_INTEGRATION_OK=false
fi
print_marker "PHASE35C_CLOUD_VIDEO_PLAYBACK_INTEGRATION_OK" "$CLOUD_VIDEO_PLAYBACK_INTEGRATION_OK"

