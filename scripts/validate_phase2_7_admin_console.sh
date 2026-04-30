#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase27-validation-$$"

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
  curl -sS -o "${output}" -w "%{http_code}" -X "${method}" "${url}" "$@"
}

print_marker() {
  echo "$1=$2"
}

expect_status() {
  local name="$1"
  local actual="$2"
  local expected="$3"
  if [ "${actual}" = "${expected}" ]; then
    print_marker "${name}" "true"
  else
    print_marker "${name}" "false expected_${expected}_got_${actual}"
  fi
}

json_has_keys() {
  local file="$1"
  shift
  python -c '
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
missing = [key for key in sys.argv[2:] if key not in payload]
if missing:
    print("missing:" + ",".join(missing))
    sys.exit(1)
print("ok")
' "${file}" "$@"
}

json_admin_results_shape() {
  local file="$1"
  python -c '
import json
import sys
required = {
    "result_id", "analysis_id", "classroom_id", "classroom_name",
    "teacher_id", "teacher_name", "lesson_title", "generated_at",
    "created_at", "feedback_score", "attention_score", "response_score",
    "status", "has_video", "video_status", "detail_url"
}
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
if not {"success", "filters", "overview", "items", "total"}.issubset(payload):
    print("bad_top_level")
    sys.exit(1)
items = payload.get("items") or []
if items:
    missing = required.difference(items[0])
    if missing:
        print("missing:" + ",".join(sorted(missing)))
        sys.exit(1)
print("ok")
' "${file}"
}

echo
echo "[step] admin pages"
ADMIN_HTML="${TMP_DIR}/admin.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin" "${ADMIN_HTML}")"
expect_status "PHASE27_ADMIN_PAGE_200" "${STATUS}" "200"
grep -q 'data-marker="admin-overview-page"' "${ADMIN_HTML}" && print_marker "PHASE27_ADMIN_OVERVIEW_PAGE_MARKER" "true" || print_marker "PHASE27_ADMIN_OVERVIEW_PAGE_MARKER" "false"
grep -q 'data-marker="admin-console-nav"' "${ADMIN_HTML}" && print_marker "PHASE27_ADMIN_NAV_MARKER" "true" || print_marker "PHASE27_ADMIN_NAV_MARKER" "false"
grep -q 'data-marker="admin-overview-metrics"' "${ADMIN_HTML}" && print_marker "PHASE27_ADMIN_OVERVIEW_METRICS_MARKER" "true" || print_marker "PHASE27_ADMIN_OVERVIEW_METRICS_MARKER" "false"

ADMIN_CLASSROOMS_HTML="${TMP_DIR}/admin-classrooms.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/classrooms" "${ADMIN_CLASSROOMS_HTML}")"
expect_status "PHASE27_ADMIN_CLASSROOMS_PAGE_200" "${STATUS}" "200"
grep -q 'data-marker="admin-classrooms-page"' "${ADMIN_CLASSROOMS_HTML}" && print_marker "PHASE27_ADMIN_CLASSROOMS_PAGE_MARKER" "true" || print_marker "PHASE27_ADMIN_CLASSROOMS_PAGE_MARKER" "false"
grep -q 'data-marker="admin-classroom-list"' "${ADMIN_CLASSROOMS_HTML}" && print_marker "PHASE27_ADMIN_CLASSROOM_LIST_MARKER" "true" || print_marker "PHASE27_ADMIN_CLASSROOM_LIST_MARKER" "false"
grep -q 'data-marker="admin-classroom-ranking"' "${ADMIN_CLASSROOMS_HTML}" && print_marker "PHASE27_ADMIN_CLASSROOM_SUPPORT_MARKER" "true" || print_marker "PHASE27_ADMIN_CLASSROOM_SUPPORT_MARKER" "false"

ADMIN_TEACHERS_HTML="${TMP_DIR}/admin-teachers.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/teachers" "${ADMIN_TEACHERS_HTML}")"
expect_status "PHASE27_ADMIN_TEACHERS_PAGE_200" "${STATUS}" "200"
grep -q 'data-marker="admin-teachers-page"' "${ADMIN_TEACHERS_HTML}" && print_marker "PHASE27_ADMIN_TEACHERS_PAGE_MARKER" "true" || print_marker "PHASE27_ADMIN_TEACHERS_PAGE_MARKER" "false"
grep -q 'data-marker="admin-teacher-list"' "${ADMIN_TEACHERS_HTML}" && print_marker "PHASE27_ADMIN_TEACHER_LIST_MARKER" "true" || print_marker "PHASE27_ADMIN_TEACHER_LIST_MARKER" "false"
grep -q 'data-marker="admin-teacher-feedback-ranking"' "${ADMIN_TEACHERS_HTML}" && print_marker "PHASE27_ADMIN_TEACHER_SUPPORT_MARKER" "true" || print_marker "PHASE27_ADMIN_TEACHER_SUPPORT_MARKER" "false"

ADMIN_RESULTS_HTML="${TMP_DIR}/admin-results.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/results" "${ADMIN_RESULTS_HTML}")"
expect_status "PHASE27_ADMIN_RESULTS_PAGE_200" "${STATUS}" "200"
grep -q 'data-marker="admin-results-page"' "${ADMIN_RESULTS_HTML}" && print_marker "PHASE27_ADMIN_RESULTS_PAGE_MARKER" "true" || print_marker "PHASE27_ADMIN_RESULTS_PAGE_MARKER" "false"
grep -q 'data-marker="admin-results-filters"' "${ADMIN_RESULTS_HTML}" && print_marker "PHASE27_ADMIN_RESULTS_FILTERS_MARKER" "true" || print_marker "PHASE27_ADMIN_RESULTS_FILTERS_MARKER" "false"
grep -q 'data-marker="admin-results-tips"' "${ADMIN_RESULTS_HTML}" && print_marker "PHASE27_ADMIN_RESULTS_SUPPORT_MARKER" "true" || print_marker "PHASE27_ADMIN_RESULTS_SUPPORT_MARKER" "false"

echo
echo "[step] admin APIs"
OVERVIEW_JSON="${TMP_DIR}/admin-overview.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/overview" "${OVERVIEW_JSON}")"
expect_status "PHASE27_ADMIN_OVERVIEW_API_200" "${STATUS}" "200"
json_has_keys "${OVERVIEW_JSON}" success admin metrics system_status status_distribution latest_results quick_links >/dev/null 2>&1 && print_marker "PHASE27_ADMIN_OVERVIEW_SHAPE" "true" || print_marker "PHASE27_ADMIN_OVERVIEW_SHAPE" "false"

CLASSROOMS_JSON="${TMP_DIR}/admin-classrooms.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/classrooms" "${CLASSROOMS_JSON}")"
expect_status "PHASE27_ADMIN_CLASSROOMS_API_200" "${STATUS}" "200"
json_has_keys "${CLASSROOMS_JSON}" success overview items total >/dev/null 2>&1 && print_marker "PHASE27_ADMIN_CLASSROOMS_SHAPE" "true" || print_marker "PHASE27_ADMIN_CLASSROOMS_SHAPE" "false"

TEACHERS_JSON="${TMP_DIR}/admin-teachers.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/teachers" "${TEACHERS_JSON}")"
expect_status "PHASE27_ADMIN_TEACHERS_API_200" "${STATUS}" "200"
json_has_keys "${TEACHERS_JSON}" success overview items total >/dev/null 2>&1 && print_marker "PHASE27_ADMIN_TEACHERS_SHAPE" "true" || print_marker "PHASE27_ADMIN_TEACHERS_SHAPE" "false"

RESULTS_JSON="${TMP_DIR}/admin-results.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/results?limit=20" "${RESULTS_JSON}")"
expect_status "PHASE27_ADMIN_RESULTS_API_200" "${STATUS}" "200"
json_admin_results_shape "${RESULTS_JSON}" >/dev/null 2>&1 && print_marker "PHASE27_ADMIN_RESULTS_SHAPE" "true" || print_marker "PHASE27_ADMIN_RESULTS_SHAPE" "false"

FILTERED_JSON="${TMP_DIR}/admin-results-classroom.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/results?classroom_id=${CLASSROOM_ID}&limit=20" "${FILTERED_JSON}")"
expect_status "PHASE27_ADMIN_RESULTS_CLASSROOM_FILTER_200" "${STATUS}" "200"

INVALID_JSON="${TMP_DIR}/admin-results-invalid.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/results?status=bad_status" "${INVALID_JSON}")"
expect_status "PHASE27_ADMIN_RESULTS_INVALID_STATUS_400" "${STATUS}" "400"

echo
echo "[step] phase 2.6 regression"
TEACHER_HTML="${TMP_DIR}/teacher.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "${TEACHER_HTML}")"
expect_status "PHASE27_TEACHER_PAGE_200" "${STATUS}" "200"
grep -q 'data-marker="teacher-home-page"' "${TEACHER_HTML}" && print_marker "PHASE27_TEACHER_HOME_MARKER" "true" || print_marker "PHASE27_TEACHER_HOME_MARKER" "false"
TEACHER_RESULTS_HTML="${TMP_DIR}/teacher-results.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/results" "${TEACHER_RESULTS_HTML}")"
expect_status "PHASE27_TEACHER_RESULTS_PAGE_200" "${STATUS}" "200"
grep -q 'data-marker="teacher-results-page"' "${TEACHER_RESULTS_HTML}" && print_marker "PHASE27_TEACHER_RESULTS_MARKER" "true" || print_marker "PHASE27_TEACHER_RESULTS_MARKER" "false"

echo
echo "[step] phase 2.5 regression"
DASHBOARD_HTML="${TMP_DIR}/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD_HTML}")"
expect_status "PHASE27_DASHBOARD_DEEPLINK_200" "${STATUS}" "200"
grep -q 'data-marker="attention-activity-chart"' "${DASHBOARD_HTML}" && print_marker "PHASE27_DASHBOARD_CHART_MARKER" "true" || print_marker "PHASE27_DASHBOARD_CHART_MARKER" "false"
DETAIL_JSON="${TMP_DIR}/detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESULT_ID}" "${DETAIL_JSON}")"
expect_status "PHASE27_PHASE25_DETAIL_200" "${STATUS}" "200"
json_has_keys "${DETAIL_JSON}" success result >/dev/null 2>&1 && print_marker "PHASE27_PHASE25_DETAIL_SHAPE" "true" || print_marker "PHASE27_PHASE25_DETAIL_SHAPE" "false"

echo
echo "[step] phase 1/2 read regression"
LATEST_JSON="${TMP_DIR}/latest.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/latest-interaction-result" "${LATEST_JSON}")"
expect_status "PHASE27_LEGACY_LATEST_200" "${STATUS}" "200"
RECENT_JSON="${TMP_DIR}/recent.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/recent-interaction-results?limit=5" "${RECENT_JSON}")"
expect_status "PHASE27_LEGACY_RECENT_200" "${STATUS}" "200"

echo
echo "[done] Phase 2.7 admin console validation completed"
