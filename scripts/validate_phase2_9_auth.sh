#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase29-validation-$$"

mkdir -p "${TMP_DIR}"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] RESULT_ID=${RESULT_ID}"
echo "[info] CLASSROOM_ID=${CLASSROOM_ID}"

curl_status() {
  local method="$1"
  local url="$2"
  local output="$3"
  shift 3
  curl -sS -o "${output}" -w "%{http_code}" -X "${method}" "$@" "${url}"
}

print_marker() {
  echo "$1=$2"
}

all_true_marker() {
  local name="$1"
  shift
  local ok="true"
  for value in "$@"; do
    if [ "${value}" != "true" ]; then
      ok="false"
    fi
  done
  print_marker "${name}" "${ok}"
}

json_success_ok() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); sys.exit(0 if p.get("success") is True else 1)' "$1"
}

json_redirect_ok() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); sys.exit(0 if p.get("redirect_to")==sys.argv[2] else 1)' "$1" "$2"
}

json_teacher_classroom_filter_ok() {
  python -c '
import json,sys
p=json.load(open(sys.argv[1],encoding="utf-8"))
items=p.get("items") or []
expected=sys.argv[2]
bad=[item.get("classroom_id") for item in items if item.get("classroom_id") != expected]
sys.exit(0 if p.get("success") is True and not bad else 1)
' "$1" "$2"
}

echo
echo "[step] login page and anonymous protection"
LOGIN_HTML="${TMP_DIR}/login.html"
STATUS="$(curl_status GET "${API_BASE_URL}/login" "${LOGIN_HTML}")"
[ "${STATUS}" = "200" ] && LOGIN_200=true || LOGIN_200=false
grep -q 'data-marker="phase29-login-page"' "${LOGIN_HTML}" && LOGIN_MARKER=true || LOGIN_MARKER=false
all_true_marker "PHASE29_LOGIN_PAGE_OK" "${LOGIN_200}" "${LOGIN_MARKER}"

ANON_TEACHER="${TMP_DIR}/anon-teacher.html"
ANON_ADMIN="${TMP_DIR}/anon-admin.html"
STATUS_TEACHER_ANON="$(curl_status GET "${API_BASE_URL}/teacher" "${ANON_TEACHER}")"
STATUS_ADMIN_ANON="$(curl_status GET "${API_BASE_URL}/admin" "${ANON_ADMIN}")"
[ "${STATUS_TEACHER_ANON}" = "302" ] && TEACHER_BLOCK=true || TEACHER_BLOCK=false
[ "${STATUS_ADMIN_ANON}" = "302" ] && ADMIN_BLOCK=true || ADMIN_BLOCK=false
all_true_marker "PHASE29_ANON_PAGE_BLOCKED" "${TEACHER_BLOCK}" "${ADMIN_BLOCK}"

ADMIN_API_ANON="${TMP_DIR}/anon-admin-api.json"
STATUS_ADMIN_API_ANON="$(curl_status GET "${API_BASE_URL}/api/admin/overview" "${ADMIN_API_ANON}")"
[ "${STATUS_ADMIN_API_ANON}" = "401" ] && ADMIN_API_PROTECTED=true || ADMIN_API_PROTECTED=false
print_marker "PHASE29_ADMIN_API_PROTECTED" "${ADMIN_API_PROTECTED}"

echo
echo "[step] teacher login and permissions"
TEACHER_COOKIE="${TMP_DIR}/teacher.cookie"
TEACHER_LOGIN_JSON="${TMP_DIR}/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${TEACHER_LOGIN_JSON}" -c "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "${STATUS}" = "200" ] && json_redirect_ok "${TEACHER_LOGIN_JSON}" "/teacher" && TEACHER_LOGIN=true || TEACHER_LOGIN=false
print_marker "PHASE29_TEACHER_LOGIN_OK" "${TEACHER_LOGIN}"

TEACHER_PAGE="${TMP_DIR}/teacher.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "${TEACHER_PAGE}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q 'data-marker="teacher-home-page"' "${TEACHER_PAGE}" && TEACHER_PAGE_OK=true || TEACHER_PAGE_OK=false
print_marker "PHASE29_TEACHER_PAGE_OK" "${TEACHER_PAGE_OK}"

TEACHER_ADMIN_PAGE="${TMP_DIR}/teacher-admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${TEACHER_ADMIN_PAGE}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "403" ] && TEACHER_ADMIN_BLOCKED=true || TEACHER_ADMIN_BLOCKED=false
print_marker "PHASE29_TEACHER_ADMIN_BLOCKED" "${TEACHER_ADMIN_BLOCKED}"

TEACHER_ADMIN_API="${TMP_DIR}/teacher-admin-api.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/overview" "${TEACHER_ADMIN_API}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "403" ] && TEACHER_ADMIN_API_BLOCKED=true || TEACHER_ADMIN_API_BLOCKED=false
print_marker "PHASE29_TEACHER_ADMIN_API_BLOCKED" "${TEACHER_ADMIN_API_BLOCKED}"

TEACHER_RESULTS_JSON="${TMP_DIR}/teacher-results.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results?limit=100&days=all" "${TEACHER_RESULTS_JSON}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && json_teacher_classroom_filter_ok "${TEACHER_RESULTS_JSON}" "${CLASSROOM_ID}" && TEACHER_FILTER=true || TEACHER_FILTER=false
print_marker "PHASE29_TEACHER_CLASSROOM_FILTER_OK" "${TEACHER_FILTER}"

ME_JSON="${TMP_DIR}/me.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/auth/me" "${ME_JSON}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && json_success_ok "${ME_JSON}" && AUTH_ME=true || AUTH_ME=false
print_marker "PHASE29_AUTH_ME_OK" "${AUTH_ME}"

LOGOUT_JSON="${TMP_DIR}/logout.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/logout" "${LOGOUT_JSON}" -b "${TEACHER_COOKIE}" -c "${TEACHER_COOKIE}")"
AFTER_LOGOUT_STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "${TMP_DIR}/after-logout.html" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && [ "${AFTER_LOGOUT_STATUS}" = "302" ] && LOGOUT_OK=true || LOGOUT_OK=false
print_marker "PHASE29_LOGOUT_OK" "${LOGOUT_OK}"

echo
echo "[step] admin login and regressions"
ADMIN_COOKIE="${TMP_DIR}/admin.cookie"
ADMIN_LOGIN_JSON="${TMP_DIR}/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${ADMIN_LOGIN_JSON}" -c "${ADMIN_COOKIE}" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "${STATUS}" = "200" ] && json_redirect_ok "${ADMIN_LOGIN_JSON}" "/admin" && ADMIN_LOGIN=true || ADMIN_LOGIN=false
print_marker "PHASE29_ADMIN_LOGIN_OK" "${ADMIN_LOGIN}"

ADMIN_PAGE="${TMP_DIR}/admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${ADMIN_PAGE}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q 'data-marker="admin-overview-page"' "${ADMIN_PAGE}" && ADMIN_PAGE_OK=true || ADMIN_PAGE_OK=false
print_marker "PHASE29_ADMIN_PAGE_OK" "${ADMIN_PAGE_OK}"

INGESTION_PAGE="${TMP_DIR}/ingestion.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/ingestion" "${INGESTION_PAGE}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q 'data-marker="admin-ingestion-page"' "${INGESTION_PAGE}" && INGESTION_OK=true || INGESTION_OK=false
print_marker "PHASE29_INGESTION_AFTER_LOGIN_OK" "${INGESTION_OK}"

DASHBOARD_PAGE="${TMP_DIR}/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD_PAGE}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q 'data-marker="teacher-analysis-center"' "${DASHBOARD_PAGE}" && DASHBOARD_OK=true || DASHBOARD_OK=false

TEACHER_RESULTS_PAGE="${TMP_DIR}/teacher-results.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/results" "${TEACHER_RESULTS_PAGE}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q 'data-marker="teacher-results-page"' "${TEACHER_RESULTS_PAGE}" && TEACHER_RESULTS_OK=true || TEACHER_RESULTS_OK=false

LATEST_JSON="${TMP_DIR}/latest.json"
RECENT_JSON="${TMP_DIR}/recent.json"
STATUS_LATEST="$(curl_status GET "${API_BASE_URL}/api/latest-interaction-result" "${LATEST_JSON}")"
STATUS_RECENT="$(curl_status GET "${API_BASE_URL}/api/recent-interaction-results?limit=5" "${RECENT_JSON}")"
[ "${STATUS_LATEST}" = "200" ] && LATEST_OK=true || LATEST_OK=false
[ "${STATUS_RECENT}" = "200" ] && RECENT_OK=true || RECENT_OK=false

UPLOAD_JSON="${TMP_DIR}/upload-open.json"
STATUS_UPLOAD="$(curl_status POST "${API_BASE_URL}/api/interaction-results" "${UPLOAD_JSON}" -H "Content-Type: application/json" --data '{}')"
if [ "${STATUS_UPLOAD}" != "401" ] && [ "${STATUS_UPLOAD}" != "403" ]; then UPLOAD_OPEN=true; else UPLOAD_OPEN=false; fi
print_marker "PHASE29_UPLOAD_API_STILL_OPEN" "${UPLOAD_OPEN}"

all_true_marker "PHASE29_REGRESSION_OK" "${DASHBOARD_OK}" "${TEACHER_RESULTS_OK}" "${LATEST_OK}" "${RECENT_OK}" "${INGESTION_OK}"

echo
echo "[done] Phase 2.9 auth validation completed"
