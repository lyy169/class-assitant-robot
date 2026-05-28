# Phase 3.17 Frontend Sample Scope Runbook

## Purpose

Validate that the cloud frontend consistently uses the final ASR-enhanced classroom sample and keeps historical, smoke-test, legacy-test, and demo data clearly separated.

## Static Validation

From `/root/video_project_src`:

```bash
source /root/venv/bin/activate
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/dashboard_v11.py cloud_backend/main.py
bash -n scripts/validate_phase3_17_frontend_sample_scope.sh
```

## Restart

If code was changed and the running service does not hot-reload, restart manually:

```bash
systemctl restart classroom-cloud-backend.service
systemctl is-active classroom-cloud-backend.service
```

If this server is currently run by a foreground `uvicorn` process rather than systemd, stop that process intentionally and start the backend using the existing project command/runbook. Do not delete data or alter PostgreSQL.

## Runtime Validation

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_17_frontend_sample_scope.sh
```

Expected:

```text
PHASE317_FRONTEND_SAMPLE_SCOPE_READY=true
```

## Manual Pages

Open these pages after login:

- `/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17`
- `/teacher`
- `/teacher/results`
- `/teacher/reports`
- `/teacher/reports?result_id=phase314_asr_full_classroom_sav_20200908_17`
- `/teacher/trends`
- `/admin`
- `/admin/results`
- `/admin/trends`

Confirm:

- The final sample is labeled as an ASR-enhanced full-classroom SAV sample.
- SAV is not described as Raspberry Pi capture or self-capture.
- Historical and smoke-test records are not default formal list items.
- Legacy all-zero test records are not default formal list items.
- Demo data is labeled when demo/all filters are used.
- No fake attention, student-count, or stage-distribution values are introduced.
