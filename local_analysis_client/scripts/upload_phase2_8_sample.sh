#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: API_BASE_URL=\"http://<cloud-host>:8011\" bash scripts/upload_phase2_8_sample.sh <result-json>" >&2
  exit 2
fi

RESULT_JSON="$1"
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
TARGET_URL="${API_BASE_URL%/}/api/interaction-results"

curl -i -X POST "$TARGET_URL" \
  -H "Content-Type: application/json" \
  --data-binary @"$RESULT_JSON"
