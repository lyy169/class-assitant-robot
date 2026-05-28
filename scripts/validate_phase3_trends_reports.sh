#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase30-validation-$$"

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

print_marker() { echo "$1=$2"; }

all_true_marker() {
  local name="$1"; shift
  local ok="true"
  for value in "$@"; do
    [ "${value}" = "true" ] || ok="false"
  done
  print_marker "${name}" "${ok}"
}

json_key_success() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); sys.exit(0 if p.get("success") is True and all(k in p for k in sys.argv[2:]) else 1)' "$@"
}

json_filter_source() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); sys.exit(0 if (p.get("filters") or {}).get("data_source")==sys.argv[2] else 1)' "$1" "$2"
}

json_ai_optional_ok() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); ai=p.get("ai_summary") or {}; sys.exit(0 if ai.get("status") in {"not_configured","success","failed"} else 1)' "$1"
}

echo
echo "[step] teacher login"
TEACHER_COOKIE="${TMP_DIR}/teacher.cookie"
TEACHER_LOGIN="${TMP_DIR}/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${TEACHER_LOGIN}" -c "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "${STATUS}" = "200" ] && TEACHER_LOGIN_OK=true || TEACHER_LOGIN_OK=false
print_marker "PHASE30_TEACHER_LOGIN_OK" "${TEACHER_LOGIN_OK}"

echo
echo "[step] teacher trends"
TEACHER_TRENDS_HTML="${TMP_DIR}/teacher-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/trends" "${TEACHER_TRENDS_HTML}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q 'data-marker="phase30-teacher-trends-page"' "${TEACHER_TRENDS_HTML}" && TRENDS_PAGE_OK=true || TRENDS_PAGE_OK=false
print_marker "PHASE30_TEACHER_TRENDS_PAGE_OK" "${TRENDS_PAGE_OK}"

TEACHER_TRENDS_JSON="${TMP_DIR}/teacher-trends.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?limit=20" "${TEACHER_TRENDS_JSON}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && json_key_success "${TEACHER_TRENDS_JSON}" filters overview series stage_distribution risk_lessons recommendations data_quality && TRENDS_API_OK=true || TRENDS_API_OK=false
print_marker "PHASE30_TEACHER_TRENDS_API_OK" "${TRENDS_API_OK}"
json_filter_source "${TEACHER_TRENDS_JSON}" "real" && DEFAULT_REAL_OK=true || DEFAULT_REAL_OK=false
print_marker "PHASE30_DATA_SOURCE_DEFAULT_REAL_OK" "${DEFAULT_REAL_OK}"

DEMO_JSON="${TMP_DIR}/teacher-trends-demo.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?data_source=demo&limit=20" "${DEMO_JSON}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && json_filter_source "${DEMO_JSON}" "demo" && DEMO_FILTER_OK=true || DEMO_FILTER_OK=false
print_marker "PHASE30_DEMO_FILTER_OK" "${DEMO_FILTER_OK}"

echo
echo "[step] teacher reports"
REPORTS_HTML="${TMP_DIR}/teacher-reports.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/reports" "${REPORTS_HTML}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q 'data-marker="phase30-teacher-reports-page"' "${REPORTS_HTML}" && REPORTS_PAGE_OK=true || REPORTS_PAGE_OK=false
print_marker "PHASE30_TEACHER_REPORTS_PAGE_OK" "${REPORTS_PAGE_OK}"

REPORTS_JSON="${TMP_DIR}/teacher-reports.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports?limit=20" "${REPORTS_JSON}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && json_key_success "${REPORTS_JSON}" filters items && REPORTS_API_OK=true || REPORTS_API_OK=false
print_marker "PHASE30_TEACHER_REPORTS_API_OK" "${REPORTS_API_OK}"

DETAIL_JSON="${TMP_DIR}/report-detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports/detail?result_id=${RESULT_ID}" "${DETAIL_JSON}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && json_key_success "${DETAIL_JSON}" report && REPORT_DETAIL_OK=true || REPORT_DETAIL_OK=false
print_marker "PHASE30_TEACHER_REPORT_DETAIL_API_OK" "${REPORT_DETAIL_OK}"

AI_JSON="${TMP_DIR}/ai-summary.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/teacher/reports/ai-summary" "${AI_JSON}" -b "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data "{\"result_id\":\"${RESULT_ID}\"}")"
[ "${STATUS}" = "200" ] && json_ai_optional_ok "${AI_JSON}" && AI_OPTIONAL_OK=true || AI_OPTIONAL_OK=false
print_marker "PHASE30_AI_OPTIONAL_OK" "${AI_OPTIONAL_OK}"

echo
echo "[step] admin trends"
ADMIN_COOKIE="${TMP_DIR}/admin.cookie"
ADMIN_LOGIN="${TMP_DIR}/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${ADMIN_LOGIN}" -c "${ADMIN_COOKIE}" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "${STATUS}" = "200" ] && ADMIN_LOGIN_OK=true || ADMIN_LOGIN_OK=false
print_marker "PHASE30_ADMIN_LOGIN_OK" "${ADMIN_LOGIN_OK}"

ADMIN_TRENDS_HTML="${TMP_DIR}/admin-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/trends" "${ADMIN_TRENDS_HTML}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q 'data-marker="phase30-admin-trends-page"' "${ADMIN_TRENDS_HTML}" && ADMIN_TRENDS_PAGE_OK=true || ADMIN_TRENDS_PAGE_OK=false
print_marker "PHASE30_ADMIN_TRENDS_PAGE_OK" "${ADMIN_TRENDS_PAGE_OK}"

ADMIN_TRENDS_JSON="${TMP_DIR}/admin-trends.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/trends?limit=30" "${ADMIN_TRENDS_JSON}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && json_key_success "${ADMIN_TRENDS_JSON}" filters overview classroom_rankings teacher_activity risk_lessons recent_reports data_quality && ADMIN_TRENDS_API_OK=true || ADMIN_TRENDS_API_OK=false
print_marker "PHASE30_ADMIN_TRENDS_API_OK" "${ADMIN_TRENDS_API_OK}"

echo
echo "[step] regressions"
AUTH_ME="${TMP_DIR}/auth-me.json"
STATUS_ME="$(curl_status GET "${API_BASE_URL}/api/auth/me" "${AUTH_ME}" -b "${ADMIN_COOKIE}")"
[ "${STATUS_ME}" = "200" ] && AUTH_REGRESSION_OK=true || AUTH_REGRESSION_OK=false
print_marker "PHASE30_AUTH_REGRESSION_OK" "${AUTH_REGRESSION_OK}"

INGESTION_HTML="${TMP_DIR}/ingestion.html"
STATUS_INGESTION="$(curl_status GET "${API_BASE_URL}/admin/ingestion" "${INGESTION_HTML}" -b "${ADMIN_COOKIE}")"
[ "${STATUS_INGESTION}" = "200" ] && grep -q 'data-marker="admin-ingestion-page"' "${INGESTION_HTML}" && INGESTION_OK=true || INGESTION_OK=false
print_marker "PHASE30_INGESTION_REGRESSION_OK" "${INGESTION_OK}"

all_true_marker "PHASE30_REGRESSION_OK" "${TEACHER_LOGIN_OK}" "${TRENDS_PAGE_OK}" "${TRENDS_API_OK}" "${REPORTS_PAGE_OK}" "${REPORTS_API_OK}" "${REPORT_DETAIL_OK}" "${ADMIN_LOGIN_OK}" "${ADMIN_TRENDS_PAGE_OK}" "${ADMIN_TRENDS_API_OK}" "${DEFAULT_REAL_OK}" "${DEMO_FILTER_OK}" "${AI_OPTIONAL_OK}" "${AUTH_REGRESSION_OK}" "${INGESTION_OK}"

echo
echo "[done] Phase 3.0 trends and reports validation completed"
