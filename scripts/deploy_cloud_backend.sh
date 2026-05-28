#!/bin/bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/root/video_project_src}"
VENV_DIR="${VENV_DIR:-/root/venv}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/cloud_backend/.env.runtime}"

echo "[info] PROJECT_DIR=${PROJECT_DIR}"
echo "[info] VENV_DIR=${VENV_DIR}"
echo "[info] ENV_FILE=${ENV_FILE}"

if [ ! -d "${PROJECT_DIR}" ]; then
  echo "[error] project directory not found: ${PROJECT_DIR}" >&2
  exit 1
fi

if [ ! -f "${VENV_DIR}/bin/activate" ]; then
  echo "[error] virtualenv activate script not found: ${VENV_DIR}/bin/activate" >&2
  exit 1
fi

cd "${PROJECT_DIR}"
source "${VENV_DIR}/bin/activate"

if [ -f "${ENV_FILE}" ]; then
  echo "[step] loading runtime environment from ${ENV_FILE}"
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
else
  echo "[warn] runtime env file not found; falling back to current shell env and code defaults"
fi

echo "[step] ensuring python dependencies are installed"
pip install -r cloud_backend/requirements.txt

echo "[step] starting cloud backend"
echo "[info] CLOUD_HOST=${CLOUD_HOST:-0.0.0.0}"
echo "[info] CLOUD_PORT=${CLOUD_PORT:-8011}"
echo "[info] CLOUD_DB_BACKEND=${CLOUD_DB_BACKEND:-file}"
echo "[info] CLOUD_DATABASE_URL=${CLOUD_DATABASE_URL:-}"
echo "[info] CLOUD_RAW_DIR=${CLOUD_RAW_DIR:-${PROJECT_DIR}/cloud_backend/data/raw}"

exec uvicorn cloud_backend.main:app --host "${CLOUD_HOST:-0.0.0.0}" --port "${CLOUD_PORT:-8011}"
