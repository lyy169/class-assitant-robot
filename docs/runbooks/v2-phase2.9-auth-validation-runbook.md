# V2 Phase 2.9 Runbook: Auth And Permission Validation

## 1. Purpose

Validate Phase 2.9 login, role routing, and permission boundaries.

## 2. Prepare Database

On cloud server:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/setup_phase2_9_auth_schema.sh
```

Expected seed users:

```text
admin / admin123
teacher / teacher123
```

Expected teacher binding:

```text
teacher -> classroom_101
```

## 3. Start Service

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

## 4. Run Validation Script

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase2_9_auth.sh
```

Expected markers:

```text
PHASE29_LOGIN_PAGE_OK=true
PHASE29_TEACHER_LOGIN_OK=true
PHASE29_ADMIN_LOGIN_OK=true
PHASE29_AUTH_ME_OK=true
PHASE29_LOGOUT_OK=true
PHASE29_TEACHER_PAGE_OK=true
PHASE29_TEACHER_ADMIN_BLOCKED=true
PHASE29_ADMIN_PAGE_OK=true
PHASE29_ADMIN_API_PROTECTED=true
PHASE29_TEACHER_CLASSROOM_FILTER_OK=true
PHASE29_UPLOAD_API_STILL_OPEN=true
PHASE29_INGESTION_AFTER_LOGIN_OK=true
PHASE29_REGRESSION_OK=true
```

## 5. Browser Validation

Open:

```text
http://<server-ip>:8011/login
```

Validate teacher:

- use `teacher / teacher123`
- redirects to `/teacher`
- user bar shows teacher identity
- `/teacher/results` shows only teacher-visible classrooms
- `/admin` is blocked

Validate admin:

- logout
- use `admin / admin123`
- redirects to `/admin`
- user bar shows admin identity
- `/admin/ingestion` opens
- Phase 2.8.1 standardized video metadata remains visible

Validate dashboard:

```text
/dashboard?result_id=<known result id>
```

Rules:

- admin can open
- teacher can open only if result classroom is bound to teacher

## 6. Upload Compatibility

Confirm the upload API remains available without browser login:

```bash
curl -i -XPOST "http://127.0.0.1:8011/api/interaction-results" \
  -H "Content-Type: application/json" \
  -d @<known-valid-result-json>
```

Expected:

```text
HTTP 200
success=true
```

## 7. Final Report Template

```text
Phase 2.9 validation result:
- schema setup:
- login page:
- teacher login:
- admin login:
- teacher page:
- admin page:
- teacher classroom filtering:
- admin API protection:
- dashboard permission:
- upload API compatibility:
- Phase 2.8.1 ingestion compatibility:
- unresolved issue:
```

