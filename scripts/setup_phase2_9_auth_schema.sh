#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/cloud_backend/.env.postgres.runtime}"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

DATABASE_URL="${CLOUD_DATABASE_URL:-${POSTGRES_URL:-}}"
if [ -z "${DATABASE_URL}" ]; then
  echo "[error] CLOUD_DATABASE_URL or POSTGRES_URL is required" >&2
  exit 1
fi

ADMIN_HASH="$(PYTHONPATH="${ROOT_DIR}" python -c 'from cloud_backend.security import hash_password; print(hash_password("admin123"))')"
TEACHER_HASH="$(PYTHONPATH="${ROOT_DIR}" python -c 'from cloud_backend.security import hash_password; print(hash_password("teacher123"))')"
ADMIN_USER_ID="$(python -c 'import uuid; print(uuid.uuid4())')"
TEACHER_USER_ID="$(python -c 'import uuid; print(uuid.uuid4())')"

psql "${DATABASE_URL}" \
  -v ON_ERROR_STOP=1 \
  -v admin_hash="${ADMIN_HASH}" \
  -v teacher_hash="${TEACHER_HASH}" \
  -v admin_user_id="${ADMIN_USER_ID}" \
  -v teacher_user_id="${TEACHER_USER_ID}" <<'SQL'

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL,
    user_id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('teacher', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS id BIGSERIAL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'teacher';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
UPDATE users SET user_id = :'teacher_user_id' WHERE username = 'teacher' AND user_id IS NULL;
UPDATE users SET user_id = :'admin_user_id' WHERE username = 'admin' AND user_id IS NULL;
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
UPDATE users SET password_hash = :'teacher_hash' WHERE password_hash IS NULL OR password_hash = '';
UPDATE users SET role = 'teacher' WHERE role IS NULL OR role = '';
ALTER TABLE users ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;
ALTER TABLE users ALTER COLUMN role SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);

CREATE TABLE IF NOT EXISTS teacher_classrooms (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    classroom_id TEXT NOT NULL,
    classroom_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, classroom_id)
);

INSERT INTO users (user_id, username, display_name, password_hash, role, is_active)
VALUES (:'admin_user_id', 'admin', 'Demo Admin', :'admin_hash', 'admin', TRUE)
ON CONFLICT (username) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    is_active = TRUE,
    updated_at = now();

INSERT INTO users (user_id, username, display_name, password_hash, role, is_active)
VALUES (:'teacher_user_id', 'teacher', 'Demo Teacher', :'teacher_hash', 'teacher', TRUE)
ON CONFLICT (username) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    password_hash = EXCLUDED.password_hash,
    role = EXCLUDED.role,
    is_active = TRUE,
    updated_at = now();

INSERT INTO teacher_classrooms (user_id, classroom_id, classroom_name)
SELECT user_id, 'classroom_101', 'classroom_101'
FROM users
WHERE username = 'teacher'
ON CONFLICT (user_id, classroom_id) DO UPDATE SET
    classroom_name = EXCLUDED.classroom_name;
SQL

echo "[done] Phase 2.9 auth schema and seed users are ready"
