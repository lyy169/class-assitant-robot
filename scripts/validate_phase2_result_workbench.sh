#!/bin/bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] RESULT_ID=${RESULT_ID}"

echo "[step] recent default"
curl -i "${API_BASE_URL}/api/teacher/results/recent"

echo
echo "[step] recent limit"
curl -i "${API_BASE_URL}/api/teacher/results/recent?limit=5"

echo
echo "[step] recent classroom filter"
curl -i "${API_BASE_URL}/api/teacher/results/recent?classroom_id=classroom_101"

echo
echo "[step] recent status filter"
curl -i "${API_BASE_URL}/api/teacher/results/recent?status=raw"

echo
echo "[step] classrooms"
curl -i "${API_BASE_URL}/api/teacher/classrooms"

echo
echo "[step] result detail"
curl -i "${API_BASE_URL}/api/teacher/results/${RESULT_ID}"

echo
echo "[step] patch status reviewed"
curl -i -X PATCH "${API_BASE_URL}/api/teacher/results/${RESULT_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"reviewed"}'

echo
echo "[step] patch invalid status should return 400"
curl -i -X PATCH "${API_BASE_URL}/api/teacher/results/${RESULT_ID}/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"bad_status"}'

echo
echo "[step] missing result should return 404"
curl -i "${API_BASE_URL}/api/teacher/results/not_exists"

echo
echo "[step] dashboard"
curl -i "${API_BASE_URL}/dashboard?classroom_id=classroom_101&status=reviewed&limit=10"

echo
echo "[step] dashboard chart markers"
DASHBOARD_HTML="$(mktemp)"
curl -fsS "${API_BASE_URL}/dashboard?classroom_id=classroom_101&status=reviewed&limit=10" -o "${DASHBOARD_HTML}"
grep -q "Vue + ECharts" "${DASHBOARD_HTML}" && echo "DASHBOARD_VUE_ECHARTS_MARKER=true"
grep -q "Score Trend" "${DASHBOARD_HTML}" && echo "DASHBOARD_SCORE_TREND_CHART=true"
grep -q "Status Distribution" "${DASHBOARD_HTML}" && echo "DASHBOARD_STATUS_DISTRIBUTION_CHART=true"
grep -q "Classroom Statistics" "${DASHBOARD_HTML}" && echo "DASHBOARD_CLASSROOM_STAT_CHART=true"
grep -q "Event Distribution" "${DASHBOARD_HTML}" && echo "DASHBOARD_EVENT_DISTRIBUTION_CHART=true"
rm -f "${DASHBOARD_HTML}"

echo
echo "[done] Phase 2 result workbench validation commands completed"
