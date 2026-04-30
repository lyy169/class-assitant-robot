#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase26-validation-$$"

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

json_result_items_shape() {
  local file="$1"
  python -c '
import json
import sys

required = {
    "result_id", "analysis_id", "classroom_id", "classroom_name", "lesson_title",
    "recorded_at", "generated_at", "created_at", "duration_seconds",
    "feedback_score", "attention_score", "response_score", "status",
    "has_video", "video_status", "detail_url", "updated_at"
}
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
if not {"success", "filters", "items", "total"}.issubset(payload):
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
echo "[step] teacher home page"
TEACHER_HTML="${TMP_DIR}/teacher.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher" "${TEACHER_HTML}")"
expect_status "PHASE26_TEACHER_PAGE_200" "${STATUS}" "200"
grep -q 'data-marker="teacher-home-page"' "${TEACHER_HTML}" && print_marker "PHASE26_TEACHER_HOME_MARKER" "true" || print_marker "PHASE26_TEACHER_HOME_MARKER" "false"
grep -q 'data-marker="teacher-console-nav"' "${TEACHER_HTML}" && print_marker "PHASE26_TEACHER_NAV_MARKER" "true" || print_marker "PHASE26_TEACHER_NAV_MARKER" "false"
if grep -q '\${{' "${TEACHER_HTML}" || grep -q '{{' "${TEACHER_HTML}"; then
  print_marker "PHASE26_TEACHER_HOME_JS_TEMPLATE_CLEAN" "false"
else
  print_marker "PHASE26_TEACHER_HOME_JS_TEMPLATE_CLEAN" "true"
fi

echo
echo "[step] teacher results page"
RESULTS_HTML="${TMP_DIR}/teacher-results.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/results" "${RESULTS_HTML}")"
expect_status "PHASE26_TEACHER_RESULTS_PAGE_200" "${STATUS}" "200"
grep -q 'data-marker="teacher-results-page"' "${RESULTS_HTML}" && print_marker "PHASE26_TEACHER_RESULTS_PAGE_MARKER" "true" || print_marker "PHASE26_TEACHER_RESULTS_PAGE_MARKER" "false"
grep -q 'data-marker="teacher-results-filters"' "${RESULTS_HTML}" && print_marker "PHASE26_TEACHER_RESULTS_FILTERS_MARKER" "true" || print_marker "PHASE26_TEACHER_RESULTS_FILTERS_MARKER" "false"
if grep -q '\${{' "${RESULTS_HTML}" || grep -q '{{' "${RESULTS_HTML}"; then
  print_marker "PHASE26_TEACHER_RESULTS_JS_TEMPLATE_CLEAN" "false"
else
  print_marker "PHASE26_TEACHER_RESULTS_JS_TEMPLATE_CLEAN" "true"
fi

echo
echo "[step] teacher overview API"
OVERVIEW_JSON="${TMP_DIR}/overview.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/overview" "${OVERVIEW_JSON}")"
expect_status "PHASE26_OVERVIEW_API_200" "${STATUS}" "200"
json_has_keys "${OVERVIEW_JSON}" success teacher metrics latest_results classroom_summaries todo_items >/dev/null 2>&1 && print_marker "PHASE26_OVERVIEW_SHAPE" "true" || print_marker "PHASE26_OVERVIEW_SHAPE" "false"
python -c '
import json
import sys

required = {
    "classroom_count", "total_result_count", "recent_result_count",
    "raw_count", "reviewed_count", "archived_count",
    "avg_feedback_score", "avg_attention_score", "avg_response_score"
}
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
metrics = payload.get("metrics") or {}
print("PHASE26_OVERVIEW_METRICS_SHAPE=" + ("true" if required.issubset(metrics) else "false"))
' "${OVERVIEW_JSON}"

echo
echo "[step] teacher results API"
TEACHER_RESULTS_JSON="${TMP_DIR}/api-results.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results?limit=20" "${TEACHER_RESULTS_JSON}")"
expect_status "PHASE26_RESULTS_API_200" "${STATUS}" "200"
json_result_items_shape "${TEACHER_RESULTS_JSON}" >/dev/null 2>&1 && print_marker "PHASE26_RESULTS_SHAPE" "true" || print_marker "PHASE26_RESULTS_SHAPE" "false"

echo
echo "[step] teacher results filters"
FILTER_JSON="${TMP_DIR}/api-results-classroom.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results?classroom_id=${CLASSROOM_ID}&limit=20" "${FILTER_JSON}")"
expect_status "PHASE26_RESULTS_CLASSROOM_FILTER_200" "${STATUS}" "200"
STATUS_JSON="${TMP_DIR}/api-results-status.json"
STATUS_CODE="$(curl_status GET "${API_BASE_URL}/api/teacher/results?status=raw&limit=20" "${STATUS_JSON}")"
expect_status "PHASE26_RESULTS_STATUS_FILTER_200" "${STATUS_CODE}" "200"
DAYS_JSON="${TMP_DIR}/api-results-days.json"
STATUS_CODE="$(curl_status GET "${API_BASE_URL}/api/teacher/results?days=7&limit=20" "${DAYS_JSON}")"
expect_status "PHASE26_RESULTS_DAYS_FILTER_200" "${STATUS_CODE}" "200"

echo
echo "[step] teacher results invalid status"
INVALID_JSON="${TMP_DIR}/api-results-invalid.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results?status=bad_status" "${INVALID_JSON}")"
expect_status "PHASE26_RESULTS_INVALID_STATUS_400" "${STATUS}" "400"

echo
echo "[step] dashboard deep link"
DASHBOARD_HTML="${TMP_DIR}/dashboard-result.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD_HTML}")"
expect_status "PHASE26_DASHBOARD_DEEPLINK_200" "${STATUS}" "200"
grep -q "data-initial-result-id=\"${RESULT_ID}\"" "${DASHBOARD_HTML}" && print_marker "PHASE26_DASHBOARD_DEEPLINK_MARKER" "true" || print_marker "PHASE26_DASHBOARD_DEEPLINK_MARKER" "false"

echo
echo "[step] phase 2.5 regression"
DETAIL_JSON="${TMP_DIR}/phase25-detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESULT_ID}" "${DETAIL_JSON}")"
expect_status "PHASE26_PHASE25_DETAIL_200" "${STATUS}" "200"
json_has_keys "${DETAIL_JSON}" success result >/dev/null 2>&1 && print_marker "PHASE26_PHASE25_DETAIL_SHAPE" "true" || print_marker "PHASE26_PHASE25_DETAIL_SHAPE" "false"
DASHBOARD_DEFAULT_HTML="${TMP_DIR}/dashboard-default.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard" "${DASHBOARD_DEFAULT_HTML}")"
expect_status "PHASE26_PHASE25_DASHBOARD_200" "${STATUS}" "200"
grep -q 'data-marker="attention-activity-chart"' "${DASHBOARD_DEFAULT_HTML}" && print_marker "PHASE26_PHASE25_CHART_MARKER" "true" || print_marker "PHASE26_PHASE25_CHART_MARKER" "false"
grep -q 'data-marker="attention-activity-chart"' "${DASHBOARD_DEFAULT_HTML}" && print_marker "PHASE26_DASHBOARD_ATTENTION_ACTIVITY_CHART" "true" || print_marker "PHASE26_DASHBOARD_ATTENTION_ACTIVITY_CHART" "false"
grep -q 'data-marker="stage-distribution-chart"' "${DASHBOARD_DEFAULT_HTML}" && print_marker "PHASE26_DASHBOARD_STAGE_CHART" "true" || print_marker "PHASE26_DASHBOARD_STAGE_CHART" "false"
grep -q 'data-marker="zone-performance-chart"' "${DASHBOARD_DEFAULT_HTML}" && print_marker "PHASE26_DASHBOARD_ZONE_CHART" "true" || print_marker "PHASE26_DASHBOARD_ZONE_CHART" "false"
grep -q 'data-marker="event-distribution-chart"' "${DASHBOARD_DEFAULT_HTML}" && print_marker "PHASE26_DASHBOARD_EVENT_CHART" "true" || print_marker "PHASE26_DASHBOARD_EVENT_CHART" "false"
if grep -q '\${{' "${DASHBOARD_DEFAULT_HTML}" || grep -q '{{' "${DASHBOARD_DEFAULT_HTML}"; then
  print_marker "PHASE26_DASHBOARD_JS_TEMPLATE_CLEAN" "false"
else
  print_marker "PHASE26_DASHBOARD_JS_TEMPLATE_CLEAN" "true"
fi

echo
echo "[step] phase 1/2 read regression"
LATEST_JSON="${TMP_DIR}/latest.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/latest-interaction-result" "${LATEST_JSON}")"
expect_status "PHASE26_LEGACY_LATEST_200" "${STATUS}" "200"
RECENT_JSON="${TMP_DIR}/legacy-recent.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/recent-interaction-results?limit=5" "${RECENT_JSON}")"
expect_status "PHASE26_LEGACY_RECENT_200" "${STATUS}" "200"

echo
echo "[done] Phase 2.6 teacher home validation completed"
