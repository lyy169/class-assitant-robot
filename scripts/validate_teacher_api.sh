#!/bin/bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
TEACHER_USERNAME="${TEACHER_USERNAME:-teacher_101}"
TEACHER_PASSWORD="${TEACHER_PASSWORD:-teacher-change-me}"
LIMIT="${LIMIT:-5}"

TMP_LOGIN="$(mktemp)"
TMP_SESSIONS="$(mktemp)"

cleanup() {
  rm -f "${TMP_LOGIN}" "${TMP_SESSIONS}"
}

trap cleanup EXIT

echo "[step] teacher login"
curl -fsS "${API_BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${TEACHER_USERNAME}\",\"password\":\"${TEACHER_PASSWORD}\"}" \
  -o "${TMP_LOGIN}"

TEACHER_TOKEN="$(python3 - "${TMP_LOGIN}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    print(json.load(handle)["access_token"])
PY
)"

echo "[step] teacher sessions"
curl -fsS "${API_BASE_URL}/api/teacher/sessions" \
  -H "Authorization: Bearer ${TEACHER_TOKEN}" \
  -o "${TMP_SESSIONS}"
cat "${TMP_SESSIONS}"

FIRST_ANALYSIS_ID="$(python3 - "${TMP_SESSIONS}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)

sessions = payload.get("sessions") or []
print(sessions[0].get("analysis_id", "") if sessions else "")
PY
)"

if [ -n "${FIRST_ANALYSIS_ID}" ]; then
  echo
  echo "[step] teacher session detail"
  curl -i "${API_BASE_URL}/api/teacher/sessions/${FIRST_ANALYSIS_ID}" \
    -H "Authorization: Bearer ${TEACHER_TOKEN}"
else
  echo
  echo "[info] no teacher sessions available; skipping session detail check"
fi

echo
echo "[step] teacher trends"
curl -i "${API_BASE_URL}/api/teacher/trends?limit=${LIMIT}" \
  -H "Authorization: Bearer ${TEACHER_TOKEN}"

echo
echo "[done] teacher API validation completed"
