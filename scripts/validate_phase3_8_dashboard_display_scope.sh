#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
FINAL_RESULT_ID="${FINAL_RESULT_ID:-phase37_full_classroom_sav_20200908_17}"
DEMO_RESULT_ID="${DEMO_RESULT_ID:-phase35_local_imported_sav_full_classroom_20200908_17}"
TMP_DIR="${TMPDIR:-/tmp}/phase38-dashboard-display-scope-$$"

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
scope = result.get("display_scope") or {}
capture = raw.get("capture") or {}
video = raw.get("video") or {}
phase37 = raw.get("phase37_final_dashboard_sample") or {}

def first(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return ""

def boolish(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off"}:
            return False
    return None

source_dataset = first(scope.get("source_dataset"), result.get("source_dataset"), raw.get("source_dataset"), capture.get("source_dataset"))
sample_type = first(scope.get("sample_type"), result.get("sample_type"), raw.get("sample_type"), capture.get("sample_type"))
is_pi = boolish(first(scope.get("is_pi_capture"), result.get("is_pi_capture"), raw.get("is_pi_capture"), capture.get("is_pi_capture")))
is_own = boolish(first(scope.get("is_own_capture"), result.get("is_own_capture"), raw.get("is_own_capture"), capture.get("is_own_capture")))
is_final = boolish(first(scope.get("is_final_dashboard_sample"), result.get("is_final_dashboard_sample"), raw.get("is_final_dashboard_sample"), capture.get("is_final_dashboard_sample"), video.get("is_final_dashboard_sample"), phase37.get("final_dashboard_sample")))
is_demo = boolish(first(scope.get("is_demo_playback_sample"), result.get("is_demo_playback_sample"), raw.get("is_demo_playback_sample"), capture.get("is_demo_playback_sample"), video.get("is_demo_playback_sample")))

checks = {
    "display_scope_present": bool(scope) and (scope.get("source_label") or source_dataset == "SAV"),
    "source_sav": source_dataset == "SAV" or scope.get("source_label") == "SAV 外部公开课堂视频",
    "not_pi": is_pi is False,
    "not_own": is_own is False,
    "final_sample": is_final is True,
    "demo_scope": (is_demo is True) or ("cloud_playback_demo" in str(sample_type)),
    "unsupported_metrics": bool(scope.get("unsupported_metric_note")) or (raw.get("evidence_summary") or {}).get("audio_present") is False,
    "no_sav50": bool(scope.get("no_sav50_mixed")) or phase37.get("not_sav50_composite") is True,
}
sys.exit(0 if checks.get(check) else 1)
PY
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] FINAL_RESULT_ID=${FINAL_RESULT_ID}"
echo "[info] DEMO_RESULT_ID=${DEMO_RESULT_ID}"

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

FINAL_DETAIL_OUT="$TMP_DIR/final-detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${FINAL_RESULT_ID}" "$FINAL_DETAIL_OUT" -b "$TEACHER_COOKIE")"
if [ "$HEALTH_OK" = "true" ] && [ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$FINAL_DETAIL_OUT"; then
  DETAIL_API_OK=true
else
  DETAIL_API_OK=false
fi
print_marker "PHASE38_DETAIL_API_OK" "$DETAIL_API_OK"

detail_check "$FINAL_DETAIL_OUT" "display_scope_present" && DISPLAY_SCOPE_PRESENT=true || DISPLAY_SCOPE_PRESENT=false
detail_check "$FINAL_DETAIL_OUT" "source_sav" && DETAIL_SOURCE_SAV=true || DETAIL_SOURCE_SAV=false
detail_check "$FINAL_DETAIL_OUT" "not_pi" && FINAL_SAMPLE_NOT_PI_CAPTURE=true || FINAL_SAMPLE_NOT_PI_CAPTURE=false
detail_check "$FINAL_DETAIL_OUT" "not_own" && FINAL_SAMPLE_NOT_OWN_CAPTURE=true || FINAL_SAMPLE_NOT_OWN_CAPTURE=false
detail_check "$FINAL_DETAIL_OUT" "final_sample" && FINAL_SAMPLE_FLAG=true || FINAL_SAMPLE_FLAG=false
detail_check "$FINAL_DETAIL_OUT" "unsupported_metrics" && DETAIL_UNSUPPORTED_METRICS=true || DETAIL_UNSUPPORTED_METRICS=false
detail_check "$FINAL_DETAIL_OUT" "no_sav50" && DETAIL_NO_SAV50=true || DETAIL_NO_SAV50=false

if [ "$DISPLAY_SCOPE_PRESENT" = "true" ] && [ "$DETAIL_SOURCE_SAV" = "true" ] && [ "$FINAL_SAMPLE_FLAG" = "true" ]; then
  DISPLAY_SCOPE_PRESENT=true
else
  DISPLAY_SCOPE_PRESENT=false
fi
print_marker "PHASE38_DISPLAY_SCOPE_PRESENT" "$DISPLAY_SCOPE_PRESENT"
print_marker "PHASE38_FINAL_SAMPLE_NOT_PI_CAPTURE" "$FINAL_SAMPLE_NOT_PI_CAPTURE"
print_marker "PHASE38_FINAL_SAMPLE_NOT_OWN_CAPTURE" "$FINAL_SAMPLE_NOT_OWN_CAPTURE"

DASHBOARD_OUT="$TMP_DIR/dashboard.html"
STATUS="$(curl_status GET "${API_BASE_URL}/dashboard?result_id=${FINAL_RESULT_ID}" "$DASHBOARD_OUT" -b "$TEACHER_COOKIE")"
[ "$STATUS" = "200" ] && DASHBOARD_REACHABLE=true || DASHBOARD_REACHABLE=false

if grep -q "当前课堂样本来自 SAV 外部公开课堂视频" "$DASHBOARD_OUT"; then
  FINAL_SAMPLE_SOURCE_NOTE_PRESENT=true
else
  FINAL_SAMPLE_SOURCE_NOTE_PRESENT=false
fi
print_marker "PHASE38_FINAL_SAMPLE_SOURCE_NOTE_PRESENT" "$FINAL_SAMPLE_SOURCE_NOTE_PRESENT"

DEMO_DETAIL_OUT="$TMP_DIR/demo-detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${DEMO_RESULT_ID}" "$DEMO_DETAIL_OUT" -b "$TEACHER_COOKIE")"
if [ "$STATUS" = "404" ]; then
  DEMO_CLIP_SCOPE_NOTE_SUPPORTED=true
elif [ "$STATUS" = "200" ] && json_success_ok "$DEMO_DETAIL_OUT" && detail_check "$DEMO_DETAIL_OUT" "demo_scope"; then
  DEMO_CLIP_SCOPE_NOTE_SUPPORTED=true
else
  DEMO_CLIP_SCOPE_NOTE_SUPPORTED=false
fi
print_marker "PHASE38_DEMO_CLIP_SCOPE_NOTE_SUPPORTED" "$DEMO_CLIP_SCOPE_NOTE_SUPPORTED"

if [ "$DETAIL_UNSUPPORTED_METRICS" = "true" ] && grep -q "语音相关教学阶段和教师提问指标仅作结构展示" "$DASHBOARD_OUT"; then
  UNSUPPORTED_METRICS_MARKED=true
else
  UNSUPPORTED_METRICS_MARKED=false
fi
print_marker "PHASE38_UNSUPPORTED_METRICS_MARKED" "$UNSUPPORTED_METRICS_MARKED"

if [ "$FINAL_SAMPLE_FLAG" = "true" ] && ! grep -q "该记录为播放链路 smoke test，不作为最终完整课堂分析展示样本。.*${FINAL_RESULT_ID}" "$DASHBOARD_OUT"; then
  NO_1MIN_VIDEO_FULL_CLASS_MISLEADING=true
else
  NO_1MIN_VIDEO_FULL_CLASS_MISLEADING=false
fi
print_marker "PHASE38_NO_1MIN_VIDEO_FULL_CLASS_MISLEADING" "$NO_1MIN_VIDEO_FULL_CLASS_MISLEADING"

if [ "$DETAIL_NO_SAV50" = "true" ] && ! grep -q "SAV-50 切片.*单堂完整课堂" "$DASHBOARD_OUT"; then
  NO_SAV50_MIXED_IN_DASHBOARD=true
else
  NO_SAV50_MIXED_IN_DASHBOARD=false
fi
print_marker "PHASE38_NO_SAV50_MIXED_IN_DASHBOARD" "$NO_SAV50_MIXED_IN_DASHBOARD"

print_marker "PHASE38_DASHBOARD_REACHABLE" "$DASHBOARD_REACHABLE"

if [ "$DETAIL_API_OK" = "true" ] \
  && [ "$DISPLAY_SCOPE_PRESENT" = "true" ] \
  && [ "$FINAL_SAMPLE_SOURCE_NOTE_PRESENT" = "true" ] \
  && [ "$FINAL_SAMPLE_NOT_PI_CAPTURE" = "true" ] \
  && [ "$FINAL_SAMPLE_NOT_OWN_CAPTURE" = "true" ] \
  && [ "$DEMO_CLIP_SCOPE_NOTE_SUPPORTED" = "true" ] \
  && [ "$UNSUPPORTED_METRICS_MARKED" = "true" ] \
  && [ "$NO_1MIN_VIDEO_FULL_CLASS_MISLEADING" = "true" ] \
  && [ "$NO_SAV50_MIXED_IN_DASHBOARD" = "true" ] \
  && [ "$DASHBOARD_REACHABLE" = "true" ]; then
  DASHBOARD_DISPLAY_SCOPE_OK=true
else
  DASHBOARD_DISPLAY_SCOPE_OK=false
fi
print_marker "PHASE38_DASHBOARD_DISPLAY_SCOPE_OK" "$DASHBOARD_DISPLAY_SCOPE_OK"
