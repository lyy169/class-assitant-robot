#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
TMP_DIR="${TMPDIR:-/tmp}/phase31c-validation-$$"
CONSOLE_CHECK="${TMP_DIR}/phase31c-layout-console-check.js"

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

cat > "${CONSOLE_CHECK}" <<'EOF'
(() => {
  const de = document.documentElement;
  const elements = Array.from(document.querySelectorAll('body *'));
  const isInsideAllowedScroll = (el) => Boolean(el.closest('.table-scroll, .debug-scroll, details.debug-details'));
  const rects = elements.map((el) => {
    const r = el.getBoundingClientRect();
    return {
      el,
      tag: el.tagName,
      cls: String(el.className || ''),
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80),
      left: Math.round(r.left + window.scrollX),
      right: Math.round(r.right + window.scrollX),
      top: Math.round(r.top + window.scrollY),
      bottom: Math.round(r.bottom + window.scrollY),
      width: Math.round(r.width),
      height: Math.round(r.height),
      allowedInternalScroll: isInsideAllowedScroll(el)
    };
  }).filter((x) => Number.isFinite(x.right) && Number.isFinite(x.bottom));
  const visibleRects = rects.filter((x) => !x.allowedInternalScroll);
  const maxRight = Math.max(...visibleRects.map((x) => x.right), 0);
  const maxBottom = Math.max(...visibleRects.map((x) => x.bottom), 0);
  const tableScrollContainers = Array.from(document.querySelectorAll('.table-scroll')).map((el) => {
    const r = el.getBoundingClientRect();
    return {
      left: Math.round(r.left + window.scrollX),
      right: Math.round(r.right + window.scrollX),
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      internalHorizontalScroll: el.scrollWidth > el.clientWidth + 2,
      containerBeyondViewport: r.right > de.clientWidth + 2
    };
  });
  return {
    url: location.href,
    clientWidth: de.clientWidth,
    scrollWidth: de.scrollWidth,
    scrollHeight: de.scrollHeight,
    maxRight,
    maxBottom,
    pageHorizontalOverflow: de.scrollWidth > de.clientWidth + 2,
    invisibleRightOverflow: maxRight > de.clientWidth + 2,
    unreachableBottom: maxBottom > de.scrollHeight + 50,
    tableScrollContainers,
    topRightOffenders: visibleRects.filter((x) => x.right > de.clientWidth + 2).sort((a, b) => b.right - a.right).slice(0, 5).map(({el, ...x}) => x),
    bottomOffenders: visibleRects.filter((x) => x.bottom > de.scrollHeight + 50).sort((a, b) => b.bottom - a.bottom).slice(0, 5).map(({el, ...x}) => x)
  };
})();
EOF

echo
echo "[step] login"
LOGIN_HTML="${TMP_DIR}/login.html"
STATUS="$(curl_status GET "${API_BASE_URL}/login" "${LOGIN_HTML}")"
[ "${STATUS}" = "200" ] && grep -q "智能课堂行为分析与教学反馈平台" "${LOGIN_HTML}" && LOGIN_OK=true || LOGIN_OK=false
marker "PHASE31C_LOGIN_OK" "${LOGIN_OK}"

echo
echo "[step] teacher session and pages"
TEACHER_COOKIE="${TMP_DIR}/teacher.cookie"
TEACHER_LOGIN="${TMP_DIR}/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${TEACHER_LOGIN}" -c "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "${STATUS}" = "200" ] && json_success "${TEACHER_LOGIN}" && TEACHER_LOGIN_OK=true || TEACHER_LOGIN_OK=false

TEACHER_HOME="${TMP_DIR}/teacher.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "${TEACHER_HOME}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "复盘 Spotlight" "${TEACHER_HOME}" && TEACHER_HOME_OK=true || TEACHER_HOME_OK=false
marker "PHASE31C_TEACHER_HOME_LAYOUT_OK" "${TEACHER_HOME_OK}"

DASHBOARD="${TMP_DIR}/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "dashboard-results-template" "${DASHBOARD}" && grep -q "dashboard-results-mount" "${DASHBOARD}" && DASHBOARD_OK=true || DASHBOARD_OK=false
marker "PHASE31C_DASHBOARD_LAYOUT_OK" "${DASHBOARD_OK}"
[ "${DASHBOARD_OK}" = "true" ] && grep -q "展开后加载课堂结果列表" "${DASHBOARD}" && grep -q "debug-details" "${DASHBOARD}" && DASHBOARD_SCROLL_OK=true || DASHBOARD_SCROLL_OK=false
marker "PHASE31C_DASHBOARD_SCROLL_OK" "${DASHBOARD_SCROLL_OK}"

TRENDS="${TMP_DIR}/teacher-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/trends" "${TRENDS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "教学反馈趋势主图" "${TRENDS}" && TEACHER_TRENDS_OK=true || TEACHER_TRENDS_OK=false
marker "PHASE31C_TEACHER_TRENDS_LAYOUT_OK" "${TEACHER_TRENDS_OK}"

REPORTS="${TMP_DIR}/teacher-reports.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/reports" "${REPORTS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "报告中心" "${REPORTS}" && TEACHER_REPORTS_OK=true || TEACHER_REPORTS_OK=false
marker "PHASE31C_TEACHER_REPORTS_LAYOUT_OK" "${TEACHER_REPORTS_OK}"

echo
echo "[step] admin session and pages"
ADMIN_COOKIE="${TMP_DIR}/admin.cookie"
ADMIN_LOGIN="${TMP_DIR}/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${ADMIN_LOGIN}" -c "${ADMIN_COOKIE}" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "${STATUS}" = "200" ] && json_success "${ADMIN_LOGIN}" && ADMIN_LOGIN_OK=true || ADMIN_LOGIN_OK=false

ADMIN_HOME="${TMP_DIR}/admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${ADMIN_HOME}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "平台总览" "${ADMIN_HOME}" && ADMIN_HOME_OK=true || ADMIN_HOME_OK=false
marker "PHASE31C_ADMIN_HOME_LAYOUT_OK" "${ADMIN_HOME_OK}"

ADMIN_TRENDS="${TMP_DIR}/admin-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/trends" "${ADMIN_TRENDS}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "rankCards" "${ADMIN_TRENDS}" && grep -q "rank-bar" "${ADMIN_TRENDS}" && ADMIN_TRENDS_OK=true || ADMIN_TRENDS_OK=false
marker "PHASE31C_ADMIN_TRENDS_LAYOUT_OK" "${ADMIN_TRENDS_OK}"
[ "${ADMIN_TRENDS_OK}" = "true" ] && ! grep -q 'id="classroom-rankings".*<table' "${ADMIN_TRENDS}" && ADMIN_TRENDS_RIGHT_OK=true || ADMIN_TRENDS_RIGHT_OK=false
marker "PHASE31C_ADMIN_TRENDS_RIGHT_OVERFLOW_OK" "${ADMIN_TRENDS_RIGHT_OK}"

ADMIN_INGESTION="${TMP_DIR}/admin-ingestion.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/ingestion" "${ADMIN_INGESTION}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "flow-board" "${ADMIN_INGESTION}" && ADMIN_INGESTION_OK=true || ADMIN_INGESTION_OK=false
marker "PHASE31C_ADMIN_INGESTION_LAYOUT_OK" "${ADMIN_INGESTION_OK}"

echo
echo "[step] layout integrity structure"
if grep -q "overflow-x: hidden" "${DASHBOARD}" "${ADMIN_TRENDS}" "${TEACHER_HOME}" "${ADMIN_HOME}"; then
  NO_HIDDEN_X=false
else
  NO_HIDDEN_X=true
fi
[ "${DASHBOARD_SCROLL_OK}" = "true" ] && [ "${NO_HIDDEN_X}" = "true" ] && NO_BOTTOM_OK=true || NO_BOTTOM_OK=false
marker "PHASE31C_NO_UNREACHABLE_BOTTOM_OK" "${NO_BOTTOM_OK}"
[ "${ADMIN_TRENDS_RIGHT_OK}" = "true" ] && [ "${NO_HIDDEN_X}" = "true" ] && NO_RIGHT_OK=true || NO_RIGHT_OK=false
marker "PHASE31C_NO_INVISIBLE_RIGHT_OVERFLOW_OK" "${NO_RIGHT_OK}"

echo
echo "[step] regressions"
TEACHER_ADMIN="${TMP_DIR}/teacher-admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${TEACHER_ADMIN}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "403" ] && AUTH_OK=true || AUTH_OK=false
marker "PHASE31C_AUTH_REGRESSION_OK" "${AUTH_OK}"

TRENDS_JSON="${TMP_DIR}/trends.json"
REPORTS_JSON="${TMP_DIR}/reports.json"
DETAIL_JSON="${TMP_DIR}/detail.json"
STATUS_TRENDS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?limit=20" "${TRENDS_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_REPORTS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports?limit=20" "${REPORTS_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_DETAIL="$(curl_status GET "${API_BASE_URL}/api/teacher/reports/detail?result_id=${RESULT_ID}" "${DETAIL_JSON}" -b "${TEACHER_COOKIE}")"
[ "${STATUS_TRENDS}" = "200" ] && json_success "${TRENDS_JSON}" && [ "${STATUS_REPORTS}" = "200" ] && json_success "${REPORTS_JSON}" && [ "${STATUS_DETAIL}" = "200" ] && json_success "${DETAIL_JSON}" && PHASE30_OK=true || PHASE30_OK=false
marker "PHASE31C_PHASE30_REGRESSION_OK" "${PHASE30_OK}"

echo
echo "[manual] Browser console layout check saved at:"
echo "${CONSOLE_CHECK}"
echo "[manual] Copy the script from docs/runbooks/v3-phase3.1c-layout-integrity-validation-runbook.md or ${CONSOLE_CHECK}"
echo "[manual] Required browser metrics: pageHorizontalOverflow=false, invisibleRightOverflow=false, unreachableBottom=false"

all_true "PHASE31C_REGRESSION_OK" "${LOGIN_OK}" "${TEACHER_LOGIN_OK}" "${ADMIN_LOGIN_OK}" "${TEACHER_HOME_OK}" "${DASHBOARD_OK}" "${DASHBOARD_SCROLL_OK}" "${TEACHER_TRENDS_OK}" "${TEACHER_REPORTS_OK}" "${ADMIN_HOME_OK}" "${ADMIN_TRENDS_OK}" "${ADMIN_TRENDS_RIGHT_OK}" "${ADMIN_INGESTION_OK}" "${NO_BOTTOM_OK}" "${NO_RIGHT_OK}" "${AUTH_OK}" "${PHASE30_OK}"

echo
echo "[done] Phase 3.1-c layout integrity validation completed"
