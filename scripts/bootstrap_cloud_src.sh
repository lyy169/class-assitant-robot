#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNING_DIR="${RUNNING_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
CLOUD_SRC_DIR="${CLOUD_SRC_DIR:-/home/${USER}/video_project_src}"

README_TEMPLATE="${SCRIPT_DIR}/templates/cloud_src_README.md.template"
GITIGNORE_TEMPLATE="${SCRIPT_DIR}/templates/cloud_src_gitignore.template"

echo "[info] RUNNING_DIR=${RUNNING_DIR}"
echo "[info] CLOUD_SRC_DIR=${CLOUD_SRC_DIR}"

if [ ! -d "${RUNNING_DIR}" ]; then
  echo "[error] Running directory does not exist: ${RUNNING_DIR}" >&2
  exit 1
fi

case "${CLOUD_SRC_DIR}" in
  "${RUNNING_DIR}"|\
  "${RUNNING_DIR}/"* )
    echo "[error] CLOUD_SRC_DIR must not be inside the running deployment directory." >&2
    exit 1
    ;;
esac

if [ -e "${CLOUD_SRC_DIR}" ]; then
  if [ -d "${CLOUD_SRC_DIR}" ] && [ -z "$(find "${CLOUD_SRC_DIR}" -mindepth 1 -maxdepth 1 2>/dev/null)" ]; then
    echo "[info] Target source directory already exists and is empty."
  else
    echo "[error] Target path already exists and is not an empty directory: ${CLOUD_SRC_DIR}" >&2
    echo "[hint] Move it away or choose another CLOUD_SRC_DIR before retrying." >&2
    exit 1
  fi
else
  mkdir -p "${CLOUD_SRC_DIR}"
fi

for item in cloud_backend docs scripts; do
  if [ ! -e "${RUNNING_DIR}/${item}" ]; then
    echo "[error] Missing required source item: ${RUNNING_DIR}/${item}" >&2
    exit 1
  fi
done

echo "[step] Copying first-batch managed assets"
cp -a "${RUNNING_DIR}/cloud_backend" "${CLOUD_SRC_DIR}/"
cp -a "${RUNNING_DIR}/docs" "${CLOUD_SRC_DIR}/"
cp -a "${RUNNING_DIR}/scripts" "${CLOUD_SRC_DIR}/"

echo "[step] Removing runtime-only and cache artifacts from copied source tree"
rm -rf "${CLOUD_SRC_DIR}/cloud_backend/data"
find "${CLOUD_SRC_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "${CLOUD_SRC_DIR}" -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.log" -o -name ".env" -o -name ".env.*" \) -delete

mkdir -p "${CLOUD_SRC_DIR}/legacy"

cat > "${CLOUD_SRC_DIR}/legacy/README.md" <<'EOF'
# Legacy Boundary

This directory is reserved for future legacy documentation and manifests.

It does not mean the running legacy assets have been copied here.

Current legacy/not-yet-managed scope includes:
- old Flask root app and related page assets
- `backend/`
- `frontend/`
- runtime-only directories such as `instance/`, `uploads/`, `logs/`, and `cloud_backend/data/`
EOF

if [ ! -f "${README_TEMPLATE}" ]; then
  echo "[error] Missing README template: ${README_TEMPLATE}" >&2
  exit 1
fi

if [ ! -f "${GITIGNORE_TEMPLATE}" ]; then
  echo "[error] Missing .gitignore template: ${GITIGNORE_TEMPLATE}" >&2
  exit 1
fi

cp "${README_TEMPLATE}" "${CLOUD_SRC_DIR}/README.md"
cp "${GITIGNORE_TEMPLATE}" "${CLOUD_SRC_DIR}/.gitignore"

echo "[step] Initializing Git repository"
cd "${CLOUD_SRC_DIR}"
git init
git checkout -b chore/cloud-src-bootstrap
git add .
git commit -m "chore: bootstrap cloud source repository"

echo "[done] Cloud source bootstrap completed."
echo "[done] Source directory: ${CLOUD_SRC_DIR}"
echo "[done] Current branch: $(git branch --show-current)"
echo "[done] Latest commit: $(git log -1 --oneline)"
