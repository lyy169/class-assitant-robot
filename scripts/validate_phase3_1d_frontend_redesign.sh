#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
TMP_DIR="${TMPDIR:-/tmp}/phase31d-validation-$$"
CONSOLE_CHECK="${TMP_DIR}/phase31d-layout-console-check.js"

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
    topRightOffenders: visibleRects.filter((x) => x.right > de.clientWidth + 2).sort((a, b) => b.right - a.right).slice(0, 5).map(({el, ...x}) => x),
    bottomOffenders: visibleRects.filter((x) => x.bottom > de.scrollHeight + 50).sort((a, b) => b.bottom - a.bottom).slice(0, 5).map(({el, ...x}) => x)
  };
})();
EOF

echo
echo "[step] login and teacher pages"
LOGIN_HTML="${TMP_DIR}/login.html"
STATUS="$(curl_status GET "${API_BASE_URL}/login" "${LOGIN_HTML}")"
[ "${STATUS}" = "200" ] && grep -q "login-shell" "${LOGIN_HTML}" && grep -q "login-visual-panel" "${LOGIN_HTML}" && LOGIN_OK=true || LOGIN_OK=false
marker "PHASE31D_LOGIN_LAYOUT_OK" "${LOGIN_OK}"

TEACHER_COOKIE="${TMP_DIR}/teacher.cookie"
TEACHER_LOGIN="${TMP_DIR}/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${TEACHER_LOGIN}" -c "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "${STATUS}" = "200" ] && json_success "${TEACHER_LOGIN}" && TEACHER_LOGIN_OK=true || TEACHER_LOGIN_OK=false
marker "PHASE31D_TEACHER_LOGIN_OK" "${TEACHER_LOGIN_OK}"

TEACHER_HOME="${TMP_DIR}/teacher.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "${TEACHER_HOME}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "page-main" "${TEACHER_HOME}" && grep -q "dashboard-grid" "${TEACHER_HOME}" && grep -q "data-marker=\"teacher-home-todos\"" "${TEACHER_HOME}" && TEACHER_HOME_OK=true || TEACHER_HOME_OK=false
marker "PHASE31D_TEACHER_HOME_LAYOUT_OK" "${TEACHER_HOME_OK}"

TEACHER_RESULTS="${TMP_DIR}/teacher-results.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/results" "${TEACHER_RESULTS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "record-grid" "${TEACHER_RESULTS}" && grep -q "result-card" "${TEACHER_RESULTS}" && TEACHER_RESULTS_OK=true || TEACHER_RESULTS_OK=false
marker "PHASE31D_TEACHER_RESULTS_LAYOUT_OK" "${TEACHER_RESULTS_OK}"

DASHBOARD="${TMP_DIR}/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "evidence-panel" "${DASHBOARD}" && grep -q "insight-panel insight-stack" "${DASHBOARD}" && grep -q "dashboard-results-template" "${DASHBOARD}" && DASHBOARD_OK=true || DASHBOARD_OK=false
marker "PHASE31D_DASHBOARD_FIRST_SCREEN_OK" "${DASHBOARD_OK}"

TEACHER_TRENDS="${TMP_DIR}/teacher-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/trends" "${TEACHER_TRENDS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "chart-side-grid" "${TEACHER_TRENDS}" && grep -q "phase30-score-trend-chart" "${TEACHER_TRENDS}" && TEACHER_TRENDS_OK=true || TEACHER_TRENDS_OK=false
marker "PHASE31D_TEACHER_TRENDS_LAYOUT_OK" "${TEACHER_TRENDS_OK}"

TEACHER_REPORTS="${TMP_DIR}/teacher-reports.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/reports" "${TEACHER_REPORTS}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "report-card" "${TEACHER_REPORTS}" && grep -q "ai-summary" "${TEACHER_REPORTS}" && TEACHER_REPORTS_OK=true || TEACHER_REPORTS_OK=false
marker "PHASE31D_TEACHER_REPORTS_LAYOUT_OK" "${TEACHER_REPORTS_OK}"

echo
echo "[step] admin pages"
ADMIN_COOKIE="${TMP_DIR}/admin.cookie"
ADMIN_LOGIN="${TMP_DIR}/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${ADMIN_LOGIN}" -c "${ADMIN_COOKIE}" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "${STATUS}" = "200" ] && json_success "${ADMIN_LOGIN}" && ADMIN_LOGIN_OK=true || ADMIN_LOGIN_OK=false
marker "PHASE31D_ADMIN_LOGIN_OK" "${ADMIN_LOGIN_OK}"

ADMIN_HOME="${TMP_DIR}/admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${ADMIN_HOME}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "admin-data-pipeline" "${ADMIN_HOME}" && grep -q "page-main" "${ADMIN_HOME}" && ADMIN_HOME_OK=true || ADMIN_HOME_OK=false
marker "PHASE31D_ADMIN_HOME_LAYOUT_OK" "${ADMIN_HOME_OK}"

ADMIN_INGESTION="${TMP_DIR}/admin-ingestion.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/ingestion" "${ADMIN_INGESTION}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "admin-ingestion-pipeline" "${ADMIN_INGESTION}" && grep -q "flow-board" "${ADMIN_INGESTION}" && grep -q "standardized_video_present" "${ADMIN_INGESTION}" && ADMIN_INGESTION_OK=true || ADMIN_INGESTION_OK=false
marker "PHASE31D_ADMIN_INGESTION_LAYOUT_OK" "${ADMIN_INGESTION_OK}"

ADMIN_TRENDS="${TMP_DIR}/admin-trends.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/trends" "${ADMIN_TRENDS}" -b "${ADMIN_COOKIE}")"
[ "${STATUS}" = "200" ] && grep -q "rankCards" "${ADMIN_TRENDS}" && grep -q "rank-bar" "${ADMIN_TRENDS}" && ADMIN_TRENDS_OK=true || ADMIN_TRENDS_OK=false
marker "PHASE31D_ADMIN_TRENDS_LAYOUT_OK" "${ADMIN_TRENDS_OK}"

echo
echo "[step] layout guard and regressions"
if grep -q "overflow-x: hidden" "${LOGIN_HTML}" "${TEACHER_HOME}" "${DASHBOARD}" "${ADMIN_TRENDS}"; then
  NO_OVERFLOW_GUARD_OK=false
else
  NO_OVERFLOW_GUARD_OK=true
fi
marker "PHASE31D_NO_OVERFLOW_GUARD_OK" "${NO_OVERFLOW_GUARD_OK}"

TEACHER_ADMIN="${TMP_DIR}/teacher-admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${TEACHER_ADMIN}" -b "${TEACHER_COOKIE}")"
[ "${STATUS}" = "403" ] && AUTH_OK=true || AUTH_OK=false
marker "PHASE31D_AUTH_REGRESSION_OK" "${AUTH_OK}"

TRENDS_JSON="${TMP_DIR}/trends.json"
REPORTS_JSON="${TMP_DIR}/reports.json"
DETAIL_JSON="${TMP_DIR}/detail.json"
ADMIN_TRENDS_JSON="${TMP_DIR}/admin-trends.json"
STATUS_TRENDS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?limit=20" "${TRENDS_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_REPORTS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports?limit=20" "${REPORTS_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_DETAIL="$(curl_status GET "${API_BASE_URL}/api/teacher/reports/detail?result_id=${RESULT_ID}" "${DETAIL_JSON}" -b "${TEACHER_COOKIE}")"
STATUS_ADMIN_TRENDS="$(curl_status GET "${API_BASE_URL}/api/admin/trends?limit=30" "${ADMIN_TRENDS_JSON}" -b "${ADMIN_COOKIE}")"
[ "${STATUS_TRENDS}" = "200" ] && json_success "${TRENDS_JSON}" && [ "${STATUS_REPORTS}" = "200" ] && json_success "${REPORTS_JSON}" && [ "${STATUS_DETAIL}" = "200" ] && json_success "${DETAIL_JSON}" && [ "${STATUS_ADMIN_TRENDS}" = "200" ] && json_success "${ADMIN_TRENDS_JSON}" && PHASE30_OK=true || PHASE30_OK=false
marker "PHASE31D_PHASE30_REGRESSION_OK" "${PHASE30_OK}"

echo "[manual] Browser console layout check script:"
echo "${CONSOLE_CHECK}"
echo "[manual] Required browser metrics: pageHorizontalOverflow=false, invisibleRightOverflow=false, unreachableBottom=false"

all_true "PHASE31D_REGRESSION_OK" "${LOGIN_OK}" "${TEACHER_LOGIN_OK}" "${TEACHER_HOME_OK}" "${TEACHER_RESULTS_OK}" "${DASHBOARD_OK}" "${TEACHER_TRENDS_OK}" "${TEACHER_REPORTS_OK}" "${ADMIN_LOGIN_OK}" "${ADMIN_HOME_OK}" "${ADMIN_INGESTION_OK}" "${ADMIN_TRENDS_OK}" "${NO_OVERFLOW_GUARD_OK}" "${AUTH_OK}" "${PHASE30_OK}"

echo
echo "[done] Phase 3.1d frontend redesign validation completed"
