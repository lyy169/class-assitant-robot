# V3 Phase 3.0 Runbook: Trends And Reports Validation

## 1. Purpose

Validate Phase 3.0 teaching trends and classroom report center.

## 2. Optional Demo Data

Seed demo trend data if real data is insufficient:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/seed_phase3_demo_trend_data.sh --seed
```

Cleanup:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/seed_phase3_demo_trend_data.sh --cleanup
```

Demo data must be marked:

```text
dataset.source=demo
dataset.purpose=phase3_trend_seed
```

## 3. Start Service

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

## 4. Run Validation

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" CLASSROOM_ID="classroom_101" bash scripts/validate_phase3_trends_reports.sh
```

Expected markers:

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

## 5. Browser Validation

Teacher:

```text
http://<server>:8011/login
teacher / teacher123
http://<server>:8011/teacher/trends
http://<server>:8011/teacher/reports
http://<server>:8011/teacher/reports?result_id=<result_id>
```

Check:

- trend cards render
- charts render
- report list renders
- report detail renders
- rule recommendations show
- AI summary area does not break when unconfigured
- data source warning appears for demo/all

Admin:

```text
admin / admin123
http://<server>:8011/admin/trends
```

Check:

- global overview renders
- classroom ranking renders
- teacher activity renders
- risk lesson list renders

## 6. Data Credibility Validation

Confirm default real data behavior:

```text
/api/teacher/trends -> filters.data_source=real
```

Confirm demo data does not pollute real trend:

```text
/api/teacher/trends?data_source=demo -> demo only
/api/teacher/trends?data_source=all -> real + demo
```

## 7. AI Summary Validation

If AI is disabled/unconfigured:

```text
report detail still works
ai_summary.status=not_configured
```

If AI is enabled:

```text
POST /api/teacher/reports/ai-summary
```

must enforce result permission and return success or controlled failure without breaking the rule report.

## 8. Final Report Template

```text
Phase 3.0 validation result:
- demo data seed:
- teacher trends page:
- teacher trends API:
- teacher reports page:
- report detail:
- admin trends page:
- admin trends API:
- data source filtering:
- AI optional summary:
- auth regression:
- ingestion regression:
- unresolved issue:
```

