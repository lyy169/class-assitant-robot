#!/bin/bash
set -euo pipefail

CLOUD_SRC_DIR="${CLOUD_SRC_DIR:-/root/video_project_src}"
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
CLASSROOM_ID="${CLASSROOM_ID:-}"
LIMIT="${LIMIT:-5}"
EXPECT_ANALYSIS_ID="${EXPECT_ANALYSIS_ID:-}"
SQLITE_PATH="${SQLITE_PATH:-${CLOUD_SRC_DIR}/cloud_backend/data/cloud_results.sqlite3}"
RAW_DIR="${RAW_DIR:-${CLOUD_SRC_DIR}/cloud_backend/data/raw}"

case "${LIMIT}" in
  ''|*[!0-9]*)
    echo "[error] LIMIT must be a positive integer" >&2
    exit 1
    ;;
esac

RECENT_URL="${API_BASE_URL%/}/api/recent-interaction-results?limit=${LIMIT}"
DASHBOARD_URL="${API_BASE_URL%/}/dashboard?limit=${LIMIT}"

if [ -n "${CLASSROOM_ID}" ]; then
  RECENT_URL="${RECENT_URL}&classroom_id=${CLASSROOM_ID}"
  DASHBOARD_URL="${DASHBOARD_URL}&classroom_id=${CLASSROOM_ID}"
fi

TMP_RECENT="$(mktemp)"
TMP_DASHBOARD="$(mktemp)"

cleanup() {
  rm -f "${TMP_RECENT}" "${TMP_DASHBOARD}"
}

trap cleanup EXIT

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] CLASSROOM_ID=${CLASSROOM_ID:-<none>}"
echo "[info] LIMIT=${LIMIT}"
echo "[info] EXPECT_ANALYSIS_ID=${EXPECT_ANALYSIS_ID:-<none>}"
echo "[info] SQLITE_PATH=${SQLITE_PATH}"
echo "[info] RAW_DIR=${RAW_DIR}"

echo "[step] check sqlite file"
if [ -f "${SQLITE_PATH}" ]; then
  ls -l "${SQLITE_PATH}"
else
  echo "[warn] sqlite file not found: ${SQLITE_PATH}"
fi

echo "[step] list newest raw files"
if [ -d "${RAW_DIR}" ]; then
  find "${RAW_DIR}" -maxdepth 2 -type f | sort | tail -n "${LIMIT}"
else
  echo "[warn] raw directory not found: ${RAW_DIR}"
fi

echo "[step] query recent API"
curl -fsS "${RECENT_URL}" -o "${TMP_RECENT}"

python3 - "${TMP_RECENT}" "${EXPECT_ANALYSIS_ID}" <<'PY'
import json
import sys

recent_path = sys.argv[1]
expect_analysis_id = sys.argv[2].strip()

with open(recent_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

results = payload.get("results") or []
print(f"RECENT_SUCCESS={payload.get('success')}")
print(f"RECENT_CLASSROOM_ID={payload.get('classroom_id')}")
print(f"RECENT_LIMIT={payload.get('limit')}")
print(f"RECENT_FALLBACK_TO_SAMPLE={payload.get('fallback_to_sample')}")
print(f"RECENT_RESULT_COUNT={len(results)}")

if expect_analysis_id:
    found = any((item.get("result") or {}).get("analysis_id") == expect_analysis_id for item in results)
    print(f"EXPECT_ANALYSIS_ID={expect_analysis_id}")
    print(f"EXPECT_ANALYSIS_ID_FOUND={found}")

for index, item in enumerate(results[:10], start=1):
    result = item.get("result") or {}
    summary = item.get("summary") or {}
    time_info = result.get("time") or {}
    analysis_id = result.get("analysis_id") or summary.get("analysis_id") or "unknown"
    source_kind = item.get("source_kind") or "unknown"
    generated_at = time_info.get("generated_at") or summary.get("generated_at") or "unknown"
    source_path = item.get("source_path") or "unknown"
    print(f"RECENT_{index}_ANALYSIS_ID={analysis_id}")
    print(f"RECENT_{index}_SOURCE_KIND={source_kind}")
    print(f"RECENT_{index}_GENERATED_AT={generated_at}")
    print(f"RECENT_{index}_SOURCE_PATH={source_path}")
PY

LATEST_ANALYSIS_ID="$(python3 - "${TMP_RECENT}" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)

results = payload.get("results") or []
if results:
    result = results[0].get("result") or {}
    print(result.get("analysis_id", ""))
PY
)"

echo "[step] query dashboard HTML"
curl -fsS "${DASHBOARD_URL}" -o "${TMP_DASHBOARD}"

if grep -Fq "Teacher Results Center" "${TMP_DASHBOARD}"; then
  echo "DASHBOARD_TITLE_FOUND=true"
else
  echo "DASHBOARD_TITLE_FOUND=false"
fi

if grep -Fq '<span class="badge">raw</span>' "${TMP_DASHBOARD}"; then
  echo "DASHBOARD_RAW_BADGE_FOUND=true"
else
  echo "DASHBOARD_RAW_BADGE_FOUND=false"
fi

if [ -n "${LATEST_ANALYSIS_ID}" ] && grep -Fq "${LATEST_ANALYSIS_ID}" "${TMP_DASHBOARD}"; then
  echo "DASHBOARD_LATEST_ANALYSIS_ID_FOUND=true"
  echo "DASHBOARD_LATEST_ANALYSIS_ID=${LATEST_ANALYSIS_ID}"
else
  echo "DASHBOARD_LATEST_ANALYSIS_ID_FOUND=false"
  echo "DASHBOARD_LATEST_ANALYSIS_ID=${LATEST_ANALYSIS_ID:-<none>}"
fi

if [ -n "${CLASSROOM_ID}" ] && grep -Fq "${CLASSROOM_ID}" "${TMP_DASHBOARD}"; then
  echo "DASHBOARD_CLASSROOM_FILTER_FOUND=true"
else
  echo "DASHBOARD_CLASSROOM_FILTER_FOUND=false"
fi

echo "[step] optional sqlite row check"
if command -v sqlite3 >/dev/null 2>&1 && [ -f "${SQLITE_PATH}" ]; then
  if [ -n "${EXPECT_ANALYSIS_ID}" ]; then
    sqlite3 "${SQLITE_PATH}" "select analysis_id, classroom_id, source_kind, generated_at from classroom_results where analysis_id = '${EXPECT_ANALYSIS_ID}' order by generated_at desc, created_at desc limit ${LIMIT};"
  else
    sqlite3 "${SQLITE_PATH}" "select analysis_id, classroom_id, source_kind, generated_at from classroom_results order by generated_at desc, created_at desc limit ${LIMIT};"
  fi
else
  echo "[warn] sqlite3 CLI not available or sqlite file missing; skipped row-level query"
fi
