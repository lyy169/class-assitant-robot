# V3 Phase 3.3 Cloud Teacher Question Guidance Validation Runbook

## Scope

Phase 3.3 validates cloud-side compatibility and display for optional teacher question guidance fields:

- `teacher_question_events`
- `question_guidance_summary`

The phase does not change the upload API, database schema, permission model, Raspberry Pi code, or local analyzer code.

## Prerequisites

- Cloud service is running with PostgreSQL runtime configuration on port `8011`.
- Phase 2.9 auth seed users exist.
- Sample file exists at `samples/phase3_3_question_guidance_result.json`.

Seed user for validation:

```text
teacher / teacher123
```

## Static Validation

```bash
cd /root/video_project_src
python -m py_compile \
  cloud_backend/repository_interface.py \
  cloud_backend/storage.py \
  cloud_backend/postgres_repository.py \
  cloud_backend/auth.py \
  cloud_backend/main.py \
  cloud_backend/dashboard_v11.py \
  cloud_backend/teacher_pages.py \
  cloud_backend/admin_pages.py \
  cloud_backend/security.py \
  cloud_backend/login_pages.py \
  cloud_backend/reporting.py \
  cloud_backend/ai_report.py \
  cloud_backend/ui_style.py
```

## Runtime Validation

```bash
cd /root/video_project_src
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_3_cloud_question_guidance.sh
```

Expected markers:

```text
PHASE33_CLOUD_UPLOAD_OK=true
PHASE33_RAW_QUESTION_FIELDS_PRESERVED=true
PHASE33_TEACHER_LOGIN_OK=true
PHASE33_DETAIL_QUESTION_FIELDS_PRESENT=true
PHASE33_DASHBOARD_OK=true
PHASE33_REPORTS_OK=true
PHASE33_REGRESSION_OK=true
```

## Browser Acceptance URLs

After runtime validation uploads the sample, open:

```text
http://<server>:8011/dashboard?result_id=phase3_3_question_guidance_sample_001
http://<server>:8011/teacher/reports?result_id=phase3_3_question_guidance_sample_001
```

## Manual Acceptance Points

- Raw JSON preserves `teacher_question_events` and `question_guidance_summary`.
- Detail API exposes both fields directly, under `phase33`, or through `raw_payload`.
- `/dashboard` shows the teacher question guidance block.
- `/teacher/reports` shows teaching-guidance analysis.
- Old results without these fields still render without errors.
- Demo/sample data is labeled as demo where the question guidance summary indicates `demo` or `demo_seed`.
