#!/bin/bash
set -u

PROJECT_DIR="/root/video_project_src"
POSTGRES_ENV="cloud_backend/.env.postgres.runtime"
RUNTIME_ENV="cloud_backend/.env.runtime"
SERVICE_EXAMPLE="cloud_backend/classroom-cloud-backend.service.example"
UPLOAD_DIR_DEFAULT="/root/video_project/uploads"
UPLOAD_DIR_COMPAT="/root/video_project/upload"
BASE_URL="http://127.0.0.1:8011"

print_marker() {
  echo "$1=$2"
}

env_value() {
  local file="$1"
  local key="$2"
  if [ ! -f "$file" ]; then
    return 0
  fi
  grep -E "^[[:space:]]*${key}=" "$file" | tail -n 1 | sed -E "s/^[^=]+=//; s/^['\"]//; s/['\"]$//"
}

db_type_from_url() {
  local value="$1"
  case "$value" in
    postgres://*|postgresql://*) echo "postgres" ;;
    sqlite://*) echo "sqlite" ;;
    *) echo "unknown" ;;
  esac
}

safe_config() {
  local key="$1"
  local value
  value="$(env_value "$POSTGRES_ENV" "$key")"
  if [ -z "$value" ]; then
    value="$(env_value "$RUNTIME_ENV" "$key")"
  fi
  case "$key" in
    CLOUD_PORT) echo "${value:-8011}" ;;
    CLOUD_DB_BACKEND) echo "${value:-unknown}" ;;
    CLOUD_DATA_DIR) echo "${value:-/root/video_project_src/cloud_backend/data}" ;;
    CLOUD_RAW_DIR) echo "${value:-/root/video_project_src/cloud_backend/data/raw}" ;;
    CLOUD_SAMPLE_DATA_DIR) echo "${value:-/root/video_project_src/cloud_backend/sample_data}" ;;
    CLOUD_REQUIRE_API_KEY) echo "${value:-false}" ;;
    CLOUD_REQUIRE_CLASSROOM_ID) echo "${value:-unknown}" ;;
    CLOUD_REQUIRE_SOURCE_HOST) echo "${value:-unknown}" ;;
    CLOUD_VIDEO_UPLOAD_DIR) echo "${value:-$UPLOAD_DIR_DEFAULT}" ;;
    *) echo "${value:-unknown}" ;;
  esac
}

port_listening() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -lnt 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:|\\])${port}$"
    return $?
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -lnt 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:|\\])${port}$"
    return $?
  fi
  return 1
}

process_present() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -af "uvicorn.*cloud_backend.main:app" >/dev/null 2>&1
    return $?
  fi
  ps ax 2>/dev/null | grep -E "uvicorn.*cloud_backend.main:app" | grep -v grep >/dev/null 2>&1
}

systemd_state() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "unknown"
    return
  fi
  if ! systemctl list-unit-files classroom-cloud-backend.service --no-pager 2>/dev/null | grep -q "classroom-cloud-backend.service"; then
    if ! systemctl status classroom-cloud-backend.service --no-pager >/dev/null 2>&1; then
      echo "missing"
      return
    fi
  fi
  local state
  state="$(systemctl is-active classroom-cloud-backend.service 2>/dev/null || true)"
  case "$state" in
    active|inactive|failed) echo "$state" ;;
    *) echo "unknown" ;;
  esac
}

http_status() {
  local url="$1"
  curl -sS -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000"
}

http_content_type() {
  local url="$1"
  curl -sS -I --max-time 5 "$url" 2>/dev/null | awk 'BEGIN{IGNORECASE=1} /^Content-Type:/ {sub(/\r$/, ""); print $0; exit}'
}

reachable_status() {
  local status="$1"
  if [ "$status" = "200" ] || [ "$status" = "302" ]; then
    echo "true"
  else
    echo "false"
  fi
}

count_videos() {
  local directory="$1"
  if [ ! -d "$directory" ]; then
    echo 0
    return
  fi
  find "$directory" -type f \( -iname "*.mp4" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.ogg" \) 2>/dev/null | wc -l | tr -d ' '
}

count_ext() {
  local directory="$1"
  local ext="$2"
  if [ ! -d "$directory" ]; then
    echo 0
    return
  fi
  find "$directory" -type f -iname "*.${ext}" 2>/dev/null | wc -l | tr -d ' '
}

redact_sensitive() {
  sed -E 's#(postgres|postgresql)://[^[:space:]]+#\1://<redacted>#g; s#(password|token|secret|api[_-]?key)=([^[:space:]]+)#\1=<redacted>#Ig'
}

echo "[info] Phase 3.5a cloud runtime check is read-only."
echo "[info] It will not start services, restart services, edit systemd, or modify databases."
echo "[info] PWD=$(pwd)"

if [ "$(pwd)" = "$PROJECT_DIR" ] && [ -f "cloud_backend/main.py" ]; then
  CLOUD_PROJECT_PRESENT=true
else
  CLOUD_PROJECT_PRESENT=false
fi

if [ -f "$POSTGRES_ENV" ]; then POSTGRES_RUNTIME_ENV_PRESENT=true; else POSTGRES_RUNTIME_ENV_PRESENT=false; fi
if [ -f "$RUNTIME_ENV" ]; then RUNTIME_ENV_PRESENT=true; else RUNTIME_ENV_PRESENT=false; fi
if [ -f "$SERVICE_EXAMPLE" ]; then SERVICE_EXAMPLE_PRESENT=true; else SERVICE_EXAMPLE_PRESENT=false; fi

DB_BACKEND="$(safe_config CLOUD_DB_BACKEND)"
case "$DB_BACKEND" in
  postgres|sqlite|file) ;;
  *) DB_BACKEND="unknown" ;;
esac

DB_URL="$(env_value "$POSTGRES_ENV" CLOUD_DATABASE_URL)"
if [ -z "$DB_URL" ]; then
  DB_URL="$(env_value "$POSTGRES_ENV" POSTGRES_URL)"
fi
DATABASE_TYPE="$(db_type_from_url "$DB_URL")"

echo "[config] CLOUD_PORT=$(safe_config CLOUD_PORT)"
echo "[config] CLOUD_DB_BACKEND=$DB_BACKEND"
echo "[config] CLOUD_DATA_DIR=$(safe_config CLOUD_DATA_DIR)"
echo "[config] CLOUD_RAW_DIR=$(safe_config CLOUD_RAW_DIR)"
echo "[config] CLOUD_SAMPLE_DATA_DIR=$(safe_config CLOUD_SAMPLE_DATA_DIR)"
echo "[config] CLOUD_VIDEO_UPLOAD_DIR=$(safe_config CLOUD_VIDEO_UPLOAD_DIR)"
echo "[config] CLOUD_REQUIRE_API_KEY=$(safe_config CLOUD_REQUIRE_API_KEY)"
echo "[config] CLOUD_REQUIRE_CLASSROOM_ID=$(safe_config CLOUD_REQUIRE_CLASSROOM_ID)"
echo "[config] CLOUD_REQUIRE_SOURCE_HOST=$(safe_config CLOUD_REQUIRE_SOURCE_HOST)"
echo "[config] DATABASE_TYPE=$DATABASE_TYPE"

if port_listening 8011; then PORT_8011_LISTENING=true; else PORT_8011_LISTENING=false; fi
if port_listening 8010; then PORT_8010_LISTENING=true; else PORT_8010_LISTENING=false; fi
if process_present; then SERVICE_PROCESS_PRESENT=true; else SERVICE_PROCESS_PRESENT=false; fi
SYSTEMD_SERVICE_STATE="$(systemd_state)"

if [ "$SYSTEMD_SERVICE_STATE" != "missing" ] && [ "$SYSTEMD_SERVICE_STATE" != "unknown" ] && command -v journalctl >/dev/null 2>&1; then
  echo "[systemd] recent log summary, sensitive values redacted:"
  journalctl -u classroom-cloud-backend.service -n 20 --no-pager 2>/dev/null | redact_sensitive || true
fi

UPLOAD_DIR="$(safe_config CLOUD_VIDEO_UPLOAD_DIR)"
if [ -z "$UPLOAD_DIR" ] || [ "$UPLOAD_DIR" = "unknown" ]; then
  UPLOAD_DIR="$UPLOAD_DIR_DEFAULT"
fi

if [ -d "$UPLOAD_DIR" ]; then UPLOAD_DIR_PRESENT=true; else UPLOAD_DIR_PRESENT=false; fi
if [ -f "$UPLOAD_DIR/video.mp4" ]; then UPLOAD_VIDEO_PRESENT=true; else UPLOAD_VIDEO_PRESENT=false; fi
UPLOAD_VIDEO_COUNT="$(count_videos "$UPLOAD_DIR")"

echo "[uploads] primary_dir=$UPLOAD_DIR present=$UPLOAD_DIR_PRESENT"
echo "[uploads] compat_dir=$UPLOAD_DIR_COMPAT present=$([ -d "$UPLOAD_DIR_COMPAT" ] && echo true || echo false)"
echo "[uploads] mp4=$(count_ext "$UPLOAD_DIR" mp4) webm=$(count_ext "$UPLOAD_DIR" webm) mov=$(count_ext "$UPLOAD_DIR" mov) ogg=$(count_ext "$UPLOAD_DIR" ogg)"
if [ "$UPLOAD_DIR_PRESENT" = "true" ]; then
  echo "[uploads] latest videos:"
  find "$UPLOAD_DIR" -type f \( -iname "*.mp4" -o -iname "*.webm" -o -iname "*.mov" -o -iname "*.ogg" \) -printf "%T@ %s %TY-%Tm-%Td %TH:%TM %f\n" 2>/dev/null \
    | sort -nr \
    | head -n 5 \
    | awk '{printf "%s size=%s mtime=%s %s name=%s\n", "[uploads]", $2, $3, $4, substr($0, index($0,$5))}'
fi

HEALTH_OK=false
RECENT_API_OK=false
UPLOADS_STATIC_OK=false
DASHBOARD_REACHABLE=false
TEACHER_RESULTS_REACHABLE=false
TEACHER_REPORTS_REACHABLE=false
ADMIN_INGESTION_REACHABLE=false

if [ "$PORT_8011_LISTENING" = "true" ]; then
  HEALTH_STATUS="$(http_status "$BASE_URL/health")"
  RECENT_STATUS="$(http_status "$BASE_URL/api/recent-interaction-results?limit=1")"
  UPLOADS_STATUS="$(http_status "$BASE_URL/uploads/video.mp4")"
  DASHBOARD_STATUS="$(http_status "$BASE_URL/dashboard")"
  TEACHER_RESULTS_STATUS="$(http_status "$BASE_URL/teacher/results")"
  TEACHER_REPORTS_STATUS="$(http_status "$BASE_URL/teacher/reports")"
  ADMIN_INGESTION_STATUS="$(http_status "$BASE_URL/admin/ingestion")"

  [ "$HEALTH_STATUS" = "200" ] && HEALTH_OK=true
  [ "$RECENT_STATUS" = "200" ] && RECENT_API_OK=true
  [ "$UPLOADS_STATUS" = "200" ] && UPLOADS_STATIC_OK=true
  DASHBOARD_REACHABLE="$(reachable_status "$DASHBOARD_STATUS")"
  TEACHER_RESULTS_REACHABLE="$(reachable_status "$TEACHER_RESULTS_STATUS")"
  TEACHER_REPORTS_REACHABLE="$(reachable_status "$TEACHER_REPORTS_STATUS")"
  ADMIN_INGESTION_REACHABLE="$(reachable_status "$ADMIN_INGESTION_STATUS")"

  echo "[http] /health status=$HEALTH_STATUS"
  echo "[http] /api/recent-interaction-results?limit=1 status=$RECENT_STATUS"
  echo "[http] /uploads/video.mp4 status=$UPLOADS_STATUS $(http_content_type "$BASE_URL/uploads/video.mp4")"
  echo "[http] /dashboard status=$DASHBOARD_STATUS"
  echo "[http] /teacher/results status=$TEACHER_RESULTS_STATUS"
  echo "[http] /teacher/reports status=$TEACHER_REPORTS_STATUS"
  echo "[http] /admin/ingestion status=$ADMIN_INGESTION_STATUS"
else
  echo "[http] 8011 is not listening; skipping HTTP checks."
fi

if [ "$CLOUD_PROJECT_PRESENT" = "true" ] \
  && [ "$POSTGRES_RUNTIME_ENV_PRESENT" = "true" ] \
  && [ "$PORT_8011_LISTENING" = "true" ] \
  && [ "$HEALTH_OK" = "true" ] \
  && [ "$RECENT_API_OK" = "true" ] \
  && [ "$UPLOAD_DIR_PRESENT" = "true" ] \
  && [ "$UPLOADS_STATIC_OK" = "true" ] \
  && [ "$DASHBOARD_REACHABLE" = "true" ]; then
  CLOUD_RUNTIME_READY=true
else
  CLOUD_RUNTIME_READY=false
fi

print_marker "PHASE35A_CLOUD_PROJECT_PRESENT" "$CLOUD_PROJECT_PRESENT"
print_marker "PHASE35A_POSTGRES_RUNTIME_ENV_PRESENT" "$POSTGRES_RUNTIME_ENV_PRESENT"
print_marker "PHASE35A_RUNTIME_ENV_PRESENT" "$RUNTIME_ENV_PRESENT"
print_marker "PHASE35A_SERVICE_EXAMPLE_PRESENT" "$SERVICE_EXAMPLE_PRESENT"
print_marker "PHASE35A_DB_BACKEND" "$DB_BACKEND"
print_marker "PHASE35A_PORT_8011_LISTENING" "$PORT_8011_LISTENING"
print_marker "PHASE35A_PORT_8010_LISTENING" "$PORT_8010_LISTENING"
print_marker "PHASE35A_SERVICE_PROCESS_PRESENT" "$SERVICE_PROCESS_PRESENT"
print_marker "PHASE35A_SYSTEMD_SERVICE_STATE" "$SYSTEMD_SERVICE_STATE"
print_marker "PHASE35A_UPLOAD_DIR_PRESENT" "$UPLOAD_DIR_PRESENT"
print_marker "PHASE35A_UPLOAD_VIDEO_PRESENT" "$UPLOAD_VIDEO_PRESENT"
print_marker "PHASE35A_UPLOAD_VIDEO_COUNT" "$UPLOAD_VIDEO_COUNT"
print_marker "PHASE35A_HEALTH_OK" "$HEALTH_OK"
print_marker "PHASE35A_RECENT_API_OK" "$RECENT_API_OK"
print_marker "PHASE35A_UPLOADS_STATIC_OK" "$UPLOADS_STATIC_OK"
print_marker "PHASE35A_DASHBOARD_REACHABLE" "$DASHBOARD_REACHABLE"
print_marker "PHASE35A_TEACHER_RESULTS_REACHABLE" "$TEACHER_RESULTS_REACHABLE"
print_marker "PHASE35A_TEACHER_REPORTS_REACHABLE" "$TEACHER_REPORTS_REACHABLE"
print_marker "PHASE35A_ADMIN_INGESTION_REACHABLE" "$ADMIN_INGESTION_REACHABLE"
print_marker "PHASE35A_CLOUD_RUNTIME_READY" "$CLOUD_RUNTIME_READY"
