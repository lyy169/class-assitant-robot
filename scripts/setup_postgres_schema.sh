#!/bin/bash
set -euo pipefail

CLOUD_SRC_DIR="${CLOUD_SRC_DIR:-/root/video_project_src}"
CLOUD_DATABASE_URL="${CLOUD_DATABASE_URL:-${POSTGRES_URL:-}}"
SEED_ADMIN="${SEED_ADMIN:-true}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin-change-me}"

if [ -z "${CLOUD_DATABASE_URL}" ]; then
  echo "[error] CLOUD_DATABASE_URL is required" >&2
  echo "example: CLOUD_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/classroom_cloud bash scripts/setup_postgres_schema.sh" >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "[error] psql is required on the Linux server" >&2
  exit 1
fi

echo "[step] creating PostgreSQL schema"
psql "${CLOUD_DATABASE_URL}" <<'SQL'
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    display_name TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
UPDATE users
SET user_id = (
    substr(md5(random()::text || clock_timestamp()::text || COALESCE(username, 'user')), 1, 8) || '-' ||
    substr(md5(random()::text || clock_timestamp()::text || COALESCE(username, 'user')), 9, 4) || '-' ||
    substr(md5(random()::text || clock_timestamp()::text || COALESCE(username, 'user')), 13, 4) || '-' ||
    substr(md5(random()::text || clock_timestamp()::text || COALESCE(username, 'user')), 17, 4) || '-' ||
    substr(md5(random()::text || clock_timestamp()::text || COALESCE(username, 'user')), 21, 12)
)::uuid
WHERE user_id IS NULL;
UPDATE users SET display_name = username WHERE display_name IS NULL OR display_name = '';
ALTER TABLE users ALTER COLUMN user_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users(lower(email)) WHERE email IS NOT NULL AND email <> '';

CREATE TABLE IF NOT EXISTS classrooms (
    id BIGSERIAL PRIMARY KEY,
    classroom_id TEXT NOT NULL UNIQUE,
    name TEXT,
    teacher_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS teacher_classrooms (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    classroom_id TEXT NOT NULL,
    classroom_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, classroom_id)
);

CREATE TABLE IF NOT EXISTS auth_email_verification_codes (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'register',
    attempts INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_email_codes_email_created ON auth_email_verification_codes(email, purpose, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_email_codes_expires ON auth_email_verification_codes(expires_at);

CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    classroom_id TEXT NOT NULL,
    analysis_id TEXT NOT NULL UNIQUE,
    video_id TEXT,
    recorded_at TIMESTAMPTZ,
    generated_at TIMESTAMPTZ,
    duration_seconds DOUBLE PRECISION,
    raw_json_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id BIGSERIAL PRIMARY KEY,
    analysis_id TEXT NOT NULL UNIQUE,
    session_id BIGINT REFERENCES sessions(id) ON DELETE SET NULL,
    classroom_id TEXT NOT NULL,
    schema_version TEXT,
    source_kind TEXT NOT NULL DEFAULT 'raw',
    source_path TEXT NOT NULL,
    source_host TEXT,
    generated_at TIMESTAMPTZ,
    feedback_score DOUBLE PRECISION,
    attention_score DOUBLE PRECISION,
    response_score DOUBLE PRECISION,
    classroom_name TEXT,
    lesson_title TEXT,
    status TEXT NOT NULL DEFAULT 'raw',
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_classrooms_teacher_user_id ON classrooms(teacher_user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_classroom_generated ON sessions(classroom_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_results_classroom_generated ON analysis_results(classroom_id, generated_at DESC);

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS raw_json_path TEXT;
ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS classroom_name TEXT;
ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS lesson_title TEXT;
ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'raw';
ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
ALTER TABLE analysis_results ALTER COLUMN classroom_id DROP NOT NULL;
UPDATE analysis_results SET status = 'raw' WHERE status IS NULL OR status = '';
UPDATE analysis_results SET updated_at = COALESCE(updated_at, created_at, now());
CREATE INDEX IF NOT EXISTS idx_analysis_results_status_created ON analysis_results(status, created_at DESC);
SQL

if [ "${SEED_ADMIN}" = "true" ]; then
  echo "[step] ensuring seed admin user exists"
  cd "${CLOUD_SRC_DIR}"
  export CLOUD_DATABASE_URL ADMIN_USERNAME ADMIN_PASSWORD
  python3 - <<'PY'
import os
import uuid
import psycopg2

from cloud_backend.security import hash_password

database_url = os.environ["CLOUD_DATABASE_URL"]
admin_username = os.environ.get("ADMIN_USERNAME", "admin")
admin_password = os.environ.get("ADMIN_PASSWORD", "admin-change-me")

with psycopg2.connect(database_url) as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (user_id, username, display_name, password_hash, role, is_active)
            VALUES (%s::uuid, %s, %s, %s, 'admin', TRUE)
            ON CONFLICT (username) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                display_name = EXCLUDED.display_name,
                role = 'admin',
                is_active = TRUE,
                updated_at = now()
            """,
            (str(uuid.uuid4()), admin_username, admin_username, hash_password(admin_password)),
        )

print(f"[info] seed admin ensured: {admin_username}")
PY
fi

echo "[done] PostgreSQL schema setup completed"
