#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/db-backed-auth-$$"
USERNAME="${USERNAME:-teacher_reg_$(date +%s)_$$}"
PASSWORD="${PASSWORD:-Register12345}"
REGISTER_EMAIL="${REGISTER_EMAIL:-}"
REGISTER_CODE="${REGISTER_CODE:-}"

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
  curl -sS -o "$output" -w "%{http_code}" -X "$method" --max-time 25 "$@" "$url" 2>/dev/null || echo "000"
}

json_check() {
  local file="$1"
  local check="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$check" "$USERNAME" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
check = sys.argv[2]
username = sys.argv[3]
user = payload.get("user") or {}
checks = {
    "success": payload.get("success") is True,
    "username": user.get("username") == username,
    "teacher_role": user.get("role") == "teacher",
    "redirect_login": payload.get("redirect_to") == "/login",
}
sys.exit(0 if checks.get(check) else 1)
PY
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] USERNAME=${USERNAME}"
echo "[info] CLASSROOM_ID=${CLASSROOM_ID}"
echo "[info] password and verification code are intentionally not printed"

REGISTER_PAGE="$TMP_DIR/register-page.html"
STATUS="$(curl_status GET "${API_BASE_URL}/register" "$REGISTER_PAGE")"
[ "$STATUS" = "200" ] && grep -q "db-backed-register-page" "$REGISTER_PAGE" && grep -q "send-register-code" "$REGISTER_PAGE" && REGISTER_PAGE_OK=true || REGISTER_PAGE_OK=false

INVALID_EMAIL_JSON="$TMP_DIR/invalid-email.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/send-register-code" "$INVALID_EMAIL_JSON" -H "Content-Type: application/json" --data '{"email":"not-qq@example.com"}')"
[ "$STATUS" = "422" ] && INVALID_EMAIL_REJECTED=true || INVALID_EMAIL_REJECTED=false

NO_CODE_JSON="$TMP_DIR/no-code.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/register" "$NO_CODE_JSON" -H "Content-Type: application/json" --data "{\"username\":\"${USERNAME}\",\"email\":\"${USERNAME}@qq.com\",\"password\":\"${PASSWORD}\",\"confirm_password\":\"${PASSWORD}\",\"verification_code\":\"000000\"}")"
[ "$STATUS" = "422" ] && REGISTER_REQUIRES_VALID_CODE=true || REGISTER_REQUIRES_VALID_CODE=false

SEND_CODE_ATTEMPTED=false
SEND_CODE_OK=false
if [ -n "$REGISTER_EMAIL" ] && [ -z "$REGISTER_CODE" ]; then
  SEND_CODE_ATTEMPTED=true
  SEND_CODE_JSON="$TMP_DIR/send-code.json"
  STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/send-register-code" "$SEND_CODE_JSON" -H "Content-Type: application/json" --data "{\"email\":\"${REGISTER_EMAIL}\"}")"
  [ "$STATUS" = "200" ] && SEND_CODE_OK=true || SEND_CODE_OK=false
fi

REGISTER_API_OK=false
LOGIN_API_OK=false
TEACHER_PAGE_AUTH_OK=false
if [ -n "$REGISTER_EMAIL" ] && [ -n "$REGISTER_CODE" ]; then
  REGISTER_JSON="$TMP_DIR/register.json"
  STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/register" "$REGISTER_JSON" -H "Content-Type: application/json" --data "{\"username\":\"${USERNAME}\",\"email\":\"${REGISTER_EMAIL}\",\"password\":\"${PASSWORD}\",\"confirm_password\":\"${PASSWORD}\",\"verification_code\":\"${REGISTER_CODE}\",\"display_name\":\"${USERNAME}\",\"classroom_id\":\"${CLASSROOM_ID}\"}")"
  [ "$STATUS" = "200" ] && json_check "$REGISTER_JSON" "success" && json_check "$REGISTER_JSON" "username" && json_check "$REGISTER_JSON" "teacher_role" && json_check "$REGISTER_JSON" "redirect_login" && REGISTER_API_OK=true || REGISTER_API_OK=false

  LOGIN_COOKIE="$TMP_DIR/login.cookie"
  LOGIN_JSON="$TMP_DIR/login.json"
  STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$LOGIN_JSON" -c "$LOGIN_COOKIE" -H "Content-Type: application/json" --data "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}")"
  [ "$STATUS" = "200" ] && json_check "$LOGIN_JSON" "success" && json_check "$LOGIN_JSON" "username" && json_check "$LOGIN_JSON" "teacher_role" && LOGIN_API_OK=true || LOGIN_API_OK=false

  TEACHER_PAGE="$TMP_DIR/teacher.html"
  STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "$TEACHER_PAGE" -b "$LOGIN_COOKIE")"
  [ "$STATUS" = "200" ] && TEACHER_PAGE_AUTH_OK=true || TEACHER_PAGE_AUTH_OK=false
fi

print_marker "DB_AUTH_REGISTER_PAGE_OK" "$REGISTER_PAGE_OK"
print_marker "DB_AUTH_INVALID_EMAIL_REJECTED" "$INVALID_EMAIL_REJECTED"
print_marker "DB_AUTH_REGISTER_REQUIRES_VALID_CODE" "$REGISTER_REQUIRES_VALID_CODE"
print_marker "DB_AUTH_SEND_CODE_ATTEMPTED" "$SEND_CODE_ATTEMPTED"
print_marker "DB_AUTH_SEND_CODE_OK" "$SEND_CODE_OK"
print_marker "DB_AUTH_REGISTER_API_OK" "$REGISTER_API_OK"
print_marker "DB_AUTH_LOGIN_API_OK" "$LOGIN_API_OK"
print_marker "DB_AUTH_TEACHER_PAGE_AUTH_OK" "$TEACHER_PAGE_AUTH_OK"

if [ "$REGISTER_PAGE_OK" = "true" ] \
  && [ "$INVALID_EMAIL_REJECTED" = "true" ] \
  && [ "$REGISTER_REQUIRES_VALID_CODE" = "true" ]; then
  DB_BACKED_REGISTER_SECURITY_READY=true
else
  DB_BACKED_REGISTER_SECURITY_READY=false
fi

if [ "$REGISTER_API_OK" = "true" ] \
  && [ "$LOGIN_API_OK" = "true" ] \
  && [ "$TEACHER_PAGE_AUTH_OK" = "true" ]; then
  DB_BACKED_REGISTER_LOGIN_OK=true
else
  DB_BACKED_REGISTER_LOGIN_OK=false
fi

print_marker "DB_BACKED_REGISTER_SECURITY_READY" "$DB_BACKED_REGISTER_SECURITY_READY"
print_marker "DB_BACKED_REGISTER_LOGIN_OK" "$DB_BACKED_REGISTER_LOGIN_OK"
