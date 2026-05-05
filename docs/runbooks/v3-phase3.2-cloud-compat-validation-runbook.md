# V3 Phase 3.2 Cloud Enhanced JSON Compatibility Validation Runbook

## Scope

Phase 3.2 verifies that the cloud can accept, preserve, return, and lightly display optional enhanced JSON fields produced by the local analyzer.

This runbook does not introduce new APIs, database migrations, upload authentication, or video processing.

## Prerequisites

- Cloud service is running on port `8011`.
- Phase 2.9 auth seed users exist.
- The service uses the same runtime environment as previous Phase 2.9 / Phase 3.0 validation.
- Sample file exists at `samples/phase3_2_enhanced_result.json`.

Seed users:

- Teacher: `teacher` / `teacher123`
- Admin: `admin` / `admin123`

## Static Check

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
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_2_cloud_compat.sh
```

Expected markers:

```text
PHASE32_CLOUD_UPLOAD_OK=true
PHASE32_RAW_PRESERVED=true
PHASE32_TEACHER_LOGIN_OK=true
PHASE32_DETAIL_ENHANCED_FIELDS_PRESENT=true
PHASE32_DASHBOARD_OK=true
PHASE32_REPORTS_OK=true
PHASE32_REGRESSION_OK=true
```

## Browser Acceptance URLs

Open these after logging in as `teacher`:

```text
http://<server>:8011/dashboard?result_id=phase3_2_enhanced_sample_001
http://<server>:8011/teacher/reports?result_id=phase3_2_enhanced_sample_001
```

Optional admin compatibility check:

```text
http://<server>:8011/admin/ingestion
```

## Manual Acceptance Points

- Uploading the Phase 3.2 sample returns HTTP 200.
- The returned `saved_path` exists on the server.
- Raw JSON contains `"analysis_version": "3.2"`.
- `GET /api/teacher/results/phase3_2_enhanced_sample_001` exposes `quality_metrics`, `score_breakdown`, and `enhanced_issues` either at top level, under `phase32`, or inside `raw_payload`.
- `/dashboard` shows the enhanced confidence / score explanation block when the sample result is selected.
- `/teacher/reports?result_id=phase3_2_enhanced_sample_001` shows enhanced issues as rule-based analysis advice.
- Old JSON remains valid because all Phase 3.2 fields are optional.

## Notes

- `samples/` is ignored by the repository `.gitignore`; the sample is for local/server validation and should be staged intentionally only if the git boundary is changed later.
- If login returns `503`, run the Phase 2.9 auth schema setup and start the service with the PostgreSQL runtime environment.
