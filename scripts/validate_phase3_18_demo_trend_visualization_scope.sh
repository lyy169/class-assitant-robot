#!/bin/bash
set -u

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
FINAL_ID="${FINAL_ID:-phase314_asr_full_classroom_sav_20200908_17}"
TMP_DIR="${TMPDIR:-/tmp}/phase318-demo-trend-scope-$$"

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
  "$PYTHON_BIN" - "$file" "$check" "$FINAL_ID" <<'PY'
import json, sys

path, check, final_id = sys.argv[1:4]
payload = json.load(open(path, encoding="utf-8"))
text = json.dumps(payload, ensure_ascii=False)


def get_series(name):
    series = payload.get("series") or {}
    value = series.get(name) or []
    return value if isinstance(value, list) else []


def items_from(*keys):
    items = []
    for key in keys:
        value = payload.get(key) or []
        if isinstance(value, list):
            items.extend([item for item in value if isinstance(item, dict)])
    return items


def count(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


filters = payload.get("filters") or {}
overview = payload.get("overview") or {}
quality = payload.get("data_quality") or {}
notes_text = " ".join(str(item) for item in (quality.get("notes") or []))
labels = get_series("labels")
recommendations = payload.get("recommendations") or []
reports = items_from("items", "recent_reports", "risk_lessons")

has_demo_id = "demo_phase3_" in text
has_demo_label = (
    quality.get("demo_warning") is True
    or "演示" in notes_text
    or "demo" in notes_text.lower()
    or "演示" in text
    or "demo" in text.lower()
)

checks = {
    "teacher_demo_scope": payload.get("success") is True and filters.get("data_source") == "demo",
    "demo_data_available": count(overview.get("lesson_count")) >= 5 or len(labels) >= 5,
    "demo_series_ok": len(labels) >= 5
        and len(get_series("score")) >= 5
        and (len(get_series("attention_score")) >= 5 or len(get_series("activity_score")) >= 5)
        and (len(get_series("question_count")) >= 5 or len(get_series("response_rate")) >= 5),
    "demo_recommendations": isinstance(recommendations, list) and len(recommendations) > 0,
    "admin_demo_scope": payload.get("success") is True and filters.get("data_source") == "demo"
        and (count(overview.get("lesson_count")) >= 5 or len(items_from("recent_reports", "risk_lessons", "classroom_rankings")) > 0),
    "real_scope": payload.get("success") is True and filters.get("data_source") == "real" and not has_demo_id,
    "reports_not_demo": payload.get("success") is True and not any(str(item.get("result_id") or item.get("analysis_id") or "").startswith("demo_phase3_") for item in reports),
    "phase314_final": payload.get("success") is True and final_id in text,
    "no_demo_as_real_claim": has_demo_label and not (filters.get("data_source") == "real" and has_demo_id),
}

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
html = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
check = sys.argv[2]
checks = {
    "teacher_demo_page": "趋势洞察" in html and "data_source" in html and "演示数据" in html,
    "teacher_demo_entry": "phase318-demo-trend-entry" in html and "查看演示趋势数据" in html,
    "teacher_demo_warning": "当前包含演示数据" in html and "不代表真实教学趋势" in html,
    "teacher_demo_charts": "phase30-score-trend-chart" in html
        and "phase30-attention-activity-chart" in html
        and "phase30-question-response-chart" in html
        and "phase30-stage-chart" in html,
    "admin_demo_page": "平台趋势洞察" in html or ("data_source" in html and "演示数据" in html),
    "admin_demo_entry": "phase318-admin-demo-trend-entry" in html and "查看平台演示趋势" in html,
}
sys.exit(0 if checks.get(check) else 1)
PY
}

echo "[info] API_BASE_URL=${API_BASE_URL}"
echo "[info] FINAL_ID=${FINAL_ID}"

if [ -f "scripts/seed_phase3_demo_trend_data.sh" ]; then
  DEMO_TREND_SEED_SCRIPT_PRESENT=true
else
  DEMO_TREND_SEED_SCRIPT_PRESENT=false
fi

TEACHER_COOKIE="$TMP_DIR/teacher.cookie"
ADMIN_COOKIE="$TMP_DIR/admin.cookie"

TEACHER_LOGIN="$TMP_DIR/teacher-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$TEACHER_LOGIN" -c "$TEACHER_COOKIE" -H "Content-Type: application/json" --data '{"username":"teacher","password":"teacher123"}')"
[ "$STATUS" = "200" ] && json_success_ok "$TEACHER_LOGIN" && TEACHER_LOGIN_OK=true || TEACHER_LOGIN_OK=false

ADMIN_LOGIN="$TMP_DIR/admin-login.json"
STATUS="$(curl_status POST "${API_BASE_URL}/api/auth/login" "$ADMIN_LOGIN" -c "$ADMIN_COOKIE" -H "Content-Type: application/json" --data '{"username":"admin","password":"admin123"}')"
[ "$STATUS" = "200" ] && json_success_ok "$ADMIN_LOGIN" && ADMIN_LOGIN_OK=true || ADMIN_LOGIN_OK=false

TEACHER_TRENDS_DEFAULT_HTML="$TMP_DIR/teacher-trends-default.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/trends" "$TEACHER_TRENDS_DEFAULT_HTML" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && html_check "$TEACHER_TRENDS_DEFAULT_HTML" "teacher_demo_entry" && TEACHER_TRENDS_DEMO_ENTRY_VISIBLE=true || TEACHER_TRENDS_DEMO_ENTRY_VISIBLE=false

TEACHER_TRENDS_HTML="$TMP_DIR/teacher-trends-demo.html"
STATUS="$(curl_status GET "${API_BASE_URL}/teacher/trends?data_source=demo&limit=20" "$TEACHER_TRENDS_HTML" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && html_check "$TEACHER_TRENDS_HTML" "teacher_demo_page" && TEACHER_TRENDS_DEMO_PAGE_REACHABLE=true || TEACHER_TRENDS_DEMO_PAGE_REACHABLE=false
html_check "$TEACHER_TRENDS_HTML" "teacher_demo_warning" && TEACHER_TRENDS_DEMO_WARNING_VISIBLE=true || TEACHER_TRENDS_DEMO_WARNING_VISIBLE=false
html_check "$TEACHER_TRENDS_HTML" "teacher_demo_charts" && TEACHER_TRENDS_DEMO_CHARTS_PRESENT=true || TEACHER_TRENDS_DEMO_CHARTS_PRESENT=false

TEACHER_DEMO_JSON="$TMP_DIR/teacher-trends-demo.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?data_source=demo&limit=20" "$TEACHER_DEMO_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_DEMO_JSON" && json_check "$TEACHER_DEMO_JSON" "teacher_demo_scope" && TEACHER_TRENDS_DEMO_API_OK=true || TEACHER_TRENDS_DEMO_API_OK=false
json_check "$TEACHER_DEMO_JSON" "demo_data_available" && TEACHER_TRENDS_DEMO_DATA_AVAILABLE=true || TEACHER_TRENDS_DEMO_DATA_AVAILABLE=false
json_check "$TEACHER_DEMO_JSON" "demo_series_ok" && TEACHER_TRENDS_DEMO_SERIES_OK=true || TEACHER_TRENDS_DEMO_SERIES_OK=false
json_check "$TEACHER_DEMO_JSON" "demo_recommendations" && TEACHER_TRENDS_DEMO_RECOMMENDATIONS_PRESENT=true || TEACHER_TRENDS_DEMO_RECOMMENDATIONS_PRESENT=false
json_check "$TEACHER_DEMO_JSON" "no_demo_as_real_claim" && NO_DEMO_AS_REAL_CLAIM=true || NO_DEMO_AS_REAL_CLAIM=false

ADMIN_TRENDS_DEFAULT_HTML="$TMP_DIR/admin-trends-default.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/trends" "$ADMIN_TRENDS_DEFAULT_HTML" -b "$ADMIN_COOKIE")"
[ "$ADMIN_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && html_check "$ADMIN_TRENDS_DEFAULT_HTML" "admin_demo_entry" && ADMIN_TRENDS_DEMO_ENTRY_VISIBLE=true || ADMIN_TRENDS_DEMO_ENTRY_VISIBLE=false

ADMIN_TRENDS_HTML="$TMP_DIR/admin-trends-demo.html"
STATUS="$(curl_status GET "${API_BASE_URL}/admin/trends?data_source=demo&limit=30" "$ADMIN_TRENDS_HTML" -b "$ADMIN_COOKIE")"
[ "$ADMIN_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && html_check "$ADMIN_TRENDS_HTML" "admin_demo_page" && ADMIN_TRENDS_DEMO_PAGE_REACHABLE=true || ADMIN_TRENDS_DEMO_PAGE_REACHABLE=false

ADMIN_DEMO_JSON="$TMP_DIR/admin-trends-demo.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/admin/trends?data_source=demo&limit=30" "$ADMIN_DEMO_JSON" -b "$ADMIN_COOKIE")"
[ "$ADMIN_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$ADMIN_DEMO_JSON" && ADMIN_TRENDS_DEMO_API_OK=true || ADMIN_TRENDS_DEMO_API_OK=false
json_check "$ADMIN_DEMO_JSON" "admin_demo_scope" && ADMIN_TRENDS_DEMO_SCOPE_OK=true || ADMIN_TRENDS_DEMO_SCOPE_OK=false

TEACHER_REAL_JSON="$TMP_DIR/teacher-trends-real.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/trends?data_source=real&limit=20" "$TEACHER_REAL_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$TEACHER_REAL_JSON" && json_check "$TEACHER_REAL_JSON" "real_scope" && REAL_TRENDS_SCOPE_STILL_REAL=true || REAL_TRENDS_SCOPE_STILL_REAL=false

REPORTS_JSON="$TMP_DIR/teacher-reports-real.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/reports?data_source=real&limit=20" "$REPORTS_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$REPORTS_JSON" && json_check "$REPORTS_JSON" "reports_not_demo" && REPORTS_DEFAULT_NOT_DEMO=true || REPORTS_DEFAULT_NOT_DEMO=false

FINAL_JSON="$TMP_DIR/final-detail.json"
STATUS="$(curl_status GET "${API_BASE_URL}/api/teacher/results/${FINAL_ID}" "$FINAL_JSON" -b "$TEACHER_COOKIE")"
[ "$TEACHER_LOGIN_OK" = "true" ] && [ "$STATUS" = "200" ] && json_success_ok "$FINAL_JSON" && json_check "$FINAL_JSON" "phase314_final" && PHASE314_FINAL_SAMPLE_UNCHANGED=true || PHASE314_FINAL_SAMPLE_UNCHANGED=false

print_marker "PHASE318_DEMO_TREND_SEED_SCRIPT_PRESENT" "$DEMO_TREND_SEED_SCRIPT_PRESENT"
print_marker "PHASE318_TEACHER_LOGIN_OK" "$TEACHER_LOGIN_OK"
print_marker "PHASE318_ADMIN_LOGIN_OK" "$ADMIN_LOGIN_OK"
print_marker "PHASE318_TEACHER_TRENDS_DEMO_ENTRY_VISIBLE" "$TEACHER_TRENDS_DEMO_ENTRY_VISIBLE"
print_marker "PHASE318_TEACHER_TRENDS_DEMO_PAGE_REACHABLE" "$TEACHER_TRENDS_DEMO_PAGE_REACHABLE"
print_marker "PHASE318_TEACHER_TRENDS_DEMO_WARNING_VISIBLE" "$TEACHER_TRENDS_DEMO_WARNING_VISIBLE"
print_marker "PHASE318_TEACHER_TRENDS_DEMO_API_OK" "$TEACHER_TRENDS_DEMO_API_OK"
print_marker "PHASE318_TEACHER_TRENDS_DEMO_DATA_AVAILABLE" "$TEACHER_TRENDS_DEMO_DATA_AVAILABLE"
print_marker "PHASE318_TEACHER_TRENDS_DEMO_SERIES_OK" "$TEACHER_TRENDS_DEMO_SERIES_OK"
print_marker "PHASE318_TEACHER_TRENDS_DEMO_CHARTS_PRESENT" "$TEACHER_TRENDS_DEMO_CHARTS_PRESENT"
print_marker "PHASE318_TEACHER_TRENDS_DEMO_RECOMMENDATIONS_PRESENT" "$TEACHER_TRENDS_DEMO_RECOMMENDATIONS_PRESENT"
print_marker "PHASE318_ADMIN_TRENDS_DEMO_ENTRY_VISIBLE" "$ADMIN_TRENDS_DEMO_ENTRY_VISIBLE"
print_marker "PHASE318_ADMIN_TRENDS_DEMO_PAGE_REACHABLE" "$ADMIN_TRENDS_DEMO_PAGE_REACHABLE"
print_marker "PHASE318_ADMIN_TRENDS_DEMO_API_OK" "$ADMIN_TRENDS_DEMO_API_OK"
print_marker "PHASE318_ADMIN_TRENDS_DEMO_SCOPE_OK" "$ADMIN_TRENDS_DEMO_SCOPE_OK"
print_marker "PHASE318_REAL_TRENDS_SCOPE_STILL_REAL" "$REAL_TRENDS_SCOPE_STILL_REAL"
print_marker "PHASE318_REPORTS_DEFAULT_NOT_DEMO" "$REPORTS_DEFAULT_NOT_DEMO"
print_marker "PHASE318_PHASE314_FINAL_SAMPLE_UNCHANGED" "$PHASE314_FINAL_SAMPLE_UNCHANGED"
print_marker "PHASE318_NO_DEMO_AS_REAL_CLAIM" "$NO_DEMO_AS_REAL_CLAIM"

if [ "$DEMO_TREND_SEED_SCRIPT_PRESENT" = "true" ] \
  && [ "$TEACHER_LOGIN_OK" = "true" ] \
  && [ "$ADMIN_LOGIN_OK" = "true" ] \
  && [ "$TEACHER_TRENDS_DEMO_ENTRY_VISIBLE" = "true" ] \
  && [ "$TEACHER_TRENDS_DEMO_PAGE_REACHABLE" = "true" ] \
  && [ "$TEACHER_TRENDS_DEMO_WARNING_VISIBLE" = "true" ] \
  && [ "$TEACHER_TRENDS_DEMO_API_OK" = "true" ] \
  && [ "$TEACHER_TRENDS_DEMO_DATA_AVAILABLE" = "true" ] \
  && [ "$TEACHER_TRENDS_DEMO_SERIES_OK" = "true" ] \
  && [ "$TEACHER_TRENDS_DEMO_CHARTS_PRESENT" = "true" ] \
  && [ "$TEACHER_TRENDS_DEMO_RECOMMENDATIONS_PRESENT" = "true" ] \
  && [ "$ADMIN_TRENDS_DEMO_ENTRY_VISIBLE" = "true" ] \
  && [ "$ADMIN_TRENDS_DEMO_API_OK" = "true" ] \
  && [ "$ADMIN_TRENDS_DEMO_SCOPE_OK" = "true" ] \
  && [ "$REAL_TRENDS_SCOPE_STILL_REAL" = "true" ] \
  && [ "$REPORTS_DEFAULT_NOT_DEMO" = "true" ] \
  && [ "$PHASE314_FINAL_SAMPLE_UNCHANGED" = "true" ] \
  && [ "$NO_DEMO_AS_REAL_CLAIM" = "true" ]; then
  DEMO_TREND_VISUALIZATION_READY=true
else
  DEMO_TREND_VISUALIZATION_READY=false
fi

print_marker "PHASE318_DEMO_TREND_VISUALIZATION_READY" "$DEMO_TREND_VISUALIZATION_READY"

if [ "$DEMO_TREND_VISUALIZATION_READY" != "true" ]; then
  exit 1
fi
