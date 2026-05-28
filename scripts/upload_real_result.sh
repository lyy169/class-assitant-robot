#!/bin/bash
set -u

JSON_FILE="${JSON_FILE:-/root/video_project_src/cls_20260417_101_001.json}"
API_URL="${API_URL:-http://127.0.0.1:8011/api/interaction-results}"
TMP_BODY="$(mktemp)"

cleanup() {
  rm -f "${TMP_BODY}"
}

trap cleanup EXIT

if [ ! -f "${JSON_FILE}" ]; then
  echo "FAILED"
  echo "JSON file not found: ${JSON_FILE}"
  exit 1
fi

HTTP_CODE="$(curl -sS -o "${TMP_BODY}" -w "%{http_code}" \
  -X POST "${API_URL}" \
  -H "Content-Type: application/json" \
  --data-binary "@${JSON_FILE}")"

echo "HTTP_STATUS=${HTTP_CODE}"
echo "RESPONSE_BODY="
cat "${TMP_BODY}"
echo

if [ "${HTTP_CODE}" -ge 200 ] && [ "${HTTP_CODE}" -lt 300 ]; then
  echo "SUCCESS"
  exit 0
fi

echo "FAILED"
exit 1
