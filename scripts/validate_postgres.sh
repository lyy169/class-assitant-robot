#!/bin/bash
set -euo pipefail

CLOUD_DATABASE_URL="${CLOUD_DATABASE_URL:-${POSTGRES_URL:-}}"
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"

if [ -z "${CLOUD_DATABASE_URL}" ]; then
  echo "[error] CLOUD_DATABASE_URL is required" >&2
  exit 1
fi

echo "[step] checking PostgreSQL tables"
psql "${CLOUD_DATABASE_URL}" -c "select table_name from information_schema.tables where table_schema = 'public' and table_name in ('users', 'classrooms', 'sessions', 'analysis_results') order by table_name;"

echo "[step] checking analysis_results rows"
psql "${CLOUD_DATABASE_URL}" -c "select analysis_id, classroom_id, source_kind, generated_at from analysis_results order by generated_at desc nulls last, created_at desc limit 5;"

echo "[step] checking cloud health endpoint"
curl -i "${API_BASE_URL}/health"

echo "[done] PostgreSQL validation commands completed"
