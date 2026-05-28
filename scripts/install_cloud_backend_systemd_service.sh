#!/bin/bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-classroom-cloud-backend.service}"
PROJECT_DIR="${PROJECT_DIR:-/root/video_project_src}"
VENV_DIR="${VENV_DIR:-/root/venv}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/cloud_backend/.env.postgres.runtime}"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
START_MODE="none"
ENABLE_SERVICE=true

usage() {
  cat <<'EOF'
Usage:
  bash scripts/install_cloud_backend_systemd_service.sh [--start|--restart] [--no-enable]

Installs the cloud backend as a systemd daemon.

Options:
  --start      Install, enable, and start the service if it is not running.
  --restart    Install, enable, and restart the service.
  --no-enable  Install without enabling boot auto-start.

Environment overrides:
  SERVICE_NAME  default: classroom-cloud-backend.service
  PROJECT_DIR   default: /root/video_project_src
  VENV_DIR      default: /root/venv
  ENV_FILE      default: /root/video_project_src/cloud_backend/.env.postgres.runtime
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --start)
      START_MODE="start"
      ;;
    --restart)
      START_MODE="restart"
      ;;
    --no-enable)
      ENABLE_SERVICE=false
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$(id -u)" -ne 0 ]; then
  echo "[error] this installer must run as root because it writes ${SERVICE_PATH}" >&2
  exit 1
fi

if [ ! -d "${PROJECT_DIR}" ]; then
  echo "[error] project directory not found: ${PROJECT_DIR}" >&2
  exit 1
fi

if [ ! -x "${VENV_DIR}/bin/uvicorn" ]; then
  echo "[error] uvicorn executable not found: ${VENV_DIR}/bin/uvicorn" >&2
  exit 1
fi

if [ ! -f "${ENV_FILE}" ]; then
  echo "[error] runtime env file not found: ${ENV_FILE}" >&2
  exit 1
fi

echo "[info] installing ${SERVICE_NAME}"
echo "[info] project_dir=${PROJECT_DIR}"
echo "[info] venv_dir=${VENV_DIR}"
echo "[info] env_file=${ENV_FILE}"
echo "[info] service_path=${SERVICE_PATH}"

tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT

cat >"${tmp_file}" <<EOF
[Unit]
Description=Classroom Cloud Backend Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${ENV_FILE}
Environment=PYTHONUNBUFFERED=1
ExecStart=${VENV_DIR}/bin/uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8011
Restart=always
RestartSec=3
TimeoutStopSec=30
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
EOF

install -m 0644 "${tmp_file}" "${SERVICE_PATH}"
systemctl daemon-reload

if [ "${ENABLE_SERVICE}" = "true" ]; then
  systemctl enable "${SERVICE_NAME}" >/dev/null
  echo "[info] enabled ${SERVICE_NAME} for boot auto-start"
else
  echo "[info] skipped enable because --no-enable was provided"
fi

if command -v ss >/dev/null 2>&1; then
  echo "[info] current 8011 listener, if any:"
  ss -ltnp 'sport = :8011' 2>/dev/null || true
fi

case "${START_MODE}" in
  start)
    systemctl start "${SERVICE_NAME}"
    ;;
  restart)
    systemctl restart "${SERVICE_NAME}"
    ;;
  none)
    echo "[info] service installed but not started. Use --start or --restart to run it from this script."
    ;;
esac

echo "[info] systemd state:"
systemctl is-enabled "${SERVICE_NAME}" || true
systemctl is-active "${SERVICE_NAME}" || true
