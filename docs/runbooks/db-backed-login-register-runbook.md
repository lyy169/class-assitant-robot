# DB-backed Login/Register Runbook

## Scope

The cloud website supports database-backed authentication:

- Login reads from PostgreSQL `users`.
- Public registration requires QQ email verification and writes a teacher user to PostgreSQL `users`.
- Optional classroom binding writes to `teacher_classrooms`.
- Admin user creation through `/api/admin/users` remains available.

Public registration only creates `teacher` accounts. Admin accounts must be created by an existing admin or seed script.

## Prepare Schema

Run this on the cloud server:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/setup_phase2_9_auth_schema.sh
```

For a fresh PostgreSQL database, `scripts/setup_postgres_schema.sh` has also been updated to include the auth columns and `teacher_classrooms`.

## Configure QQ Mail SMTP

Add these values to `/root/video_project_src/cloud_backend/.env.postgres.runtime`.

Do not print or commit the real authorization code.

```bash
CLOUD_SMTP_HOST=smtp.qq.com
CLOUD_SMTP_PORT=465
CLOUD_SMTP_USE_SSL=true
CLOUD_SMTP_USERNAME=<your_qq_email@qq.com>
CLOUD_SMTP_PASSWORD=<your_qq_mail_authorization_code>
CLOUD_SMTP_FROM=<your_qq_email@qq.com>
CLOUD_EMAIL_CODE_EXPIRE_MINUTES=10
CLOUD_EMAIL_CODE_COOLDOWN_SECONDS=60
```

## Restart Service

If running through systemd:

```bash
systemctl restart classroom-cloud-backend.service
systemctl is-active classroom-cloud-backend.service
```

If running manually, stop the old uvicorn process and start it again with the PostgreSQL runtime environment.

## Validate

Basic validation checks page rendering and security guards. It does not print the password, token, or verification code.

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_db_backed_register_login.sh
```

Expected basic marker:

```text
DB_BACKED_REGISTER_SECURITY_READY=true
```

For full email registration validation, first request a code to a QQ mailbox:

```bash
API_BASE_URL="http://127.0.0.1:8011" REGISTER_EMAIL="<your_test_qq@qq.com>" bash scripts/validate_db_backed_register_login.sh
```

Then rerun with the code received in QQ Mail:

```bash
API_BASE_URL="http://127.0.0.1:8011" REGISTER_EMAIL="<your_test_qq@qq.com>" REGISTER_CODE="<code_from_email>" bash scripts/validate_db_backed_register_login.sh
```

Expected full marker:

```text
DB_BACKED_REGISTER_LOGIN_OK=true
```

## User-facing URLs

- Login page: `/login`
- Register page: `/register`
- Login API: `POST /api/auth/login`
- Send code API: `POST /api/auth/send-register-code`
- Register API: `POST /api/auth/register`
