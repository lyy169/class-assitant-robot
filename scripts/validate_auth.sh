#!/bin/bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin-change-me}"
TEACHER_USERNAME="${TEACHER_USERNAME:-teacher_101}"
TEACHER_PASSWORD="${TEACHER_PASSWORD:-teacher-change-me}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"

TMP_LOGIN="$(mktemp)"
TMP_ME="$(mktemp)"
TMP_CREATE="$(mktemp)"
TMP_LIST="$(mktemp)"

cleanup() {
  rm -f "${TMP_LOGIN}" "${TMP_ME}" "${TMP_CREATE}" "${TMP_LIST}"
}

trap cleanup EXIT

echo "[step] admin login"
curl -fsS "${API_BASE_URL}/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${ADMIN_PASSWORD}\"}" \
  -o "${TMP_LOGIN}"

ADMIN_TOKEN="$(python3 - "${TMP_LOGIN}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    print(json.load(handle)["access_token"])
PY
)"

echo "[info] admin token acquired"

echo "[step] current user"
curl -fsS "${API_BASE_URL}/api/auth/me" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -o "${TMP_ME}"
cat "${TMP_ME}"
echo

echo "[step] create teacher user"
curl -fsS "${API_BASE_URL}/api/admin/users" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d "{\"username\":\"${TEACHER_USERNAME}\",\"password\":\"${TEACHER_PASSWORD}\",\"role\":\"teacher\",\"classroom_id\":\"${CLASSROOM_ID}\"}" \
  -o "${TMP_CREATE}"
cat "${TMP_CREATE}"
echo

echo "[step] list users"
curl -fsS "${API_BASE_URL}/api/admin/users" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -o "${TMP_LIST}"
cat "${TMP_LIST}"
echo

echo "[done] auth validation completed"
