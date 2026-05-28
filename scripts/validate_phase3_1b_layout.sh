#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
TMP_DIR="${TMPDIR:-/tmp}/phase31b-validation-$$"

mkdir -p "${TMP_DIR}"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] RESULT_ID=${RESULT_ID}"

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
echo "[step] login"
LOGIN_HTML="${TMP_DIR}/login.html"
STATUS="$(curl_status GET "${API_BASE_URL}/login" "${LOGIN_HTML}")"
[ "${STATUS}" = "200" ] && grep -q "智能课堂行为分析与教学反馈平台" "${LOGIN_HTML}" && LOGIN_OK=true || LOGIN_OK=false
marker "PHASE31B_LOGIN_OK" "${LOGIN_OK}"

echo
echo "[step] teacher pages"
TEACHER_COOKIE="${TMP_DIR}/teacher.cookie"
TEACHER_LOGIN="${TMP_DIR}/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${TEACHER_LOGIN}" -c "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "${STATUS}" = "200" ] && json_success "${TEACHER_LOGIN}" && TEACHER_LOGIN_OK=true || TEACHER_LOGIN_OK=false

TEACHER_HOME="${TMP_DIR}/teacher.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "${TEACHER_HOME}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "复盘 Spotlight" "${TEACHER_HOME}" && grep -q "教学节奏提示" "${TEACHER_HOME}" && TEACHER_HOME_LAYOUT_OK=true || TEACHER_HOME_LAYOUT_OK=false
marker "PHASE31B_TEACHER_HOME_LAYOUT_OK" "${TEACHER_HOME_LAYOUT_OK}"

DASHBOARD="${TMP_DIR}/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "课堂视频证据" "${DASHBOARD}" && grep -q "课堂参与节奏条" "${DASHBOARD}" && grep -q "课堂结果列表与筛选" "${DASHBOARD}" && DASHBOARD_LAYOUT_OK=true || DASHBOARD_LAYOUT_OK=false
marker "PHASE31B_DASHBOARD_LAYOUT_OK" "${DASHBOARD_LAYOUT_OK}"
[ "${DASHBOARD_LAYOUT_OK}" = "true" ] && grep -q "debug-details" "${DASHBOARD}" && DASHBOARD_SCROLL_OK=true || DASHBOARD_SCROLL_OK=false
marker "PHASE31B_DASHBOARD_SCROLL_OK" "${DASHBOARD_SCROLL_OK}"

TRENDS="${TMP_DIR}/teacher-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/trends" "${TRENDS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "教学反馈趋势主图" "${TRENDS}" && grep -q "复盘优先级" "${TRENDS}" && TEACHER_TRENDS_LAYOUT_OK=true || TEACHER_TRENDS_LAYOUT_OK=false
marker "PHASE31B_TEACHER_TRENDS_LAYOUT_OK" "${TEACHER_TRENDS_LAYOUT_OK}"

REPORTS="${TMP_DIR}/teacher-reports.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/reports" "${REPORTS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "教学报告" "${REPORTS}" && grep -q "建议摘要" "${REPORTS}" && TEACHER_REPORTS_LAYOUT_OK=true || TEACHER_REPORTS_LAYOUT_OK=false
marker "PHASE31B_TEACHER_REPORTS_LAYOUT_OK" "${TEACHER_REPORTS_LAYOUT_OK}"

echo
echo "[step] admin pages"
ADMIN_COOKIE="${TMP_DIR}/admin.cookie"
ADMIN_LOGIN="${TMP_DIR}/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${ADMIN_LOGIN}" -c "${ADMIN_COOKIE}" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "${STATUS}" = "200" ] && json_success "${ADMIN_LOGIN}" && ADMIN_LOGIN_OK=true || ADMIN_LOGIN_OK=false

ADMIN_HOME="${TMP_DIR}/admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${ADMIN_HOME}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "平台总览" "${ADMIN_HOME}" && grep -q "快捷入口" "${ADMIN_HOME}" && ADMIN_HOME_LAYOUT_OK=true || ADMIN_HOME_LAYOUT_OK=false
marker "PHASE31B_ADMIN_HOME_LAYOUT_OK" "${ADMIN_HOME_LAYOUT_OK}"

ADMIN_TRENDS="${TMP_DIR}/admin-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/trends" "${ADMIN_TRENDS}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "平台课堂质量趋势" "${ADMIN_TRENDS}" && grep -q "平台风险分布" "${ADMIN_TRENDS}" && ADMIN_TRENDS_LAYOUT_OK=true || ADMIN_TRENDS_LAYOUT_OK=false
marker "PHASE31B_ADMIN_TRENDS_LAYOUT_OK" "${ADMIN_TRENDS_LAYOUT_OK}"

ADMIN_INGESTION="${TMP_DIR}/admin-ingestion.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/ingestion" "${ADMIN_INGESTION}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "三端数据接入状态" "${ADMIN_INGESTION}" && grep -q "flow-board" "${ADMIN_INGESTION}" && grep -q "数据质量进度" "${ADMIN_INGESTION}" && ADMIN_INGESTION_LAYOUT_OK=true || ADMIN_INGESTION_LAYOUT_OK=false
marker "PHASE31B_ADMIN_INGESTION_LAYOUT_OK" "${ADMIN_INGESTION_LAYOUT_OK}"

echo
echo "[step] structure and localization"
grep -q "overflow-x: hidden" "${TMP_DIR}/dashboard.html" && grep -q "table-scroll" "${TMP_DIR}/dashboard.html" && NO_OVERFLOW_OK=true || NO_OVERFLOW_OK=false
marker "PHASE31B_NO_PAGE_OVERFLOW_OK" "${NO_OVERFLOW_OK}"
grep -q "details" "${TMP_DIR}/dashboard.html" && grep -q "max-height" "${TMP_DIR}/dashboard.html" && NO_BOTTOM_OK=true || NO_BOTTOM_OK=false
marker "PHASE31B_NO_UNREACHABLE_BOTTOM_OK" "${NO_BOTTOM_OK}"
! grep -Eq ">raw<|>reviewed<|>archived<|>high<|>medium<|>low<|>real<|>demo<" "${DASHBOARD}" "${TEACHER_HOME}" "${ADMIN_HOME}" "${ADMIN_INGESTION}" && TEXT_OK=true || TEXT_OK=false
marker "PHASE31B_TEXT_LOCALIZATION_OK" "${TEXT_OK}"
grep -q "课堂证据" "${DASHBOARD}" && grep -q "教学反馈" "${TEACHER_HOME}" && EDUCATION_OK=true || EDUCATION_OK=false
marker "PHASE31B_EDUCATION_STYLE_OK" "${EDUCATION_OK}"
grep -q "markLine" "${DASHBOARD}" && grep -q "areaStyle" "${TRENDS}" && grep -q "echarts" "${ADMIN_TRENDS}" && CHART_OK=true || CHART_OK=false
marker "PHASE31B_CHART_VISUAL_POLISH_OK" "${CHART_OK}"
grep -q "dashboard-grid" "${DASHBOARD}" && grep -q "dashboard-grid" "${TRENDS}" && SPACE_OK=true || SPACE_OK=false
marker "PHASE31B_VISUAL_EMPTY_SPACE_OK" "${SPACE_OK}"
grep -q "prefers-reduced-motion" "${DASHBOARD}" && MOTION_OK=true || MOTION_OK=false
marker "PHASE31B_MOTION_SAFE_OK" "${MOTION_OK}"
grep -q "课堂参与节奏条" "${DASHBOARD}" && grep -q "复盘优先级" "${TRENDS}" && grep -q "flow-board" "${ADMIN_INGESTION}" && REF_OK=true || REF_OK=false
marker "PHASE31B_REFERENCE_ABSORPTION_VISIBLE" "${REF_OK}"

echo
echo "[step] regressions"
TEACHER_ADMIN="${TMP_DIR}/teacher-admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${TEACHER_ADMIN}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "403" ] && AUTH_OK=true || AUTH_OK=false
marker "PHASE31B_AUTH_REGRESSION_OK" "${AUTH_OK}"

TRENDS_JSON="${TMP_DIR}/trends.json"
REPORTS_JSON="${TMP_DIR}/reports.json"
DETAIL_JSON="${TMP_DIR}/detail.json"
STATUS_TRENDS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?limit=20" "${TRENDS_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_REPORTS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports?limit=20" "${REPORTS_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_DETAIL="$(curl_status GET "${API_BASE_URL}/api/teacher/reports/detail?result_id=${RESULT_ID}" "${DETAIL_JSON}" -b "${TEACHER_COOKIE}")"
[ "${STATUS_TRENDS}" = "200" ] && json_success "${TRENDS_JSON}" && [ "${STATUS_REPORTS}" = "200" ] && json_success "${REPORTS_JSON}" && [ "${STATUS_DETAIL}" = "200" ] && json_success "${DETAIL_JSON}" && PHASE30_OK=true || PHASE30_OK=false
marker "PHASE31B_PHASE30_REGRESSION_OK" "${PHASE30_OK}"

all_true "PHASE31B_REGRESSION_OK" "${LOGIN_OK}" "${TEACHER_LOGIN_OK}" "${ADMIN_LOGIN_OK}" "${TEACHER_HOME_LAYOUT_OK}" "${DASHBOARD_LAYOUT_OK}" "${DASHBOARD_SCROLL_OK}" "${TEACHER_TRENDS_LAYOUT_OK}" "${TEACHER_REPORTS_LAYOUT_OK}" "${ADMIN_HOME_LAYOUT_OK}" "${ADMIN_TRENDS_LAYOUT_OK}" "${ADMIN_INGESTION_LAYOUT_OK}" "${NO_OVERFLOW_OK}" "${NO_BOTTOM_OK}" "${TEXT_OK}" "${EDUCATION_OK}" "${CHART_OK}" "${SPACE_OK}" "${MOTION_OK}" "${REF_OK}" "${AUTH_OK}" "${PHASE30_OK}"

echo
echo "[done] Phase 3.1-b layout validation completed"
