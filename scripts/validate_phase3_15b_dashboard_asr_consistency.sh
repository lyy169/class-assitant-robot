#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-phase314_asr_full_classroom_sav_20200908_17}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
TMP_DIR="${TMPDIR:-/tmp}/phase315b-dashboard-asr-consistency-$$"

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

detail_value() {
  local file="$1"
  local field="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    echo ""
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$field" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
value = payload.get("result") or {}
for part in sys.argv[2].split("."):
    if not isinstance(value, dict):
        value = ""
        break
    value = value.get(part, "")
if isinstance(value, bool):
    print("true" if value else "false")
elif value is None:
    print("")
else:
    print(value)
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
summary = result.get("summary") or {}
timeline = result.get("timeline") or {}
stage = result.get("stage_distribution") or {}
asr = result.get("asr_display") or {}
events = result.get("events") or []
scope = result.get("display_scope") or {}
raw = result.get("raw_payload") or {}

bad_legacy = "当前素材中未识别到明确提问事件"
bad_scope = "未接入树莓派语音触发与课堂转写"

def count(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0

def all_zero(values):
    return bool(values) and all(float(v or 0) == 0 for v in values)

def any_nonzero(values):
    return any(float(v or 0) > 0 for v in values or [])

checks = {
    "asr_display": bool(asr),
    "summary_override": (
        "本地 ASR 转写" in str(summary.get("summary_text") or "")
        and bad_legacy not in str(summary.get("summary_text") or "")
    ),
    "no_wrong_scope": bad_scope not in str(scope.get("unsupported_metric_note") or ""),
    "visual_zero": all_zero(timeline.get("attention_curve") or []) and all_zero(timeline.get("heat_curve") or []),
    "stage_zero": all_zero(list((stage or {}).values())),
    "activity_visible": any_nonzero(timeline.get("activity_curve") or []),
    "question_candidate_events": len([e for e in events if e.get("event_type") == "question_candidate"]) >= count(asr.get("question_event_count")),
    "no_fake_visual_score": (
        all_zero(timeline.get("attention_curve") or [])
        and all_zero(timeline.get("heat_curve") or [])
        and all_zero(list((stage or {}).values()))
        and float(summary.get("attention_score") or 0) <= 1
    ),
    "not_pi": result.get("is_pi_capture") is False and result.get("is_own_capture") is False,
    "sav": scope.get("source_dataset") == "SAV" or raw.get("source_dataset") == "SAV",
}
sys.exit(0 if checks.get(check) else 1)
PY
}

admin_ingestion_check() {
  local file="$1"
  local check="$2"
  if [ -z "$PYTHON_BIN" ] || [ ! -f "$file" ]; then
    return 1
  fi
  "$PYTHON_BIN" - "$file" "$check" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
check = sys.argv[2]
pipeline = payload.get("pipeline") or []
ingestions = payload.get("recent_ingestions") or []
text = json.dumps(payload, ensure_ascii=False)
checks = {
    "pipeline_not_pi_only": any((item.get("stage") == "Capture or External Sample") for item in pipeline)
        or "采集端或外部样本" in text,
    "no_sav_as_pi": "SAV" not in text or "非树莓派采集" in text or "外部样本" in text,
    "data_quality_note": "外部 SAV ASR 增强演示样本" in text or any(item.get("data_quality_note") for item in ingestions),
}
sys.exit(0 if checks.get(check) else 1)
PY
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] RESULT_ID=${RESULT_ID}"

HEALTH_OUT="$TMP_DIR/health.json"
STATUS="$(curl_status GET "${API_BASE_URL}/health" "$HEALTH_OUT")"

TEACHER_COOKIE="$TMP_DIR/teacher.cookie"
TEACHER_LOGIN_OUT="$TMP_DIR/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$TEACHER_LOGIN_OUT" -c "$TEACHER_COOKIE" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
if [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_LOGIN_OUT"; then
  TEACHER_LOGIN_OK=true
else
  TEACHER_LOGIN_OK=false
fi

ADMIN_COOKIE="$TMP_DIR/admin.cookie"
ADMIN_LOGIN_OUT="$TMP_DIR/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$ADMIN_LOGIN_OUT" -c "$ADMIN_COOKIE" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
if [ "$STATUS" = "200" ] && json_success_ok "$ADMIN_LOGIN_OUT"; then
  ADMIN_LOGIN_OK=true
else
  ADMIN_LOGIN_OK=false
fi

DETAIL_OUT="$TMP_DIR/detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESULT_ID}" "$DETAIL_OUT" -b "$TEACHER_COOKIE")"
if [ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$DETAIL_OUT"; then
  DETAIL_API_OK=true
else
  DETAIL_API_OK=false
fi
print_marker "PHASE315B_DETAIL_API_OK" "$DETAIL_API_OK"

detail_check "$DETAIL_OUT" "asr_display" && ASR_DISPLAY_PRESENT=true || ASR_DISPLAY_PRESENT=false
detail_check "$DETAIL_OUT" "summary_override" && ASR_SUMMARY_OVERRIDES_LEGACY_TEXT=true || ASR_SUMMARY_OVERRIDES_LEGACY_TEXT=false
detail_check "$DETAIL_OUT" "no_wrong_scope" && NO_WRONG_NO_TRANSCRIPT_SCOPE_NOTE=true || NO_WRONG_NO_TRANSCRIPT_SCOPE_NOTE=false
TRANSCRIPT_SEGMENT_COUNT="$(detail_value "$DETAIL_OUT" "asr_display.transcript_segment_count")"
QUESTION_EVENT_COUNT="$(detail_value "$DETAIL_OUT" "asr_display.question_event_count")"
RESPONSE_DETECTED_COUNT="$(detail_value "$DETAIL_OUT" "asr_display.response_detected_count")"

DASHBOARD_OUT="$TMP_DIR/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "$DASHBOARD_OUT" -b "$TEACHER_COOKIE")"
[ "$STATUS" = "200" ] && DASHBOARD_REACHABLE=true || DASHBOARD_REACHABLE=false

# raw_payload intentionally remains unchanged, so only dashboard HTML and
# display summary are checked for legacy no-question wording.
if grep -q "当前素材中未识别到明确提问事件" "$DASHBOARD_OUT" || [ "$ASR_SUMMARY_OVERRIDES_LEGACY_TEXT" != "true" ]; then
  NO_LEGACY_NO_QUESTION_TEXT=false
else
  NO_LEGACY_NO_QUESTION_TEXT=true
fi
if grep -q "教师提问转写暂不可用" "$DASHBOARD_OUT"; then
  NO_TRANSCRIPT_UNAVAILABLE_TEXT=false
else
  NO_TRANSCRIPT_UNAVAILABLE_TEXT=true
fi
if grep -q "视觉侧专注度、热度和教学阶段估计在该外部样本上置信度较低" "$DASHBOARD_OUT"; then
  VISUAL_LOW_CONFIDENCE_NOTE_PRESENT=true
else
  VISUAL_LOW_CONFIDENCE_NOTE_PRESENT=false
fi
if detail_check "$DETAIL_OUT" "visual_zero" && [ "$VISUAL_LOW_CONFIDENCE_NOTE_PRESENT" = "true" ]; then
  ATTENTION_HEAT_ZERO_HANDLED=true
else
  ATTENTION_HEAT_ZERO_HANDLED=false
fi
if detail_check "$DETAIL_OUT" "stage_zero" && grep -q "暂无可靠教学阶段分布" "$DASHBOARD_OUT"; then
  STAGE_ZERO_HANDLED=true
else
  STAGE_ZERO_HANDLED=false
fi
detail_check "$DETAIL_OUT" "activity_visible" && ACTIVITY_CURVE_STILL_VISIBLE=true || ACTIVITY_CURVE_STILL_VISIBLE=false
detail_check "$DETAIL_OUT" "question_candidate_events" && EVENT_DISTRIBUTION_QUESTION_CANDIDATES_VISIBLE=true || EVENT_DISTRIBUTION_QUESTION_CANDIDATES_VISIBLE=false
detail_check "$DETAIL_OUT" "no_fake_visual_score" && NO_FAKE_VISUAL_SCORE=true || NO_FAKE_VISUAL_SCORE=false
detail_check "$DETAIL_OUT" "not_pi" && FINAL_NOT_PI_OWN=true || FINAL_NOT_PI_OWN=false
detail_check "$DETAIL_OUT" "sav" && DETAIL_SAV=true || DETAIL_SAV=false

ADMIN_INGESTION_OUT="$TMP_DIR/admin-ingestion.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/ingestion?classroom_id=${CLASSROOM_ID}&limit=10" "$ADMIN_INGESTION_OUT" -b "$ADMIN_COOKIE")"
admin_ingestion_check "$ADMIN_INGESTION_OUT" "pipeline_not_pi_only" && ADMIN_PIPELINE_NOT_PI_ONLY=true || ADMIN_PIPELINE_NOT_PI_ONLY=false
admin_ingestion_check "$ADMIN_INGESTION_OUT" "no_sav_as_pi" && ADMIN_NO_SAV_AS_PI=true || ADMIN_NO_SAV_AS_PI=false

if grep -q "analysis_version { enhanced.analysis_version" "$DASHBOARD_OUT"; then
  ANALYSIS_VERSION_TEMPLATE_FIXED=false
else
  ANALYSIS_VERSION_TEMPLATE_FIXED=true
fi

if [ "$FINAL_NOT_PI_OWN" = "true" ] && [ "$DETAIL_SAV" = "true" ] && [ "$ADMIN_NO_SAV_AS_PI" = "true" ]; then
  NO_SAV_AS_PI_CAPTURE=true
else
  NO_SAV_AS_PI_CAPTURE=false
fi

print_marker "PHASE315B_ASR_DISPLAY_PRESENT" "$ASR_DISPLAY_PRESENT"
print_marker "PHASE315B_ASR_SUMMARY_OVERRIDES_LEGACY_TEXT" "$ASR_SUMMARY_OVERRIDES_LEGACY_TEXT"
print_marker "PHASE315B_NO_LEGACY_NO_QUESTION_TEXT" "$NO_LEGACY_NO_QUESTION_TEXT"
print_marker "PHASE315B_NO_TRANSCRIPT_UNAVAILABLE_TEXT" "$NO_TRANSCRIPT_UNAVAILABLE_TEXT"
print_marker "PHASE315B_NO_WRONG_NO_TRANSCRIPT_SCOPE_NOTE" "$NO_WRONG_NO_TRANSCRIPT_SCOPE_NOTE"
print_marker "PHASE315B_TRANSCRIPT_SEGMENT_COUNT" "${TRANSCRIPT_SEGMENT_COUNT:-0}"
print_marker "PHASE315B_QUESTION_EVENT_COUNT" "${QUESTION_EVENT_COUNT:-0}"
print_marker "PHASE315B_RESPONSE_DETECTED_COUNT" "${RESPONSE_DETECTED_COUNT:-0}"
print_marker "PHASE315B_VISUAL_LOW_CONFIDENCE_NOTE_PRESENT" "$VISUAL_LOW_CONFIDENCE_NOTE_PRESENT"
print_marker "PHASE315B_ATTENTION_HEAT_ZERO_HANDLED" "$ATTENTION_HEAT_ZERO_HANDLED"
print_marker "PHASE315B_STAGE_ZERO_HANDLED" "$STAGE_ZERO_HANDLED"
print_marker "PHASE315B_ACTIVITY_CURVE_STILL_VISIBLE" "$ACTIVITY_CURVE_STILL_VISIBLE"
print_marker "PHASE315B_EVENT_DISTRIBUTION_QUESTION_CANDIDATES_VISIBLE" "$EVENT_DISTRIBUTION_QUESTION_CANDIDATES_VISIBLE"
print_marker "PHASE315B_NO_FAKE_VISUAL_SCORE" "$NO_FAKE_VISUAL_SCORE"
print_marker "PHASE315B_ADMIN_PIPELINE_NOT_PI_ONLY" "$ADMIN_PIPELINE_NOT_PI_ONLY"
print_marker "PHASE315B_NO_SAV_AS_PI_CAPTURE" "$NO_SAV_AS_PI_CAPTURE"
print_marker "PHASE315B_ANALYSIS_VERSION_TEMPLATE_FIXED" "$ANALYSIS_VERSION_TEMPLATE_FIXED"
print_marker "PHASE315B_DASHBOARD_REACHABLE" "$DASHBOARD_REACHABLE"

if [ "$DETAIL_API_OK" = "true" ] \
  && [ "$ASR_DISPLAY_PRESENT" = "true" ] \
  && [ "$ASR_SUMMARY_OVERRIDES_LEGACY_TEXT" = "true" ] \
  && [ "$NO_LEGACY_NO_QUESTION_TEXT" = "true" ] \
  && [ "$NO_TRANSCRIPT_UNAVAILABLE_TEXT" = "true" ] \
  && [ "$NO_WRONG_NO_TRANSCRIPT_SCOPE_NOTE" = "true" ] \
  && [ "${TRANSCRIPT_SEGMENT_COUNT:-0}" -ge 764 ] \
  && [ "${QUESTION_EVENT_COUNT:-0}" -ge 35 ] \
  && [ "${RESPONSE_DETECTED_COUNT:-0}" -ge 16 ] \
  && [ "$VISUAL_LOW_CONFIDENCE_NOTE_PRESENT" = "true" ] \
  && [ "$ATTENTION_HEAT_ZERO_HANDLED" = "true" ] \
  && [ "$STAGE_ZERO_HANDLED" = "true" ] \
  && [ "$ACTIVITY_CURVE_STILL_VISIBLE" = "true" ] \
  && [ "$EVENT_DISTRIBUTION_QUESTION_CANDIDATES_VISIBLE" = "true" ] \
  && [ "$NO_FAKE_VISUAL_SCORE" = "true" ] \
  && [ "$ADMIN_PIPELINE_NOT_PI_ONLY" = "true" ] \
  && [ "$NO_SAV_AS_PI_CAPTURE" = "true" ] \
  && [ "$ANALYSIS_VERSION_TEMPLATE_FIXED" = "true" ] \
  && [ "$DASHBOARD_REACHABLE" = "true" ]; then
  DASHBOARD_ASR_CONSISTENCY_OK=true
else
  DASHBOARD_ASR_CONSISTENCY_OK=false
fi
print_marker "PHASE315B_DASHBOARD_ASR_CONSISTENCY_OK" "$DASHBOARD_ASR_CONSISTENCY_OK"
