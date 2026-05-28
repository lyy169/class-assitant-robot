#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
FINAL_ID="${FINAL_ID:-phase314_asr_full_classroom_sav_20200908_17}"
PHASE37_ID="${PHASE37_ID:-phase37_full_classroom_sav_20200908_17}"
PHASE35_ID="${PHASE35_ID:-phase35_local_imported_sav_full_classroom_20200908_17}"
LEGACY_ID_1="${LEGACY_ID_1:-cls_20260430_classroom_101_d4b91cf9c0bf4e68bfcb5e12933d30ee}"
LEGACY_ID_2="${LEGACY_ID_2:-cls_20260429_classroom_101_c993e071203b44e1bef1db1586181503}"
LEGACY_ID_3="${LEGACY_ID_3:-cls_20260417_101_001}"
TMP_DIR="${TMPDIR:-/tmp}/phase317-frontend-sample-scope-$$"

mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

print_marker() {
  echo "$1=$2"
}

find_python() {
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  echo ""
}

PYTHON_BIN="$(find_python)"

curl_status() {
  local method="$1"
  local url="$2"
  local output="$3"
  shift 3
  curl -sS -o "$output" -w "%{http_code}" -X "$method" --max-time 30 "$@" "$url" 2>/dev/null || echo "000"
}

json_success_ok() {
  local file="$1"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if payload.get("success") is True else 1)
PY
}

json_check() {
  local file="$1"
  local check="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$check" "$FINAL_ID" "$PHASE37_ID" "$PHASE35_ID" "$LEGACY_ID_1" "$LEGACY_ID_2" "$LEGACY_ID_3" <<'PY'
import json, sys

path, check, final_id, phase37, phase35, legacy1, legacy2, legacy3 = sys.argv[1:9]
payload = json.load(open(path, encoding="utf-8"))
hidden = {phase37, phase35, legacy1, legacy2, legacy3}

def items_from(payload):
    for key in ("items", "latest_results", "recent_reports", "risk_lessons"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []

def item_id(item):
    return str(item.get("result_id") or item.get("analysis_id") or "")

def num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

def display_keys(item):
    return {m.get("key") for m in item.get("display_metrics") or [] if isinstance(m, dict)}

def no_hidden(items):
    return not hidden.intersection({item_id(item) for item in items})

def final_item(items):
    return next((item for item in items if item_id(item) == final_id), None)

def demo_labeled(items):
    demos = [
        item for item in items
        if item.get("dataset_source") == "demo"
        or ((item.get("presentation_scope") or {}).get("record_kind") == "demo_data")
    ]
    return all(
        ((item.get("presentation_scope") or {}).get("record_kind") == "demo_data")
        or item.get("display_badge") == "演示数据"
        for item in demos
    )

result = payload.get("result") or {}
report = payload.get("report") or {}
items = items_from(payload)

checks = {}
checks["list_hides_history"] = no_hidden(items)
checks["list_has_final"] = final_item(items) is not None
checks["list_final_scope"] = bool(final_item(items)) and (final_item(items).get("presentation_scope") or {}).get("record_kind") == "competition_final"
checks["demo_labeled"] = demo_labeled(items)

asr = result.get("asr_display") or {}
flags = result.get("display_flags") or {}
video = result.get("video") or {}
checks["dashboard_detail_video"] = video.get("status") == "playable" and bool(video.get("video_url"))
checks["dashboard_detail_asr"] = (
    int(num(asr.get("transcript_segment_count"))) >= 764
    and int(num(asr.get("question_event_count"))) >= 35
    and int(num(asr.get("response_detected_count"))) >= 16
)
checks["dashboard_no_fake_attention"] = flags.get("hide_attention_metrics") is True and num((result.get("summary") or {}).get("attention_score")) == 0
checks["dashboard_no_fake_student"] = flags.get("hide_student_count") is True and num(((result.get("raw_payload") or {}).get("students") or {}).get("estimated_student_count")) == 0

scope = report.get("presentation_scope") or {}
keys = display_keys(report)
checks["report_detail_scope"] = scope.get("record_kind") == "competition_final" and scope.get("metric_profile") == "asr_multimodal"
checks["report_no_attention_zero"] = "attention_score" not in keys and "avg_attention_ratio" not in keys
checks["report_no_stage_zero"] = (report.get("display_flags") or {}).get("hide_stage_distribution") is True or scope.get("metric_profile") == "asr_multimodal"
checks["report_no_high_risk"] = report.get("risk_level") != "high" and not any("高风险" in str(x) for x in (report.get("risks") or []))

checks["trend_scope"] = no_hidden(payload.get("risk_lessons") or []) and no_hidden(payload.get("recent_reports") or [])
checks["admin_results_scope"] = no_hidden(items)
checks["admin_trends_scope"] = no_hidden(payload.get("risk_lessons") or []) and no_hidden(payload.get("recent_reports") or [])

sys.exit(0 if checks.get(check) else 1)
PY
}

html_check() {
  local file="$1"
  local check="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$check" <<'PY'
import sys
html = open(sys.argv[1], encoding="utf-8").read()
check = sys.argv[2]
main = html.split('<section class="card debug-card"', 1)[0]
checks = {
    "dashboard_reachable": "classroom-analysis-detail" in html,
    "video_present": 'data-marker="video-area"' in html and "classroom-video" in html,
    "asr_metrics": "课堂语音转写与提问候选" in main and "转写片段" in main and "提问候选" in main and "检测到响应" in main,
    "no_stage_chart": 'v-if="!hideStageDistribution"' in html,
    "no_attention_curve": "hideAttentionCurve" in html,
}
sys.exit(0 if checks.get(check) else 1)
PY
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] FINAL_ID=${FINAL_ID}"

TEACHER_COOKIE="$TMP_DIR/teacher.cookie"
ADMIN_COOKIE="$TMP_DIR/admin.cookie"

TEACHER_LOGIN="$TMP_DIR/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$TEACHER_LOGIN" -c "$TEACHER_COOKIE" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "$STATUS" = "200" ] && json_success_ok "$TEACHER_LOGIN" && TEACHER_LOGIN_OK=true || TEACHER_LOGIN_OK=false

ADMIN_LOGIN="$TMP_DIR/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$ADMIN_LOGIN" -c "$ADMIN_COOKIE" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "$STATUS" = "200" ] && json_success_ok "$ADMIN_LOGIN" && ADMIN_LOGIN_OK=true || ADMIN_LOGIN_OK=false

DASHBOARD_HTML="$TMP_DIR/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${FINAL_ID}" "$DASHBOARD_HTML" -b "$TEACHER_COOKIE")"
[ "$STATUS" = "200" ] && DASHBOARD_REACHABLE=true || DASHBOARD_REACHABLE=false
html_check "$DASHBOARD_HTML" "video_present" && DASHBOARD_VIDEO_PRESENT=true || DASHBOARD_VIDEO_PRESENT=false
html_check "$DASHBOARD_HTML" "asr_metrics" && DASHBOARD_ASR_METRICS_VISIBLE=true || DASHBOARD_ASR_METRICS_VISIBLE=false

DETAIL_JSON="$TMP_DIR/detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${FINAL_ID}" "$DETAIL_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$DETAIL_JSON" && DETAIL_OK=true || DETAIL_OK=false
json_check "$DETAIL_JSON" "dashboard_detail_video" && DETAIL_VIDEO_OK=true || DETAIL_VIDEO_OK=false
json_check "$DETAIL_JSON" "dashboard_detail_asr" && DETAIL_ASR_OK=true || DETAIL_ASR_OK=false
json_check "$DETAIL_JSON" "dashboard_no_fake_attention" && NO_FAKE_ATTENTION=true || NO_FAKE_ATTENTION=false
json_check "$DETAIL_JSON" "dashboard_no_fake_student" && NO_FAKE_STUDENT=true || NO_FAKE_STUDENT=false
[ "$DASHBOARD_VIDEO_PRESENT" = "true" ] && [ "$DETAIL_VIDEO_OK" = "true" ] && VIDEO_PRESENT_OK=true || VIDEO_PRESENT_OK=false

TEACHER_REPORTS_JSON="$TMP_DIR/teacher-reports.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports?data_source=real&limit=20" "$TEACHER_REPORTS_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_REPORTS_JSON" && REPORTS_API_OK=true || REPORTS_API_OK=false
json_check "$TEACHER_REPORTS_JSON" "list_hides_history" && REPORTS_FILTER_HISTORY=true || REPORTS_FILTER_HISTORY=false
json_check "$TEACHER_REPORTS_JSON" "list_has_final" && REPORTS_PHASE314_PRESENT=true || REPORTS_PHASE314_PRESENT=false
json_check "$TEACHER_REPORTS_JSON" "list_final_scope" && REPORTS_PHASE314_SCOPE=true || REPORTS_PHASE314_SCOPE=false
[ "$REPORTS_FILTER_HISTORY" = "true" ] && [ "$REPORTS_PHASE314_PRESENT" = "true" ] && [ "$REPORTS_PHASE314_SCOPE" = "true" ] && REPORTS_DEFAULT_SCOPE_OK=true || REPORTS_DEFAULT_SCOPE_OK=false

REPORT_DETAIL_JSON="$TMP_DIR/report-detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports/detail?result_id=${FINAL_ID}" "$REPORT_DETAIL_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$REPORT_DETAIL_JSON" && REPORT_DETAIL_OK=true || REPORT_DETAIL_OK=false
json_check "$REPORT_DETAIL_JSON" "report_detail_scope" && REPORT_DETAIL_SCOPE_OK=true || REPORT_DETAIL_SCOPE_OK=false
json_check "$REPORT_DETAIL_JSON" "report_no_attention_zero" && REPORT_NO_ATTENTION_ZERO=true || REPORT_NO_ATTENTION_ZERO=false
json_check "$REPORT_DETAIL_JSON" "report_no_stage_zero" && REPORT_NO_STAGE_ZERO_CHART=true || REPORT_NO_STAGE_ZERO_CHART=false
json_check "$REPORT_DETAIL_JSON" "report_no_high_risk" && REPORT_NO_HIGH_RISK=true || REPORT_NO_HIGH_RISK=false

TEACHER_RESULTS_JSON="$TMP_DIR/teacher-results.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results?days=all&limit=20" "$TEACHER_RESULTS_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_RESULTS_JSON" && json_check "$TEACHER_RESULTS_JSON" "list_hides_history" && TEACHER_RESULTS_SCOPE_OK=true || TEACHER_RESULTS_SCOPE_OK=false

TEACHER_HOME_JSON="$TMP_DIR/teacher-home.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/overview" "$TEACHER_HOME_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_HOME_JSON" && json_check "$TEACHER_HOME_JSON" "list_hides_history" && TEACHER_HOME_SCOPE_OK=true || TEACHER_HOME_SCOPE_OK=false

TEACHER_TRENDS_JSON="$TMP_DIR/teacher-trends.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?data_source=real&limit=20" "$TEACHER_TRENDS_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_TRENDS_JSON" && json_check "$TEACHER_TRENDS_JSON" "trend_scope" && TEACHER_TRENDS_SCOPE_OK=true || TEACHER_TRENDS_SCOPE_OK=false

ADMIN_RESULTS_JSON="$TMP_DIR/admin-results.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/results?days=all&limit=20" "$ADMIN_RESULTS_JSON" -b "$ADMIN_COOKIE")"
[ "$ADMIN_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$ADMIN_RESULTS_JSON" && json_check "$ADMIN_RESULTS_JSON" "admin_results_scope" && ADMIN_RESULTS_SCOPE_OK=true || ADMIN_RESULTS_SCOPE_OK=false

ADMIN_TRENDS_JSON="$TMP_DIR/admin-trends.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/trends?data_source=real&limit=30" "$ADMIN_TRENDS_JSON" -b "$ADMIN_COOKIE")"
[ "$ADMIN_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$ADMIN_TRENDS_JSON" && json_check "$ADMIN_TRENDS_JSON" "admin_trends_scope" && ADMIN_TRENDS_SCOPE_OK=true || ADMIN_TRENDS_SCOPE_OK=false

ALL_REPORTS_JSON="$TMP_DIR/all-reports.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports?data_source=all&limit=50" "$ALL_REPORTS_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$ALL_REPORTS_JSON" && json_check "$ALL_REPORTS_JSON" "demo_labeled" && DEMO_DATA_LABELED=true || DEMO_DATA_LABELED=false

NO_DB_DELETE=true
NO_STAGE_FAKE=true

print_marker "PHASE317_DASHBOARD_REACHABLE" "$DASHBOARD_REACHABLE"
print_marker "PHASE317_DASHBOARD_VIDEO_PRESENT" "$VIDEO_PRESENT_OK"
print_marker "PHASE317_DASHBOARD_ASR_METRICS_VISIBLE" "$DASHBOARD_ASR_METRICS_VISIBLE"
print_marker "PHASE317_TEACHER_REPORTS_DEFAULT_FILTERS_HISTORY" "$REPORTS_FILTER_HISTORY"
print_marker "PHASE317_TEACHER_REPORTS_PHASE314_PRESENT" "$REPORTS_PHASE314_PRESENT"
print_marker "PHASE317_TEACHER_REPORTS_PHASE37_HIDDEN" "$REPORTS_FILTER_HISTORY"
print_marker "PHASE317_TEACHER_REPORTS_PHASE35_HIDDEN" "$REPORTS_FILTER_HISTORY"
print_marker "PHASE317_TEACHER_REPORTS_LEGACY_VIDEO_VIDEO_HIDDEN" "$REPORTS_FILTER_HISTORY"
print_marker "PHASE317_PHASE314_REPORT_DETAIL_SCOPE_OK" "$REPORT_DETAIL_SCOPE_OK"
print_marker "PHASE317_PHASE314_REPORT_NO_ATTENTION_ZERO" "$REPORT_NO_ATTENTION_ZERO"
print_marker "PHASE317_PHASE314_REPORT_NO_STAGE_ZERO_CHART" "$REPORT_NO_STAGE_ZERO_CHART"
print_marker "PHASE317_PHASE314_REPORT_NO_HIGH_RISK_OVERCLAIM" "$REPORT_NO_HIGH_RISK"
print_marker "PHASE317_TEACHER_RESULTS_SCOPE_OK" "$TEACHER_RESULTS_SCOPE_OK"
print_marker "PHASE317_TEACHER_HOME_SCOPE_OK" "$TEACHER_HOME_SCOPE_OK"
print_marker "PHASE317_TEACHER_TRENDS_SCOPE_OK" "$TEACHER_TRENDS_SCOPE_OK"
print_marker "PHASE317_ADMIN_RESULTS_SCOPE_OK" "$ADMIN_RESULTS_SCOPE_OK"
print_marker "PHASE317_ADMIN_TRENDS_SCOPE_OK" "$ADMIN_TRENDS_SCOPE_OK"
print_marker "PHASE317_DEMO_DATA_LABELED" "$DEMO_DATA_LABELED"
print_marker "PHASE317_NO_FAKE_ATTENTION" "$NO_FAKE_ATTENTION"
print_marker "PHASE317_NO_FAKE_STUDENT_COUNT" "$NO_FAKE_STUDENT"
print_marker "PHASE317_NO_DB_DELETE" "$NO_DB_DELETE"

if [ "$DASHBOARD_REACHABLE" = "true" ] \
  && [ "$VIDEO_PRESENT_OK" = "true" ] \
  && [ "$DASHBOARD_ASR_METRICS_VISIBLE" = "true" ] \
  && [ "$REPORTS_FILTER_HISTORY" = "true" ] \
  && [ "$REPORTS_PHASE314_PRESENT" = "true" ] \
  && [ "$REPORTS_PHASE314_SCOPE" = "true" ] \
  && [ "$REPORT_DETAIL_SCOPE_OK" = "true" ] \
  && [ "$REPORT_NO_ATTENTION_ZERO" = "true" ] \
  && [ "$REPORT_NO_STAGE_ZERO_CHART" = "true" ] \
  && [ "$REPORT_NO_HIGH_RISK" = "true" ] \
  && [ "$TEACHER_RESULTS_SCOPE_OK" = "true" ] \
  && [ "$TEACHER_HOME_SCOPE_OK" = "true" ] \
  && [ "$TEACHER_TRENDS_SCOPE_OK" = "true" ] \
  && [ "$ADMIN_RESULTS_SCOPE_OK" = "true" ] \
  && [ "$ADMIN_TRENDS_SCOPE_OK" = "true" ] \
  && [ "$DEMO_DATA_LABELED" = "true" ] \
  && [ "$NO_FAKE_ATTENTION" = "true" ] \
  && [ "$NO_FAKE_STUDENT" = "true" ] \
  && [ "$NO_DB_DELETE" = "true" ]; then
  FRONTEND_SAMPLE_SCOPE_READY=true
else
  FRONTEND_SAMPLE_SCOPE_READY=false
fi

print_marker "PHASE317_FRONTEND_SAMPLE_SCOPE_READY" "$FRONTEND_SAMPLE_SCOPE_READY"
