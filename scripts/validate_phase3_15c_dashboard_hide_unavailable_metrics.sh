#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-phase314_asr_full_classroom_sav_20200908_17}"
TMP_DIR="${TMPDIR:-/tmp}/phase315c-dashboard-hide-unavailable-$$"

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
  curl -sS -o "$output" -w "%{http_code}" -X "$method" --max-time 25 "$@" "$url" 2>/dev/null || echo "000"
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

detail_check() {
  local file="$1"
  local check="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$check" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
check = sys.argv[2]
result = payload.get("result") or {}
raw = result.get("raw_payload") or {}
summary = result.get("summary") or {}
timeline = result.get("timeline") or {}
stage = result.get("stage_distribution") or {}
asr = result.get("asr_display") or {}
flags = result.get("display_flags") or {}
zones = result.get("zones") or {}

def num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

def all_zero(values):
    return bool(values) and all(num(value) == 0 for value in values)

zone_attention = [num((zones.get(name) or {}).get("avg_attention_ratio")) for name in ["front", "middle", "back"]]

checks = {
    "asr_sample": flags.get("asr_trusted_metrics_only") is True
        and result.get("sample_type") == "external_full_classroom_video_with_asr"
        and asr.get("transcript_present") is True,
    "attention_hidden": flags.get("hide_attention_metrics") is True and flags.get("hide_attention_curve") is True,
    "avg_attention_hidden": flags.get("hide_avg_attention") is True,
    "student_hidden": flags.get("hide_student_count") is True,
    "stage_hidden": flags.get("hide_stage_distribution") is True,
    "region_attention_hidden": flags.get("hide_region_attention") is True,
    "asr_transcript": int(num(asr.get("transcript_segment_count"))) >= 764,
    "question_candidates": int(num(asr.get("question_event_count"))) >= 35,
    "response_detected": int(num(asr.get("response_detected_count"))) >= 16,
    "event_distribution": len([event for event in result.get("events") or [] if event.get("event_type") == "question_candidate"]) >= 35,
    "no_fake_attention": num(summary.get("attention_score")) == 0 and all_zero(timeline.get("attention_curve") or []),
    "no_fake_student": num((raw.get("students") or {}).get("estimated_student_count")) == 0,
    "no_asr_stage": all_zero(list((stage or {}).values())) and flags.get("hide_stage_distribution") is True,
    "activity_available": any(num(value) > 0 for value in timeline.get("activity_curve") or []),
    "zone_attention_zero": all(value == 0 for value in zone_attention),
}
sys.exit(0 if checks.get(check) else 1)
PY
}

dashboard_check() {
  local file="$1"
  local check="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$check" <<'PY'
import sys
html = open(sys.argv[1], encoding="utf-8").read()
check = sys.argv[2]
hero = html.split('<section id="chart-app"', 1)[0]
main = html.split('<section class="card debug-card"', 1)[0]
markup = html.split('<script src=', 1)[0]
checks = {
    "attention_kpi_hidden": "专注度</span>" not in hero and "专注度</span><div" not in hero,
    "avg_attention_hidden": "平均专注率" not in hero,
    "student_count_hidden": "学生人数估计" not in hero,
    "stage_conditional": 'v-if="!hideStageDistribution"' in html and 'data-marker="stage-distribution-panel"' in html,
    "no_gray_stage_ring": 'v-if="!hideStageDistribution"' in html,
    "asr_transcript_visible": "转写片段" in main and "课堂语音转写与提问候选" in main,
    "question_candidates_visible": "提问候选" in main and "asr-question-candidates" in main,
    "response_detected_visible": "检测到响应" in main,
    "activity_timeline_visible": "课堂活跃度与提问候选时间线" in main and "activity_curve" in html,
    "attention_curve_not_shown": "hideAttentionCurve" in html and 'legend: { data: showAttention ? ["专注度", "活跃度", "提问候选"] : ["活跃度", "提问候选"] }' in html,
    "region_attention_not_shown": "hideRegionAttention" in html and 'legend: { data: showAttention ? ["专注度", "活跃度"] : ["活跃度"] }' in html,
    "event_distribution_visible": "事件分布" in main and "question_candidate" in html,
    "audio_false_hidden": "音频：false" not in markup and "audio_present" not in markup and "detected_student_count_avg" not in markup and "keyframe_count" not in markup,
    "old_score_breakdown_not_main": 'hasEnhanced && !asrTrustedMetricsOnly' in html and "scoreBreakdownEntries.length && !asrTrustedMetricsOnly" in html,
}
sys.exit(0 if checks.get(check) else 1)
PY
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] RESULT_ID=${RESULT_ID}"

TEACHER_COOKIE="$TMP_DIR/teacher.cookie"
LOGIN_OUT="$TMP_DIR/login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$LOGIN_OUT" -c "$TEACHER_COOKIE" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
if [ "$STATUS" = "200" ] && json_success_ok "$LOGIN_OUT"; then
  TEACHER_LOGIN_OK=true
else
  TEACHER_LOGIN_OK=false
fi

DETAIL_OUT="$TMP_DIR/detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESULT_ID}" "$DETAIL_OUT" -b "$TEACHER_COOKIE")"
if [ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$DETAIL_OUT"; then
  DETAIL_API_OK=true
else
  DETAIL_API_OK=false
fi
print_marker "PHASE315C_DETAIL_API_OK" "$DETAIL_API_OK"

detail_check "$DETAIL_OUT" "asr_sample" && ASR_SAMPLE_DETECTED=true || ASR_SAMPLE_DETECTED=false
detail_check "$DETAIL_OUT" "attention_hidden" && DETAIL_ATTENTION_HIDDEN=true || DETAIL_ATTENTION_HIDDEN=false
detail_check "$DETAIL_OUT" "avg_attention_hidden" && DETAIL_AVG_ATTENTION_HIDDEN=true || DETAIL_AVG_ATTENTION_HIDDEN=false
detail_check "$DETAIL_OUT" "student_hidden" && DETAIL_STUDENT_HIDDEN=true || DETAIL_STUDENT_HIDDEN=false
detail_check "$DETAIL_OUT" "stage_hidden" && DETAIL_STAGE_HIDDEN=true || DETAIL_STAGE_HIDDEN=false
detail_check "$DETAIL_OUT" "region_attention_hidden" && DETAIL_REGION_ATTENTION_HIDDEN=true || DETAIL_REGION_ATTENTION_HIDDEN=false
detail_check "$DETAIL_OUT" "asr_transcript" && DETAIL_ASR_TRANSCRIPT=true || DETAIL_ASR_TRANSCRIPT=false
detail_check "$DETAIL_OUT" "question_candidates" && DETAIL_QUESTION_CANDIDATES=true || DETAIL_QUESTION_CANDIDATES=false
detail_check "$DETAIL_OUT" "response_detected" && DETAIL_RESPONSE_DETECTED=true || DETAIL_RESPONSE_DETECTED=false
detail_check "$DETAIL_OUT" "event_distribution" && DETAIL_EVENT_DISTRIBUTION=true || DETAIL_EVENT_DISTRIBUTION=false
detail_check "$DETAIL_OUT" "no_fake_attention" && NO_FAKE_ATTENTION_SCORE=true || NO_FAKE_ATTENTION_SCORE=false
detail_check "$DETAIL_OUT" "no_fake_student" && NO_FAKE_STUDENT_COUNT=true || NO_FAKE_STUDENT_COUNT=false
detail_check "$DETAIL_OUT" "no_asr_stage" && NO_ASR_STAGE_ESTIMATION=true || NO_ASR_STAGE_ESTIMATION=false
detail_check "$DETAIL_OUT" "activity_available" && DETAIL_ACTIVITY_AVAILABLE=true || DETAIL_ACTIVITY_AVAILABLE=false
detail_check "$DETAIL_OUT" "zone_attention_zero" && DETAIL_ZONE_ATTENTION_ZERO=true || DETAIL_ZONE_ATTENTION_ZERO=false

DASHBOARD_OUT="$TMP_DIR/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "$DASHBOARD_OUT" -b "$TEACHER_COOKIE")"
[ "$STATUS" = "200" ] && DASHBOARD_OK=true || DASHBOARD_OK=false

dashboard_check "$DASHBOARD_OUT" "attention_kpi_hidden" && DASH_ATTENTION_KPI_HIDDEN=true || DASH_ATTENTION_KPI_HIDDEN=false
dashboard_check "$DASHBOARD_OUT" "avg_attention_hidden" && DASH_AVG_ATTENTION_HIDDEN=true || DASH_AVG_ATTENTION_HIDDEN=false
dashboard_check "$DASHBOARD_OUT" "student_count_hidden" && DASH_STUDENT_COUNT_HIDDEN=true || DASH_STUDENT_COUNT_HIDDEN=false
dashboard_check "$DASHBOARD_OUT" "stage_conditional" && DASH_STAGE_CONDITIONAL=true || DASH_STAGE_CONDITIONAL=false
dashboard_check "$DASHBOARD_OUT" "no_gray_stage_ring" && DASH_NO_GRAY_STAGE_RING=true || DASH_NO_GRAY_STAGE_RING=false
dashboard_check "$DASHBOARD_OUT" "asr_transcript_visible" && DASH_ASR_TRANSCRIPT=true || DASH_ASR_TRANSCRIPT=false
dashboard_check "$DASHBOARD_OUT" "question_candidates_visible" && DASH_QUESTION_CANDIDATES=true || DASH_QUESTION_CANDIDATES=false
dashboard_check "$DASHBOARD_OUT" "response_detected_visible" && DASH_RESPONSE_DETECTED=true || DASH_RESPONSE_DETECTED=false
dashboard_check "$DASHBOARD_OUT" "activity_timeline_visible" && DASH_ACTIVITY_TIMELINE=true || DASH_ACTIVITY_TIMELINE=false
dashboard_check "$DASHBOARD_OUT" "attention_curve_not_shown" && DASH_ATTENTION_CURVE_NOT_SHOWN=true || DASH_ATTENTION_CURVE_NOT_SHOWN=false
dashboard_check "$DASHBOARD_OUT" "region_attention_not_shown" && DASH_REGION_ATTENTION_NOT_SHOWN=true || DASH_REGION_ATTENTION_NOT_SHOWN=false
dashboard_check "$DASHBOARD_OUT" "event_distribution_visible" && DASH_EVENT_DISTRIBUTION=true || DASH_EVENT_DISTRIBUTION=false
dashboard_check "$DASHBOARD_OUT" "audio_false_hidden" && DASH_AUDIO_FALSE_HIDDEN=true || DASH_AUDIO_FALSE_HIDDEN=false
dashboard_check "$DASHBOARD_OUT" "old_score_breakdown_not_main" && DASH_OLD_SCORE_BREAKDOWN_NOT_MAIN=true || DASH_OLD_SCORE_BREAKDOWN_NOT_MAIN=false

[ "$DETAIL_ATTENTION_HIDDEN" = "true" ] && [ "$DASH_ATTENTION_KPI_HIDDEN" = "true" ] && ATTENTION_KPI_HIDDEN=true || ATTENTION_KPI_HIDDEN=false
[ "$DETAIL_AVG_ATTENTION_HIDDEN" = "true" ] && [ "$DASH_AVG_ATTENTION_HIDDEN" = "true" ] && AVG_ATTENTION_HIDDEN=true || AVG_ATTENTION_HIDDEN=false
[ "$DETAIL_STUDENT_HIDDEN" = "true" ] && [ "$DASH_STUDENT_COUNT_HIDDEN" = "true" ] && STUDENT_COUNT_HIDDEN=true || STUDENT_COUNT_HIDDEN=false
[ "$DETAIL_STAGE_HIDDEN" = "true" ] && [ "$DASH_STAGE_CONDITIONAL" = "true" ] && STAGE_DISTRIBUTION_HIDDEN=true || STAGE_DISTRIBUTION_HIDDEN=false
[ "$DASH_ASR_TRANSCRIPT" = "true" ] && [ "$DETAIL_ASR_TRANSCRIPT" = "true" ] && ASR_TRANSCRIPT_VISIBLE=true || ASR_TRANSCRIPT_VISIBLE=false
[ "$DASH_QUESTION_CANDIDATES" = "true" ] && [ "$DETAIL_QUESTION_CANDIDATES" = "true" ] && QUESTION_CANDIDATES_VISIBLE=true || QUESTION_CANDIDATES_VISIBLE=false
[ "$DASH_RESPONSE_DETECTED" = "true" ] && [ "$DETAIL_RESPONSE_DETECTED" = "true" ] && RESPONSE_DETECTED_VISIBLE=true || RESPONSE_DETECTED_VISIBLE=false
[ "$DASH_ACTIVITY_TIMELINE" = "true" ] && [ "$DETAIL_ACTIVITY_AVAILABLE" = "true" ] && ACTIVITY_TIMELINE_VISIBLE=true || ACTIVITY_TIMELINE_VISIBLE=false
[ "$DASH_ATTENTION_CURVE_NOT_SHOWN" = "true" ] && [ "$DETAIL_ATTENTION_HIDDEN" = "true" ] && ATTENTION_CURVE_NOT_SHOWN=true || ATTENTION_CURVE_NOT_SHOWN=false
[ "$DASH_REGION_ATTENTION_NOT_SHOWN" = "true" ] && [ "$DETAIL_REGION_ATTENTION_HIDDEN" = "true" ] && [ "$DETAIL_ZONE_ATTENTION_ZERO" = "true" ] && REGION_ATTENTION_NOT_SHOWN=true || REGION_ATTENTION_NOT_SHOWN=false
[ "$DASH_EVENT_DISTRIBUTION" = "true" ] && [ "$DETAIL_EVENT_DISTRIBUTION" = "true" ] && EVENT_DISTRIBUTION_VISIBLE=true || EVENT_DISTRIBUTION_VISIBLE=false

print_marker "PHASE315C_ASR_SAMPLE_DETECTED" "$ASR_SAMPLE_DETECTED"
print_marker "PHASE315C_ATTENTION_KPI_HIDDEN" "$ATTENTION_KPI_HIDDEN"
print_marker "PHASE315C_AVG_ATTENTION_HIDDEN" "$AVG_ATTENTION_HIDDEN"
print_marker "PHASE315C_STUDENT_COUNT_HIDDEN" "$STUDENT_COUNT_HIDDEN"
print_marker "PHASE315C_STAGE_DISTRIBUTION_HIDDEN" "$STAGE_DISTRIBUTION_HIDDEN"
print_marker "PHASE315C_NO_GRAY_STAGE_RING" "$DASH_NO_GRAY_STAGE_RING"
print_marker "PHASE315C_ASR_TRANSCRIPT_VISIBLE" "$ASR_TRANSCRIPT_VISIBLE"
print_marker "PHASE315C_QUESTION_CANDIDATES_VISIBLE" "$QUESTION_CANDIDATES_VISIBLE"
print_marker "PHASE315C_RESPONSE_DETECTED_VISIBLE" "$RESPONSE_DETECTED_VISIBLE"
print_marker "PHASE315C_ACTIVITY_TIMELINE_VISIBLE" "$ACTIVITY_TIMELINE_VISIBLE"
print_marker "PHASE315C_ATTENTION_CURVE_NOT_SHOWN" "$ATTENTION_CURVE_NOT_SHOWN"
print_marker "PHASE315C_REGION_ATTENTION_NOT_SHOWN" "$REGION_ATTENTION_NOT_SHOWN"
print_marker "PHASE315C_EVENT_DISTRIBUTION_VISIBLE" "$EVENT_DISTRIBUTION_VISIBLE"
print_marker "PHASE315C_AUDIO_FALSE_HIDDEN_FROM_MAIN_DISPLAY" "$DASH_AUDIO_FALSE_HIDDEN"
print_marker "PHASE315C_OLD_SCORE_BREAKDOWN_NOT_MAIN_DISPLAY" "$DASH_OLD_SCORE_BREAKDOWN_NOT_MAIN"
print_marker "PHASE315C_NO_FAKE_ATTENTION_SCORE" "$NO_FAKE_ATTENTION_SCORE"
print_marker "PHASE315C_NO_FAKE_STUDENT_COUNT" "$NO_FAKE_STUDENT_COUNT"
print_marker "PHASE315C_NO_ASR_STAGE_ESTIMATION" "$NO_ASR_STAGE_ESTIMATION"

if [ "$DETAIL_API_OK" = "true" ] \
  && [ "$ASR_SAMPLE_DETECTED" = "true" ] \
  && [ "$ATTENTION_KPI_HIDDEN" = "true" ] \
  && [ "$AVG_ATTENTION_HIDDEN" = "true" ] \
  && [ "$STUDENT_COUNT_HIDDEN" = "true" ] \
  && [ "$STAGE_DISTRIBUTION_HIDDEN" = "true" ] \
  && [ "$DASH_NO_GRAY_STAGE_RING" = "true" ] \
  && [ "$ASR_TRANSCRIPT_VISIBLE" = "true" ] \
  && [ "$QUESTION_CANDIDATES_VISIBLE" = "true" ] \
  && [ "$RESPONSE_DETECTED_VISIBLE" = "true" ] \
  && [ "$ACTIVITY_TIMELINE_VISIBLE" = "true" ] \
  && [ "$ATTENTION_CURVE_NOT_SHOWN" = "true" ] \
  && [ "$REGION_ATTENTION_NOT_SHOWN" = "true" ] \
  && [ "$EVENT_DISTRIBUTION_VISIBLE" = "true" ] \
  && [ "$DASH_AUDIO_FALSE_HIDDEN" = "true" ] \
  && [ "$DASH_OLD_SCORE_BREAKDOWN_NOT_MAIN" = "true" ] \
  && [ "$NO_FAKE_ATTENTION_SCORE" = "true" ] \
  && [ "$NO_FAKE_STUDENT_COUNT" = "true" ] \
  && [ "$NO_ASR_STAGE_ESTIMATION" = "true" ]; then
  DASHBOARD_TRUSTED_METRICS_ONLY_OK=true
else
  DASHBOARD_TRUSTED_METRICS_ONLY_OK=false
fi
print_marker "PHASE315C_DASHBOARD_TRUSTED_METRICS_ONLY_OK" "$DASHBOARD_TRUSTED_METRICS_ONLY_OK"
