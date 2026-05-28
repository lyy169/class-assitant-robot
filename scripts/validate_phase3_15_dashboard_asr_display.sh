#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
RESULT_ID="${RESULT_ID:-phase314_asr_full_classroom_sav_20200908_17}"
TMP_DIR="${TMPDIR:-/tmp}/phase315-dashboard-asr-display-$$"

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
  curl -sS -o "$output" -w "%{http_code}" -X "$method" --max-time 20 "$@" "$url" 2>/dev/null || echo "000"
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
raw = result.get("raw_payload") or {}
asr = result.get("asr_display") or {}
video = result.get("video") or {}
display_scope = result.get("display_scope") or {}

def count(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0

checks = {
    "asr_display": bool(asr),
    "transcript_summary": count(asr.get("transcript_segment_count")) > 0,
    "question_events": count(asr.get("question_event_count")) > 0 and bool(asr.get("question_events")),
    "response_alignment": count(asr.get("alignment_count")) > 0 and count(asr.get("response_detected_count")) > 0,
    "speaker_false": asr.get("speaker_diarization") is False,
    "video_playable": video.get("status") == "playable" and str(video.get("video_url") or "").startswith("/uploads/"),
    "sav_source": display_scope.get("source_label") == "SAV 外部公开课堂视频" or raw.get("source_dataset") == "SAV",
}
sys.exit(0 if checks.get(check) else 1)
PY
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] RESULT_ID=${RESULT_ID}"

HEALTH_OUT="$TMP_DIR/health.json"
STATUS="$(curl_status GET "${API_BASE_URL}/health" "$HEALTH_OUT")"
[ "$STATUS" = "200" ] && HEALTH_OK=true || HEALTH_OK=false

TEACHER_COOKIE="$TMP_DIR/teacher.cookie"
TEACHER_LOGIN_OUT="$TMP_DIR/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$TEACHER_LOGIN_OUT" -c "$TEACHER_COOKIE" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
if [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_LOGIN_OUT"; then
  TEACHER_LOGIN_OK=true
else
  TEACHER_LOGIN_OK=false
fi

DETAIL_OUT="$TMP_DIR/detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${RESULT_ID}" "$DETAIL_OUT" -b "$TEACHER_COOKIE")"
if [ "$HEALTH_OK" = "true" ] && [ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$DETAIL_OUT"; then
  DETAIL_API_OK=true
else
  DETAIL_API_OK=false
fi
print_marker "PHASE315_DETAIL_API_OK" "$DETAIL_API_OK"

detail_check "$DETAIL_OUT" "asr_display" && ASR_DISPLAY_PRESENT=true || ASR_DISPLAY_PRESENT=false
detail_check "$DETAIL_OUT" "transcript_summary" && TRANSCRIPT_SUMMARY_PRESENT=true || TRANSCRIPT_SUMMARY_PRESENT=false
TRANSCRIPT_SEGMENT_COUNT="$(detail_value "$DETAIL_OUT" "asr_display.transcript_segment_count")"
detail_check "$DETAIL_OUT" "question_events" && QUESTION_EVENTS_VISIBLE_IN_API=true || QUESTION_EVENTS_VISIBLE_IN_API=false
QUESTION_EVENT_COUNT="$(detail_value "$DETAIL_OUT" "asr_display.question_event_count")"
detail_check "$DETAIL_OUT" "response_alignment" && RESPONSE_ALIGNMENT_VISIBLE_IN_API=true || RESPONSE_ALIGNMENT_VISIBLE_IN_API=false
RESPONSE_DETECTED_COUNT="$(detail_value "$DETAIL_OUT" "asr_display.response_detected_count")"
detail_check "$DETAIL_OUT" "speaker_false" && SPEAKER_DIARIZATION_FALSE=true || SPEAKER_DIARIZATION_FALSE=false

print_marker "PHASE315_ASR_DISPLAY_PRESENT" "$ASR_DISPLAY_PRESENT"
print_marker "PHASE315_TRANSCRIPT_SUMMARY_PRESENT" "$TRANSCRIPT_SUMMARY_PRESENT"
print_marker "PHASE315_TRANSCRIPT_SEGMENT_COUNT" "${TRANSCRIPT_SEGMENT_COUNT:-0}"
print_marker "PHASE315_QUESTION_EVENTS_VISIBLE_IN_API" "$QUESTION_EVENTS_VISIBLE_IN_API"
print_marker "PHASE315_QUESTION_EVENT_COUNT" "${QUESTION_EVENT_COUNT:-0}"
print_marker "PHASE315_RESPONSE_ALIGNMENT_VISIBLE_IN_API" "$RESPONSE_ALIGNMENT_VISIBLE_IN_API"
print_marker "PHASE315_RESPONSE_DETECTED_COUNT" "${RESPONSE_DETECTED_COUNT:-0}"
print_marker "PHASE315_SPEAKER_DIARIZATION_FALSE" "$SPEAKER_DIARIZATION_FALSE"

DASHBOARD_OUT="$TMP_DIR/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${RESULT_ID}" "$DASHBOARD_OUT" -b "$TEACHER_COOKIE")"
[ "$STATUS" = "200" ] && DASHBOARD_REACHABLE=true || DASHBOARD_REACHABLE=false
print_marker "PHASE315_DASHBOARD_REACHABLE" "$DASHBOARD_REACHABLE"

grep -q "课堂语音转写与提问候选" "$DASHBOARD_OUT" && DASHBOARD_ASR_SECTION_PRESENT=true || DASHBOARD_ASR_SECTION_PRESENT=false
grep -q "提问候选" "$DASHBOARD_OUT" && DASHBOARD_QUESTION_CANDIDATES_PRESENT=true || DASHBOARD_QUESTION_CANDIDATES_PRESENT=false
if grep -q "未进行说话人分离" "$DASHBOARD_OUT" || grep -q "不做精准教师身份判断" "$DASHBOARD_OUT"; then
  DASHBOARD_ASR_BOUNDARY_NOTE_PRESENT=true
else
  DASHBOARD_ASR_BOUNDARY_NOTE_PRESENT=false
fi
if grep -q "已完成精准教师身份识别\\|精准教师身份识别结论\\|教师身份已识别" "$DASHBOARD_OUT"; then
  NO_TEACHER_IDENTITY_OVERCLAIM=false
else
  NO_TEACHER_IDENTITY_OVERCLAIM=true
fi

detail_check "$DETAIL_OUT" "video_playable" && VIDEO_STILL_PLAYABLE=true || VIDEO_STILL_PLAYABLE=false
detail_check "$DETAIL_OUT" "sav_source" && DETAIL_SAV_SOURCE=true || DETAIL_SAV_SOURCE=false
if grep -q "当前课堂样本来自 SAV 外部公开课堂视频" "$DASHBOARD_OUT" && [ "$DETAIL_SAV_SOURCE" = "true" ]; then
  SAV_SOURCE_NOTE_STILL_PRESENT=true
else
  SAV_SOURCE_NOTE_STILL_PRESENT=false
fi

print_marker "PHASE315_DASHBOARD_ASR_SECTION_PRESENT" "$DASHBOARD_ASR_SECTION_PRESENT"
print_marker "PHASE315_DASHBOARD_QUESTION_CANDIDATES_PRESENT" "$DASHBOARD_QUESTION_CANDIDATES_PRESENT"
print_marker "PHASE315_DASHBOARD_ASR_BOUNDARY_NOTE_PRESENT" "$DASHBOARD_ASR_BOUNDARY_NOTE_PRESENT"
print_marker "PHASE315_NO_TEACHER_IDENTITY_OVERCLAIM" "$NO_TEACHER_IDENTITY_OVERCLAIM"
print_marker "PHASE315_VIDEO_STILL_PLAYABLE" "$VIDEO_STILL_PLAYABLE"
print_marker "PHASE315_SAV_SOURCE_NOTE_STILL_PRESENT" "$SAV_SOURCE_NOTE_STILL_PRESENT"

if [ "$DETAIL_API_OK" = "true" ] \
  && [ "$ASR_DISPLAY_PRESENT" = "true" ] \
  && [ "$TRANSCRIPT_SUMMARY_PRESENT" = "true" ] \
  && [ "${TRANSCRIPT_SEGMENT_COUNT:-0}" -gt 0 ] \
  && [ "$QUESTION_EVENTS_VISIBLE_IN_API" = "true" ] \
  && [ "${QUESTION_EVENT_COUNT:-0}" -gt 0 ] \
  && [ "$RESPONSE_ALIGNMENT_VISIBLE_IN_API" = "true" ] \
  && [ "${RESPONSE_DETECTED_COUNT:-0}" -gt 0 ] \
  && [ "$SPEAKER_DIARIZATION_FALSE" = "true" ] \
  && [ "$DASHBOARD_REACHABLE" = "true" ] \
  && [ "$DASHBOARD_ASR_SECTION_PRESENT" = "true" ] \
  && [ "$DASHBOARD_QUESTION_CANDIDATES_PRESENT" = "true" ] \
  && [ "$DASHBOARD_ASR_BOUNDARY_NOTE_PRESENT" = "true" ] \
  && [ "$NO_TEACHER_IDENTITY_OVERCLAIM" = "true" ] \
  && [ "$VIDEO_STILL_PLAYABLE" = "true" ] \
  && [ "$SAV_SOURCE_NOTE_STILL_PRESENT" = "true" ]; then
  DASHBOARD_ASR_DISPLAY_OK=true
else
  DASHBOARD_ASR_DISPLAY_OK=false
fi
print_marker "PHASE315_DASHBOARD_ASR_DISPLAY_OK" "$DASHBOARD_ASR_DISPLAY_OK"
