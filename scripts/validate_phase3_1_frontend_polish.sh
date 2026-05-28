#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase31-validation-$$"

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

marker() { echo "$1=$2"; }

all_true() {
  local name="$1"; shift
  local ok="true"
  for value in "$@"; do
    [ "${value}" = "true" ] || ok="false"
  done
  marker "${name}" "${ok}"
}

json_success() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); sys.exit(0 if p.get("success") is True else 1)' "$1"
}

echo
echo "[step] login page"
LOGIN_HTML="${TMP_DIR}/login.html"
STATUS="$(curl_status GET "${API_BASE_URL}/login" "${LOGIN_HTML}")"
[ "${STATUS}" = "200" ] && grep -q "智能课堂行为分析与教学反馈平台" "${LOGIN_HTML}" && LOGIN_OK=true || LOGIN_OK=false
marker "PHASE31_LOGIN_PAGE_OK" "${LOGIN_OK}"

echo
echo "[step] teacher login and pages"
TEACHER_COOKIE="${TMP_DIR}/teacher.cookie"
TEACHER_LOGIN="${TMP_DIR}/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${TEACHER_LOGIN}" -c "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "${STATUS}" = "200" ] && json_success "${TEACHER_LOGIN}" && TEACHER_LOGIN_OK=true || TEACHER_LOGIN_OK=false
marker "PHASE31_TEACHER_LOGIN_OK" "${TEACHER_LOGIN_OK}"

TEACHER_HOME="${TMP_DIR}/teacher.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "${TEACHER_HOME}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "教学反馈工作台" "${TEACHER_HOME}" && TEACHER_HOME_OK=true || TEACHER_HOME_OK=false
marker "PHASE31_TEACHER_HOME_OK" "${TEACHER_HOME_OK}"

DASHBOARD="${TMP_DIR}/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "课堂分析" "${DASHBOARD}" && grep -q 'data-marker="teacher-analysis-center"' "${DASHBOARD}" && DASHBOARD_OK=true || DASHBOARD_OK=false
marker "PHASE31_DASHBOARD_OK" "${DASHBOARD_OK}"

TRENDS="${TMP_DIR}/teacher-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/trends" "${TRENDS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "趋势洞察" "${TRENDS}" && TRENDS_OK=true || TRENDS_OK=false
marker "PHASE31_TEACHER_TRENDS_OK" "${TRENDS_OK}"

REPORTS="${TMP_DIR}/teacher-reports.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/reports" "${REPORTS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "报告中心" "${REPORTS}" && REPORTS_OK=true || REPORTS_OK=false
marker "PHASE31_TEACHER_REPORTS_OK" "${REPORTS_OK}"

echo
echo "[step] admin login and pages"
ADMIN_COOKIE="${TMP_DIR}/admin.cookie"
ADMIN_LOGIN="${TMP_DIR}/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${ADMIN_LOGIN}" -c "${ADMIN_COOKIE}" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "${STATUS}" = "200" ] && json_success "${ADMIN_LOGIN}" && ADMIN_LOGIN_OK=true || ADMIN_LOGIN_OK=false
marker "PHASE31_ADMIN_LOGIN_OK" "${ADMIN_LOGIN_OK}"

ADMIN_HOME="${TMP_DIR}/admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${ADMIN_HOME}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "平台总览" "${ADMIN_HOME}" && ADMIN_HOME_OK=true || ADMIN_HOME_OK=false
marker "PHASE31_ADMIN_HOME_OK" "${ADMIN_HOME_OK}"

ADMIN_TRENDS="${TMP_DIR}/admin-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/trends" "${ADMIN_TRENDS}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "平台趋势洞察" "${ADMIN_TRENDS}" && ADMIN_TRENDS_OK=true || ADMIN_TRENDS_OK=false
marker "PHASE31_ADMIN_TRENDS_OK" "${ADMIN_TRENDS_OK}"

ADMIN_INGESTION="${TMP_DIR}/admin-ingestion.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/ingestion" "${ADMIN_INGESTION}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "三端数据接入状态" "${ADMIN_INGESTION}" && ADMIN_INGESTION_OK=true || ADMIN_INGESTION_OK=false
marker "PHASE31_ADMIN_INGESTION_OK" "${ADMIN_INGESTION_OK}"

TEACHER_ADMIN="${TMP_DIR}/teacher-admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${TEACHER_ADMIN}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "403" ] && AUTH_OK=true || AUTH_OK=false
marker "PHASE31_AUTH_REGRESSION_OK" "${AUTH_OK}"

echo
echo "[step] phase 3.0 API regression"
TRENDS_JSON="${TMP_DIR}/trends.json"
REPORTS_JSON="${TMP_DIR}/reports.json"
DETAIL_JSON="${TMP_DIR}/detail.json"
AI_JSON="${TMP_DIR}/ai.json"
STATUS_TRENDS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?limit=20" "${TRENDS_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_REPORTS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports?limit=20" "${REPORTS_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_DETAIL="$(curl_status GET "${API_BASE_URL}/api/teacher/reports/detail?result_id=${RESULT_ID}" "${DETAIL_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_AI="$(curl_status POST "${API_BASE_URL}/api/teacher/reports/ai-summary" "${AI_JSON}" -b "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data "{\"result_id\":\"${RESULT_ID}\"}")"
[ "${STATUS_TRENDS}" = "200" ] && json_success "${TRENDS_JSON}" && P30_TRENDS=true || P30_TRENDS=false
[ "${STATUS_REPORTS}" = "200" ] && json_success "${REPORTS_JSON}" && P30_REPORTS=true || P30_REPORTS=false
[ "${STATUS_DETAIL}" = "200" ] && json_success "${DETAIL_JSON}" && P30_DETAIL=true || P30_DETAIL=false
[ "${STATUS_AI}" = "200" ] && json_success "${AI_JSON}" && P30_AI=true || P30_AI=false
all_true "PHASE31_PHASE30_REGRESSION_OK" "${P30_TRENDS}" "${P30_REPORTS}" "${P30_DETAIL}" "${P30_AI}"

grep -q "教学首页" "${TEACHER_HOME}" && grep -q "课堂分析" "${DASHBOARD}" && grep -q "报告中心" "${REPORTS}" && grep -q "接入状态" "${ADMIN_INGESTION}" && VISUAL_OK=true || VISUAL_OK=false
marker "PHASE31_VISUAL_STRUCTURE_OK" "${VISUAL_OK}"

all_true "PHASE31_REGRESSION_OK" "${LOGIN_OK}" "${TEACHER_LOGIN_OK}" "${ADMIN_LOGIN_OK}" "${TEACHER_HOME_OK}" "${DASHBOARD_OK}" "${TRENDS_OK}" "${REPORTS_OK}" "${ADMIN_HOME_OK}" "${ADMIN_TRENDS_OK}" "${ADMIN_INGESTION_OK}" "${AUTH_OK}" "${P30_TRENDS}" "${P30_REPORTS}" "${P30_DETAIL}" "${P30_AI}" "${VISUAL_OK}"

echo
echo "[done] Phase 3.1 frontend polish validation completed"
