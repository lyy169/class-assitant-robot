#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase28-validation-$$"

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

json_ingestion_keys_ok() {
  local file="$1"
  python -c '
import json
import sys
required = {"success", "filters", "overview", "pipeline", "devices", "recent_ingestions", "video_summary", "validation_hints"}
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
missing = required.difference(payload)
if missing:
    print("missing:" + ",".join(sorted(missing)))
    sys.exit(1)
if payload.get("success") is not True:
    print("success_not_true")
    sys.exit(1)
print("ok")
' "${file}"
}

json_video_standard_metadata_ok() {
  local file="$1"
  python -c '
import json
import sys
required_summary = {"standardized_present", "browser_compatible", "browser_incompatible", "transcode_failed"}
required_item = {"standardized_video_path", "standardized_video_present", "browser_compatible", "transcode_status", "transcode_error"}
with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
summary = payload.get("video_summary") or {}
missing_summary = required_summary.difference(summary)
if missing_summary:
    print("missing_summary:" + ",".join(sorted(missing_summary)))
    sys.exit(1)
items = payload.get("recent_ingestions") or []
if items:
    missing_item = required_item.difference(items[0])
    if missing_item:
        print("missing_item:" + ",".join(sorted(missing_item)))
        sys.exit(1)
print("ok")
' "${file}"
}

echo
echo "[step] admin ingestion page"
INGESTION_HTML="${TMP_DIR}/admin-ingestion.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/ingestion" "${INGESTION_HTML}")"
if [ "${STATUS}" = "200" ]; then PAGE_200=true; else PAGE_200=false; fi
grep -q 'data-marker="admin-ingestion-page"' "${INGESTION_HTML}" && PAGE_MARKER=true || PAGE_MARKER=false
grep -q 'data-marker="admin-ingestion-pipeline"' "${INGESTION_HTML}" && PIPELINE_MARKER=true || PIPELINE_MARKER=false
grep -q 'data-marker="admin-ingestion-devices"' "${INGESTION_HTML}" && DEVICES_MARKER=true || DEVICES_MARKER=false
grep -q 'data-marker="admin-ingestion-recent"' "${INGESTION_HTML}" && RECENT_MARKER=true || RECENT_MARKER=false
grep -q 'data-marker="admin-ingestion-video-summary"' "${INGESTION_HTML}" && VIDEO_MARKER=true || VIDEO_MARKER=false
grep -q 'data-marker="admin-ingestion-validation-hints"' "${INGESTION_HTML}" && HINTS_MARKER=true || HINTS_MARKER=false
all_true_marker "PHASE28_ADMIN_INGESTION_PAGE_OK" "${PAGE_200}" "${PAGE_MARKER}" "${PIPELINE_MARKER}" "${DEVICES_MARKER}" "${RECENT_MARKER}" "${VIDEO_MARKER}" "${HINTS_MARKER}"

echo
echo "[step] admin ingestion API"
INGESTION_JSON="${TMP_DIR}/admin-ingestion.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/ingestion?classroom_id=${CLASSROOM_ID}&limit=20" "${INGESTION_JSON}")"
if [ "${STATUS}" = "200" ]; then API_200=true; else API_200=false; fi
print_marker "PHASE28_ADMIN_INGESTION_API_OK" "${API_200}"
json_ingestion_keys_ok "${INGESTION_JSON}" >/dev/null 2>&1 && KEYS_OK=true || KEYS_OK=false
print_marker "PHASE28_ADMIN_INGESTION_KEYS_OK" "${KEYS_OK}"
json_video_standard_metadata_ok "${INGESTION_JSON}" >/dev/null 2>&1 && VIDEO_STANDARD_KEYS_OK=true || VIDEO_STANDARD_KEYS_OK=false
print_marker "PHASE281_VIDEO_STANDARD_METADATA_KEYS_OK" "${VIDEO_STANDARD_KEYS_OK}"

echo
echo "[step] phase 2.7 admin regression"
ADMIN_HTML="${TMP_DIR}/admin.html"
ADMIN_CLASSROOMS_HTML="${TMP_DIR}/admin-classrooms.html"
ADMIN_TEACHERS_HTML="${TMP_DIR}/admin-teachers.html"
ADMIN_RESULTS_HTML="${TMP_DIR}/admin-results.html"
STATUS_ADMIN="$(curl_status GET "${API_BASE_URL}/admin" "${ADMIN_HTML}")"
STATUS_CLASSROOMS="$(curl_status GET "${API_BASE_URL}/admin/classrooms" "${ADMIN_CLASSROOMS_HTML}")"
STATUS_TEACHERS="$(curl_status GET "${API_BASE_URL}/admin/teachers" "${ADMIN_TEACHERS_HTML}")"
STATUS_RESULTS="$(curl_status GET "${API_BASE_URL}/admin/results" "${ADMIN_RESULTS_HTML}")"
[ "${STATUS_ADMIN}" = "200" ] && A=true || A=false
[ "${STATUS_CLASSROOMS}" = "200" ] && C=true || C=false
[ "${STATUS_TEACHERS}" = "200" ] && T=true || T=false
[ "${STATUS_RESULTS}" = "200" ] && R=true || R=false
all_true_marker "PHASE27_ADMIN_REGRESSION_OK" "${A}" "${C}" "${T}" "${R}"

echo
echo "[step] phase 2.6 teacher regression"
TEACHER_HTML="${TMP_DIR}/teacher.html"
TEACHER_RESULTS_HTML="${TMP_DIR}/teacher-results.html"
STATUS_TEACHER="$(curl_status GET "${API_BASE_URL}/teacher" "${TEACHER_HTML}")"
STATUS_TEACHER_RESULTS="$(curl_status GET "${API_BASE_URL}/teacher/results" "${TEACHER_RESULTS_HTML}")"
[ "${STATUS_TEACHER}" = "200" ] && T1=true || T1=false
[ "${STATUS_TEACHER_RESULTS}" = "200" ] && T2=true || T2=false
all_true_marker "PHASE26_TEACHER_REGRESSION_OK" "${T1}" "${T2}"

echo
echo "[step] phase 2.5 dashboard regression"
DASHBOARD_HTML="${TMP_DIR}/dashboard.html"
STATUS_DASHBOARD="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "${DASHBOARD_HTML}")"
[ "${STATUS_DASHBOARD}" = "200" ] && D1=true || D1=false
grep -q 'data-marker="attention-activity-chart"' "${DASHBOARD_HTML}" && D2=true || D2=false
all_true_marker "PHASE25_DASHBOARD_REGRESSION_OK" "${D1}" "${D2}"

echo
echo "[step] phase 1/2 API regression"
LATEST_JSON="${TMP_DIR}/latest.json"
RECENT_JSON="${TMP_DIR}/recent.json"
STATUS_LATEST="$(curl_status GET "${API_BASE_URL}/api/latest-interaction-result" "${LATEST_JSON}")"
STATUS_RECENT="$(curl_status GET "${API_BASE_URL}/api/recent-interaction-results?limit=5" "${RECENT_JSON}")"
[ "${STATUS_LATEST}" = "200" ] && L=true || L=false
[ "${STATUS_RECENT}" = "200" ] && RR=true || RR=false
all_true_marker "PHASE12_API_REGRESSION_OK" "${L}" "${RR}"

echo
echo "[done] Phase 2.8 ingestion status validation completed"
