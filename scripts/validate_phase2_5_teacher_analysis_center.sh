#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-cls_20260417_101_001}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase25-validation-$$"

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
  local name="$1"
  local value="$2"
  echo "${name}=${value}"
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

path = sys.argv[1]
keys = sys.argv[2:]
with open(path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)
current = payload.get("result", payload)
missing = [key for key in keys if key not in current]
if missing:
    print("missing:" + ",".join(missing))
    sys.exit(1)
print("ok")
' "${file}" "$@"
}

json_items_non_sample() {
  local file="$1"
  python -c '
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
items = payload.get("items") or payload.get("results") or []
fallback = payload.get("fallback_to_sample")
if fallback is False and isinstance(items, list):
    print("ok")
else:
    print("bad")
    sys.exit(1)
' "${file}"
}

echo
echo "[step] demo video static route"
VIDEO_SAMPLE="${TMP_DIR}/video-sample.bin"
VIDEO_STATUS="$(curl -sS -r 0-0 -o "${VIDEO_SAMPLE}" -w "%{http_code}" "${API_BASE_URL}/uploads/video.mp4")"
if [ "${VIDEO_STATUS}" = "200" ] || [ "${VIDEO_STATUS}" = "206" ]; then
  print_marker "PHASE25_UPLOADS_VIDEO_MP4_SERVED" "true"
else
  print_marker "PHASE25_UPLOADS_VIDEO_MP4_SERVED" "false expected_200_or_206_got_${VIDEO_STATUS}"
fi

echo
echo "[step] teacher recent"
RECENT_JSON="${TMP_DIR}/recent.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/recent?limit=10" "${RECENT_JSON}")"
expect_status "PHASE25_RECENT_STATUS_200" "${STATUS}" "200"
json_items_non_sample "${RECENT_JSON}" >/dev/null 2>&1 && print_marker "PHASE25_RECENT_FALLBACK_FALSE" "true" || print_marker "PHASE25_RECENT_FALLBACK_FALSE" "false"

echo
echo "[step] teacher recent classroom filter"
RECENT_CLASSROOM_JSON="${TMP_DIR}/recent-classroom.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/recent?classroom_id=${CLASSROOM_ID}&limit=10" "${RECENT_CLASSROOM_JSON}")"
expect_status "PHASE25_RECENT_CLASSROOM_STATUS_200" "${STATUS}" "200"

echo
echo "[step] teacher classrooms"
CLASSROOMS_JSON="${TMP_DIR}/classrooms.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/classrooms" "${CLASSROOMS_JSON}")"
expect_status "PHASE25_CLASSROOMS_STATUS_200" "${STATUS}" "200"
json_has_keys "${CLASSROOMS_JSON}" success items >/dev/null 2>&1 && print_marker "PHASE25_CLASSROOMS_SHAPE" "true" || print_marker "PHASE25_CLASSROOMS_SHAPE" "false"

echo
echo "[step] teacher detail unified structure"
DETAIL_JSON="${TMP_DIR}/detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESULT_ID}" "${DETAIL_JSON}")"
expect_status "PHASE25_DETAIL_STATUS_200" "${STATUS}" "200"
json_has_keys "${DETAIL_JSON}" video summary timeline stage_distribution zones events raw_path raw_payload >/dev/null 2>&1 && print_marker "PHASE25_DETAIL_UNIFIED_STRUCTURE" "true" || print_marker "PHASE25_DETAIL_UNIFIED_STRUCTURE" "false"

python -c '
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        payload = json.load(handle)
except Exception:
    print("PHASE25_DETAIL_VIDEO_EVENTS_TIMELINE=false")
    print("PHASE25_DETAIL_VIDEO_PLAYABLE=false")
    print("PHASE25_DETAIL_VIDEO_URL_UPLOADS=false")
    sys.exit(0)

result = payload.get("result") or {}
video = result.get("video") or {}
events = result.get("events") or []
timeline = result.get("timeline") or {}
shape_ok = (
    video.get("status") in {"playable", "pending", "missing"}
    and isinstance(events, list)
    and "attention_curve" in timeline
    and "activity_curve" in timeline
)
video_url = video.get("video_url") or ""
print("PHASE25_DETAIL_VIDEO_EVENTS_TIMELINE=" + ("true" if shape_ok else "false"))
print("PHASE25_DETAIL_VIDEO_PLAYABLE=" + ("true" if video.get("status") == "playable" else "false"))
print("PHASE25_DETAIL_VIDEO_URL_UPLOADS=" + ("true" if video_url.startswith("/uploads/") else "false"))
' "${DETAIL_JSON}"

echo
echo "[step] missing result"
MISSING_JSON="${TMP_DIR}/missing.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/not_exists_phase25" "${MISSING_JSON}")"
expect_status "PHASE25_MISSING_DETAIL_404" "${STATUS}" "404"

echo
echo "[step] status update reviewed"
STATUS_REVIEWED_JSON="${TMP_DIR}/status-reviewed.json"
printf '{"status":"reviewed"}' > "${STATUS_REVIEWED_JSON}"
PATCH_JSON="${TMP_DIR}/patch-reviewed.json"
STATUS="$(curl_status PATCH "${API_BASE_URL}/api/teacher/results/${RESULT_ID}/status" "${PATCH_JSON}" -H 'Content-Type:application/json' -d @"${STATUS_REVIEWED_JSON}")"
expect_status "PHASE25_PATCH_REVIEWED_STATUS_200" "${STATUS}" "200"
python -c '
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    payload = json.load(handle)
status = (payload.get("result") or {}).get("status")
print("PHASE25_PATCH_REVIEWED_VALUE=" + ("true" if status == "reviewed" else "false"))
' "${PATCH_JSON}"

echo
echo "[step] status update invalid"
STATUS_BAD_JSON="${TMP_DIR}/status-bad.json"
printf '{"status":"bad_status"}' > "${STATUS_BAD_JSON}"
PATCH_BAD_JSON="${TMP_DIR}/patch-bad.json"
STATUS="$(curl_status PATCH "${API_BASE_URL}/api/teacher/results/${RESULT_ID}/status" "${PATCH_BAD_JSON}" -H 'Content-Type:application/json' -d @"${STATUS_BAD_JSON}")"
expect_status "PHASE25_PATCH_INVALID_STATUS_400" "${STATUS}" "400"

echo
echo "[step] legacy phase1/phase2 read APIs"
LATEST_JSON="${TMP_DIR}/latest.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/latest-interaction-result" "${LATEST_JSON}")"
expect_status "PHASE25_LEGACY_LATEST_STATUS_200" "${STATUS}" "200"
LEGACY_RECENT_JSON="${TMP_DIR}/legacy-recent.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/recent-interaction-results?limit=5&classroom_id=${CLASSROOM_ID}" "${LEGACY_RECENT_JSON}")"
expect_status "PHASE25_LEGACY_RECENT_STATUS_200" "${STATUS}" "200"
json_items_non_sample "${LEGACY_RECENT_JSON}" >/dev/null 2>&1 && print_marker "PHASE25_LEGACY_RECENT_FALLBACK_FALSE" "true" || print_marker "PHASE25_LEGACY_RECENT_FALLBACK_FALSE" "false"

if [ "${RUN_UPLOAD_REGRESSION:-0}" = "1" ]; then
  echo
  echo "[step] optional upload regression"
  if bash scripts/upload_real_result.sh >/tmp/phase25-upload-regression.log 2>&1; then
    print_marker "PHASE25_UPLOAD_REGRESSION" "true"
  else
    print_marker "PHASE25_UPLOAD_REGRESSION" "false"
    cat /tmp/phase25-upload-regression.log
  fi
else
  print_marker "PHASE25_UPLOAD_REGRESSION" "skipped_set_RUN_UPLOAD_REGRESSION_1"
fi

echo
echo "[step] dashboard html markers"
DASHBOARD_HTML="${TMP_DIR}/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?classroom_id=${CLASSROOM_ID}&limit=10" "${DASHBOARD_HTML}")"
expect_status "PHASE25_DASHBOARD_STATUS_200" "${STATUS}" "200"
grep -q 'data-marker="teacher-analysis-center"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_TEACHER_CENTER_MARKER" "true" || print_marker "PHASE25_DASHBOARD_TEACHER_CENTER_MARKER" "false"
grep -q 'Teacher Console' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_TEACHER_CONSOLE" "true" || print_marker "PHASE25_DASHBOARD_TEACHER_CONSOLE" "false"
grep -q 'data-marker="data-pipeline-status"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_PIPELINE_MARKER" "true" || print_marker "PHASE25_DASHBOARD_PIPELINE_MARKER" "false"
grep -q 'data-marker="video-area"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_VIDEO_MARKER" "true" || print_marker "PHASE25_DASHBOARD_VIDEO_MARKER" "false"
grep -q 'data-marker="teaching-feedback-summary"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_FEEDBACK_MARKER" "true" || print_marker "PHASE25_DASHBOARD_FEEDBACK_MARKER" "false"
grep -q 'data-marker="key-event-list"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_EVENT_LIST_MARKER" "true" || print_marker "PHASE25_DASHBOARD_EVENT_LIST_MARKER" "false"
grep -q 'data-marker="attention-activity-chart"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_ATTENTION_ACTIVITY_CHART" "true" || print_marker "PHASE25_DASHBOARD_ATTENTION_ACTIVITY_CHART" "false"
grep -q 'data-marker="stage-distribution-chart"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_STAGE_CHART" "true" || print_marker "PHASE25_DASHBOARD_STAGE_CHART" "false"
grep -q 'data-marker="zone-performance-chart"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_ZONE_CHART" "true" || print_marker "PHASE25_DASHBOARD_ZONE_CHART" "false"
grep -q 'data-marker="event-distribution-chart"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_EVENT_CHART" "true" || print_marker "PHASE25_DASHBOARD_EVENT_CHART" "false"
grep -q 'No result selected' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_NO_RESULT_SELECTED_HIDDEN" "false" || print_marker "PHASE25_DASHBOARD_NO_RESULT_SELECTED_HIDDEN" "true"
grep -q 'Raw Detail Snapshot' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_RAW_SNAPSHOT_NOT_PRIMARY" "false" || print_marker "PHASE25_DASHBOARD_RAW_SNAPSHOT_NOT_PRIMARY" "true"
grep -q 'data-marker="debug-raw-data"' "${DASHBOARD_HTML}" && print_marker "PHASE25_DASHBOARD_DEBUG_COLLAPSE_MARKER" "true" || print_marker "PHASE25_DASHBOARD_DEBUG_COLLAPSE_MARKER" "false"

echo
echo "[done] Phase 2.5 teacher analysis center validation completed"
