#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
FINAL_ID="${FINAL_ID:-phase314_asr_full_classroom_sav_20200908_17}"
TMP_DIR="${TMPDIR:-/tmp}/phase319-remove-trends-$$"

mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

print_marker() {
  echo "$1=$2"
}

curl_status() {
  local method="$1"
  local url="$2"
  local output="$3"
  shift 3
  curl -sS -o "$output" -w "%{http_code}" -X "$method" --max-time 25 "$@" "$url" 2>/dev/null || echo "000"
}

json_success_ok() {
  local file="$1"
  python - "$file" <<'PY' 2>/dev/null
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if payload.get("success") is True else 1)
PY
}

html_has_no_trend_link() {
  local file="$1"
  local link="$2"
  [ -f "$file" ] && ! grep -q "$link" "$file"
}

redirects_to() {
  local header_file="$1"
  local target="$2"
  grep -qi "^[Ll]ocation: ${target}" "$header_file"
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] FINAL_ID=${FINAL_ID}"

TEACHER_COOKIE="$TMP_DIR/teacher.cookie"
ADMIN_COOKIE="$TMP_DIR/admin.cookie"

TEACHER_LOGIN="$TMP_DIR/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$TEACHER_LOGIN" -c "$TEACHER_COOKIE" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "$STATUS" = "200" ] && json_success_ok "$TEACHER_LOGIN" && TEACHER_LOGIN_OK=true || TEACHER_LOGIN_OK=false

ADMIN_LOGIN="$TMP_DIR/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$ADMIN_LOGIN" -c "$ADMIN_COOKIE" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "$STATUS" = "200" ] && json_success_ok "$ADMIN_LOGIN" && ADMIN_LOGIN_OK=true || ADMIN_LOGIN_OK=false

TEACHER_HOME="$TMP_DIR/teacher-home.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "$TEACHER_HOME" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && html_has_no_trend_link "$TEACHER_HOME" "/teacher/trends" && TEACHER_HOME_NO_TREND_LINK=true || TEACHER_HOME_NO_TREND_LINK=false

DASHBOARD="$TMP_DIR/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${FINAL_ID}" "$DASHBOARD" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && html_has_no_trend_link "$DASHBOARD" "/teacher/trends" && DASHBOARD_NO_TREND_LINK=true || DASHBOARD_NO_TREND_LINK=false

ADMIN_HOME="$TMP_DIR/admin-home.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "$ADMIN_HOME" -b "$ADMIN_COOKIE")"
[ "$ADMIN_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && html_has_no_trend_link "$ADMIN_HOME" "/admin/trends" && ADMIN_HOME_NO_TREND_LINK=true || ADMIN_HOME_NO_TREND_LINK=false

TEACHER_TRENDS_BODY="$TMP_DIR/teacher-trends.html"
TEACHER_TRENDS_HEADERS="$TMP_DIR/teacher-trends.headers"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/trends" "$TEACHER_TRENDS_BODY" -D "$TEACHER_TRENDS_HEADERS" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "302" ] && redirects_to "$TEACHER_TRENDS_HEADERS" "/teacher/reports" && TEACHER_TRENDS_REDIRECTS=true || TEACHER_TRENDS_REDIRECTS=false

ADMIN_TRENDS_BODY="$TMP_DIR/admin-trends.html"
ADMIN_TRENDS_HEADERS="$TMP_DIR/admin-trends.headers"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/trends" "$ADMIN_TRENDS_BODY" -D "$ADMIN_TRENDS_HEADERS" -b "$ADMIN_COOKIE")"
[ "$ADMIN_LOGIN_OK" = "true" ] && [ "$STATUS" = "302" ] && redirects_to "$ADMIN_TRENDS_HEADERS" "/admin/results" && ADMIN_TRENDS_REDIRECTS=true || ADMIN_TRENDS_REDIRECTS=false

TEACHER_TRENDS_API="$TMP_DIR/teacher-trends-api.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?data_source=real&limit=1" "$TEACHER_TRENDS_API" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_TRENDS_API" && TEACHER_TRENDS_API_PRESERVED=true || TEACHER_TRENDS_API_PRESERVED=false

ADMIN_TRENDS_API="$TMP_DIR/admin-trends-api.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/trends?data_source=real&limit=1" "$ADMIN_TRENDS_API" -b "$ADMIN_COOKIE")"
[ "$ADMIN_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$ADMIN_TRENDS_API" && ADMIN_TRENDS_API_PRESERVED=true || ADMIN_TRENDS_API_PRESERVED=false

print_marker "PHASE319_TEACHER_LOGIN_OK" "$TEACHER_LOGIN_OK"
print_marker "PHASE319_ADMIN_LOGIN_OK" "$ADMIN_LOGIN_OK"
print_marker "PHASE319_TEACHER_HOME_NO_TREND_LINK" "$TEACHER_HOME_NO_TREND_LINK"
print_marker "PHASE319_DASHBOARD_NO_TREND_LINK" "$DASHBOARD_NO_TREND_LINK"
print_marker "PHASE319_ADMIN_HOME_NO_TREND_LINK" "$ADMIN_HOME_NO_TREND_LINK"
print_marker "PHASE319_TEACHER_TRENDS_REDIRECTS" "$TEACHER_TRENDS_REDIRECTS"
print_marker "PHASE319_ADMIN_TRENDS_REDIRECTS" "$ADMIN_TRENDS_REDIRECTS"
print_marker "PHASE319_TREND_APIS_PRESERVED" "$([ "$TEACHER_TRENDS_API_PRESERVED" = "true" ] && [ "$ADMIN_TRENDS_API_PRESERVED" = "true" ] && echo true || echo false)"

if [ "$TEACHER_LOGIN_OK" = "true" ] \
  && [ "$ADMIN_LOGIN_OK" = "true" ] \
  && [ "$TEACHER_HOME_NO_TREND_LINK" = "true" ] \
  && [ "$DASHBOARD_NO_TREND_LINK" = "true" ] \
  && [ "$ADMIN_HOME_NO_TREND_LINK" = "true" ] \
  && [ "$TEACHER_TRENDS_REDIRECTS" = "true" ] \
  && [ "$ADMIN_TRENDS_REDIRECTS" = "true" ]; then
  FRONTEND_TRENDS_REMOVED=true
else
  FRONTEND_TRENDS_REMOVED=false
fi

print_marker "PHASE319_FRONTEND_TRENDS_REMOVED" "$FRONTEND_TRENDS_REMOVED"
