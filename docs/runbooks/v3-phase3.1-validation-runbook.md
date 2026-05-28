# V3 Phase 3.1 Runbook: Frontend Polish Validation

## 1. Start Service

Run on the Linux cloud server:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Expected:

```text
CLOUD_DB_BACKEND=postgres
Uvicorn running on http://0.0.0.0:8011
```

## 2. Optional Demo Data

Seed Phase 3.0 demo trend/report records if the browser pages need richer demo charts:

```bash
API_BASE_URL="http://127.0.0.1:8011" CLASSROOM_ID="classroom_101" bash scripts/seed_phase3_demo_trend_data.sh --seed
```

## 3. Automated Validation

Run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" CLASSROOM_ID="classroom_101" bash scripts/validate_phase3_1_frontend_polish.sh
```

Expected markers:

```text
PHASE31_LOGIN_PAGE_OK=true
PHASE31_TEACHER_LOGIN_OK=true
PHASE31_ADMIN_LOGIN_OK=true
PHASE31_TEACHER_HOME_OK=true
PHASE31_DASHBOARD_OK=true
PHASE31_TEACHER_TRENDS_OK=true
PHASE31_TEACHER_REPORTS_OK=true
PHASE31_ADMIN_HOME_OK=true
PHASE31_ADMIN_TRENDS_OK=true
PHASE31_ADMIN_INGESTION_OK=true
PHASE31_AUTH_REGRESSION_OK=true
PHASE31_PHASE30_REGRESSION_OK=true
PHASE31_VISUAL_STRUCTURE_OK=true
PHASE31_REGRESSION_OK=true
```

## 4. Browser Validation URLs

Teacher:

```text
http://<server>:8011/login
http://<server>:8011/teacher
http://<server>:8011/dashboard
http://<server>:8011/teacher/trends
http://<server>:8011/teacher/reports
```

Admin:

```text
http://<server>:8011/admin
http://<server>:8011/admin/trends
http://<server>:8011/admin/ingestion
```

## 5. Manual Checklist

Check:

- primary UI text is Chinese
- teacher/admin share a coherent shell
- dashboard feels like a classroom evidence and feedback dashboard
- report detail reads like a teaching feedback report
- charts are readable and not collapsed
- demo/all data source shows warning
- video missing state is friendly
- AI unconfigured state does not block report
- teacher still gets 403 on admin page
