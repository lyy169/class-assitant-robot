#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
SAMPLE_FILE="${SAMPLE_FILE:-samples/phase3_2_enhanced_result.json}"
TMP_DIR="${TMPDIR:-/tmp}/phase32-cloud-compat-$$"

mkdir -p "${TMP_DIR}"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] SAMPLE_FILE=${SAMPLE_FILE}"

curl_status() {
  local method="$1"
  local url="$2"
  local output="$3"
  shift 3
  curl -sS -o "${output}" -w "%{http_code}" -X "${method}" "$@" "${url}"
}

print_marker() {
  echo "$1=$2"
}

all_true_marker() {
  local name="$1"
  shift
  local ok="true"
  for value in "$@"; do
    if [ "${value}" != "true" ]; then
      ok="false"
    fi
  done
  print_marker "${name}" "${ok}"
}

json_saved_path() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); print(p.get("saved_path") or "")' "$1"
}

json_analysis_id() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); print(p.get("analysis_id") or "")' "$1"
}

json_success_ok() {
  python -c 'import json,sys; p=json.load(open(sys.argv[1],encoding="utf-8")); sys.exit(0 if p.get("success") is True else 1)' "$1"
}

json_detail_enhanced_ok() {
  python -c '
import json, sys
p = json.load(open(sys.argv[1], encoding="utf-8"))
result = p.get("result") or {}
raw = result.get("raw_payload") or result.get("result") or {}
phase32 = result.get("phase32") or {}
def present(key):
    value = result.get(key)
    if value in (None, "", [], {}):
        value = phase32.get(key)
    if value in (None, "", [], {}):
        value = raw.get(key)
    return value not in (None, "", [], {})
required = ["quality_metrics", "score_breakdown", "enhanced_issues"]
sys.exit(0 if p.get("success") is True and all(present(key) for key in required) else 1)
' "$1"
}

if [ ! -f "${SAMPLE_FILE}" ]; then
  echo "[error] sample file not found: ${SAMPLE_FILE}"
  print_marker "PHASE32_CLOUD_UPLOAD_OK" "false"
  print_marker "PHASE32_RAW_PRESERVED" "false"
  print_marker "PHASE32_DETAIL_ENHANCED_FIELDS_PRESENT" "false"
  print_marker "PHASE32_DASHBOARD_OK" "false"
  print_marker "PHASE32_REPORTS_OK" "false"
  exit 0
fi

RESULT_ID="$(json_analysis_id "${SAMPLE_FILE}")"
echo "[info] RESULT_ID=${RESULT_ID}"

echo
echo "[step] upload enhanced JSON"
UPLOAD_JSON="${TMP_DIR}/upload.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/interaction-results" "${UPLOAD_JSON}" -H "Content-Type: application/json" --data-binary "@${SAMPLE_FILE}")"
if [ "${STATUS}" = "200" ] && json_success_ok "${UPLOAD_JSON}"; then
  CLOUD_UPLOAD_OK=true
else
  CLOUD_UPLOAD_OK=false
fi
print_marker "PHASE32_CLOUD_UPLOAD_OK" "${CLOUD_UPLOAD_OK}"

SAVED_PATH="$(json_saved_path "${UPLOAD_JSON}")"
echo "[info] saved_path=${SAVED_PATH}"

if [ -n "${SAVED_PATH}" ] && [ -f "${SAVED_PATH}" ] && grep -q '"analysis_version": "3.2"' "${SAVED_PATH}"; then
  RAW_PRESERVED=true
else
  RAW_PRESERVED=false
fi
print_marker "PHASE32_RAW_PRESERVED" "${RAW_PRESERVED}"

echo
echo "[step] teacher login and detail API"
TEACHER_COOKIE="${TMP_DIR}/teacher.cookie"
TEACHER_LOGIN="${TMP_DIR}/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "${TEACHER_LOGIN}" -c "${TEACHER_COOKIE}" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
if [ "${STATUS}" = "200" ] && json_success_ok "${TEACHER_LOGIN}"; then
  TEACHER_LOGIN_OK=true
else
  TEACHER_LOGIN_OK=false
fi
print_marker "PHASE32_TEACHER_LOGIN_OK" "${TEACHER_LOGIN_OK}"

DETAIL_JSON="${TMP_DIR}/detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESULT_ID}" "${DETAIL_JSON}" -b "${TEACHER_COOKIE}")"
if [ "${STATUS}" = "200" ] && json_detail_enhanced_ok "${DETAIL_JSON}"; then
  DETAIL_ENHANCED_OK=true
else
  DETAIL_ENHANCED_OK=false
fi
print_marker "PHASE32_DETAIL_ENHANCED_FIELDS_PRESENT" "${DETAIL_ENHANCED_OK}"

echo
echo "[step] dashboard and reports pages"
DASHBOARD_HTML="${TMP_DIR}/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD_HTML}" -b "${TEACHER_COOKIE}")"
if [ "${STATUS}" = "200" ] && grep -q 'data-marker="teacher-analysis-center"' "${DASHBOARD_HTML}"; then
  DASHBOARD_OK=true
else
  DASHBOARD_OK=false
fi
print_marker "PHASE32_DASHBOARD_OK" "${DASHBOARD_OK}"

REPORTS_HTML="${TMP_DIR}/reports.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/reports?result_id=${RESULT_ID}" "${REPORTS_HTML}" -b "${TEACHER_COOKIE}")"
if [ "${STATUS}" = "200" ] && grep -q 'data-marker="phase30-teacher-report-detail-page"' "${REPORTS_HTML}"; then
  REPORTS_OK=true
else
  REPORTS_OK=false
fi
print_marker "PHASE32_REPORTS_OK" "${REPORTS_OK}"

all_true_marker "PHASE32_REGRESSION_OK" "${CLOUD_UPLOAD_OK}" "${RAW_PRESERVED}" "${TEACHER_LOGIN_OK}" "${DETAIL_ENHANCED_OK}" "${DASHBOARD_OK}" "${REPORTS_OK}"

echo
echo "[done] Phase 3.2 cloud enhanced JSON compatibility validation completed"
