#!/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8011}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"

echo "[info] BASE_URL=${BASE_URL}"
echo "[info] CLASSROOM_ID=${CLASSROOM_ID}"

echo "[step] Health check"
curl --fail --silent --show-error "${BASE_URL}/health"
echo

echo "[step] Recent results"
curl --fail --silent --show-error "${BASE_URL}/api/recent-interaction-results"
echo

echo "[step] Recent results filtered by classroom"
curl --fail --silent --show-error "${BASE_URL}/api/recent-interaction-results?classroom_id=${CLASSROOM_ID}"
echo

echo "[step] Dashboard headers"
curl --fail --silent --show-error --head "${BASE_URL}/dashboard?classroom_id=${CLASSROOM_ID}"
echo

echo "[step] Dashboard content markers"
dashboard_html="$(curl --fail --silent --show-error "${BASE_URL}/dashboard?classroom_id=${CLASSROOM_ID}")"
printf '%s' "${dashboard_html}" | grep -q "Teacher Results Center"
printf '%s' "${dashboard_html}" | grep -q "Recent Classroom Results"
printf '%s' "${dashboard_html}" | grep -q "Filter by classroom_id"
printf '%s' "${dashboard_html}" | grep -q "Region / Heat Summary"
echo "[ok] Dashboard contains expected markers"
