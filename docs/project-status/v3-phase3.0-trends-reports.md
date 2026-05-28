# V3 Phase 3.0 Status: Teaching Trends And Classroom Report Center

## 1. Status

Cloud-side implementation completed in the SSHFS workspace. Runtime validation must be executed on the Linux server after backend restart.

## 2. Goal

Upgrade the platform from single-result viewing to longitudinal teaching analysis.

Target:

```text
teacher trend analysis
classroom report center
admin trend overview
rule-based teaching recommendations
optional AI summary
demo data without polluting real analysis
```

## 3. Confirmed Scope

In scope:

- `/teacher/trends`
- `/teacher/reports`
- `/admin/trends`
- teacher trends API
- teacher reports API
- report detail API
- optional AI summary API
- admin trends API
- rule report generator
- demo trend seed script
- data_source filtering
- validation script

Out of scope:

- PDF export
- Excel export
- AI summary cache
- report snapshot table
- trend AI summary
- student-level profile
- video asset hosting
- device upload auth

## 4. Data Credibility Decision

Default analysis uses:

```text
data_source=real
```

Demo data must be marked:

```text
dataset.source=demo
dataset.purpose=phase3_trend_seed
```

Pages must show a warning when `data_source=demo` or `data_source=all`.

## 5. AI Summary Decision

Rule report is mandatory.

AI summary is optional:

- single-lesson report only
- button triggered
- no cache
- environment controlled
- failure does not break report

## 6. Expected Files

Likely modified or added files:

- `cloud_backend/postgres_repository.py`
- `cloud_backend/repository_interface.py`
- `cloud_backend/teacher_pages.py`
- `cloud_backend/admin_pages.py`
- `cloud_backend/reporting.py`
- `cloud_backend/ai_report.py`
- `cloud_backend/auth.py`
- `scripts/seed_phase3_demo_trend_data.sh`
- `scripts/validate_phase3_trends_reports.sh`
- Phase 3.0 docs

## 7. Implementation Result

Implemented.

Modified files:

- `cloud_backend/postgres_repository.py`
- `cloud_backend/auth.py`
- `cloud_backend/main.py`
- `cloud_backend/teacher_pages.py`
- `cloud_backend/admin_pages.py`
- `cloud_backend/reporting.py`
- `cloud_backend/ai_report.py`
- `scripts/seed_phase3_demo_trend_data.sh`
- `scripts/validate_phase3_trends_reports.sh`
- `docs/project-status/v3-phase3.0-trends-reports.md`

APIs:

- `GET /api/teacher/trends`
- `GET /api/teacher/reports`
- `GET /api/teacher/reports/detail?result_id=<result_id>`
- `POST /api/teacher/reports/ai-summary`
- `GET /api/admin/trends`

Pages:

- `GET /teacher/trends`
- `GET /teacher/reports`
- `GET /teacher/reports?result_id=<result_id>`
- `GET /admin/trends`

Validation command:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" CLASSROOM_ID="classroom_101" bash scripts/validate_phase3_trends_reports.sh
```

Validation result:

```text
Static compile passed in SSHFS workspace:
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py

Runtime validation: pending operator execution on Linux server.
```

## 8. Data Source Filtering

Implemented for trend/report APIs:

- Default `data_source=real`.
- Missing `payload_json.dataset.source` is treated as `real`.
- `dataset.source=demo` is only returned when `data_source=demo` or `data_source=all`.
- Unknown dataset sources are excluded from `real` and `all`.
- API responses include `filters.data_source`.
- Teacher and admin pages show demo/all warnings.

## 9. Rule Report

Implemented in:

```text
cloud_backend/reporting.py
```

The rule report generates:

- `highlights`
- `risks`
- `recommendations`
- `risk_level`

Rules cover low attention, low activity, low question count, low response rate, high management ratio, and high issue count. Report detail works without AI.

## 10. Optional AI Summary

Implemented in:

```text
cloud_backend/ai_report.py
```

Behavior:

- Disabled/unconfigured returns `not_configured`.
- Only single report summary is supported.
- Button-triggered from report detail page.
- No cache.
- Uses structured report summary only, not full raw JSON.
- Failure returns controlled `failed` status and does not break rule report.

Environment variables:

```text
AI_REPORT_ENABLED=true/false
AI_REPORT_PROVIDER=deepseek
AI_REPORT_API_KEY=...
AI_REPORT_MODEL=...
AI_REPORT_TIMEOUT=20
```

## 11. Demo Seed / Cleanup

Script:

```text
scripts/seed_phase3_demo_trend_data.sh
```

Commands:

```bash
API_BASE_URL="http://127.0.0.1:8011" CLASSROOM_ID="classroom_101" bash scripts/seed_phase3_demo_trend_data.sh --seed
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/seed_phase3_demo_trend_data.sh --cleanup
```

Seed behavior:

- Generates 8 `demo_phase3_*` results.
- Adds `dataset.source=demo`.
- Adds `dataset.purpose=phase3_trend_seed`.
- Uploads through `POST /api/interaction-results`.

Cleanup behavior:

- Deletes only `demo_phase3_*` or `dataset.source=demo` / `dataset.purpose=phase3_trend_seed` rows.
- Does not touch real records.

## 12. Expected Validation Markers

```text
PHASE30_TEACHER_LOGIN_OK=true
PHASE30_TEACHER_TRENDS_PAGE_OK=true
PHASE30_TEACHER_TRENDS_API_OK=true
PHASE30_TEACHER_REPORTS_PAGE_OK=true
PHASE30_TEACHER_REPORTS_API_OK=true
PHASE30_TEACHER_REPORT_DETAIL_API_OK=true
PHASE30_ADMIN_LOGIN_OK=true
PHASE30_ADMIN_TRENDS_PAGE_OK=true
PHASE30_ADMIN_TRENDS_API_OK=true
PHASE30_DATA_SOURCE_DEFAULT_REAL_OK=true
PHASE30_DEMO_FILTER_OK=true
PHASE30_AI_OPTIONAL_OK=true
PHASE30_AUTH_REGRESSION_OK=true
PHASE30_INGESTION_REGRESSION_OK=true
PHASE30_REGRESSION_OK=true
```

## 13. Browser Acceptance URLs

Teacher:

```text
http://<server>:8011/login
http://<server>:8011/teacher/trends
http://<server>:8011/teacher/reports
http://<server>:8011/teacher/reports?result_id=cls_20260417_101_001
```

Admin:

```text
http://<server>:8011/admin/trends
```

## 14. Residual Risks

- Runtime validation is pending until the server process is restarted.
- Real trend quality depends on having multiple real uploaded classroom records.
- AI summary requires external provider configuration and network access; unconfigured behavior is expected and non-blocking.
- Demo seed cleanup uses database access through `ENV_FILE`; verify `CLOUD_DATABASE_URL` before cleanup.

## 15. Acceptance Criteria

Pass when:

- teacher can open `/teacher/trends`
- teacher trends API returns success
- teacher can open `/teacher/reports`
- report detail returns rule report
- AI unconfigured does not break report
- admin can open `/admin/trends`
- admin trends API returns success
- default data_source is real
- demo data can be filtered separately
- teacher permissions are respected
- Phase 2.9 auth still works
- Phase 2.8 ingestion still works

## 16. Git Boundary

Phase 3.0 must not use `git add .`.

Only stage files explicitly modified for:

```text
trends
reports
rule recommendations
optional AI summary
demo trend seed
Phase 3.0 docs
validation script
```

Historical dirty files recorded in:

```text
docs/project-status/git-working-tree-boundary-after-phase2.8.1.md
```

must not be swept into Phase 3.0 commits.
