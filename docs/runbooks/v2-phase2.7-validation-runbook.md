# V2 Phase 2.7 Validation Runbook

## Purpose

Validate Admin Console and Platform Overview after Phase 2.7 implementation.

Run runtime validation on the Linux server.

## 1. Start Service

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Variables:

```bash
BASE_URL="http://127.0.0.1:8011"
RESULT_ID="cls_20260417_101_001"
CLASSROOM_ID="classroom_101"
```

## 2. Static Validation

```bash
python -m py_compile \
  cloud_backend/repository_interface.py \
  cloud_backend/storage.py \
  cloud_backend/postgres_repository.py \
  cloud_backend/auth.py \
  cloud_backend/main.py \
  cloud_backend/dashboard_v11.py \
  cloud_backend/teacher_pages.py \
  cloud_backend/admin_pages.py
```

## 3. Page Validation

```bash
curl -i "$BASE_URL/admin"
curl -i "$BASE_URL/admin/classrooms"
curl -i "$BASE_URL/admin/teachers"
curl -i "$BASE_URL/admin/results"
```

Expected:

- all return `200`
- all include Admin Console navigation
- all include overview/metric/list/supporting modules

## 4. API Validation

```bash
curl -s "$BASE_URL/api/admin/overview" | tee /tmp/phase27-admin-overview.json
curl -s "$BASE_URL/api/admin/classrooms" | tee /tmp/phase27-admin-classrooms.json
curl -s "$BASE_URL/api/admin/teachers" | tee /tmp/phase27-admin-teachers.json
curl -s "$BASE_URL/api/admin/results?limit=20" | tee /tmp/phase27-admin-results.json
```

Expected required keys:

```text
overview:
  success admin metrics system_status status_distribution latest_results quick_links

classrooms:
  success overview items total

teachers:
  success overview items total

results:
  success filters overview items total
```

Invalid status:

```bash
curl -i "$BASE_URL/api/admin/results?status=bad_status"
```

Expected:

- `400`

## 5. Workflow Browser Validation

Open:

```text
http://<server-ip>:8011/admin
```

Expected:

- platform status hero visible
- metric cards visible
- data ingestion status visible
- status distribution visible
- recent classroom analyses visible
- quick links visible

Open:

```text
http://<server-ip>:8011/admin/classrooms
```

Expected:

- classroom overview visible
- classroom list visible
- ranking/active classroom summary visible
- view results opens `/admin/results?classroom_id=...`

Open:

```text
http://<server-ip>:8011/admin/teachers
```

Expected:

- teacher overview visible
- teacher list visible
- ranking modules visible
- view results opens `/admin/results?teacher_id=...`

Open:

```text
http://<server-ip>:8011/admin/results
```

Expected:

- overview cards visible
- status distribution visible
- filters visible
- all-platform results visible
- view analysis opens `/dashboard?result_id=...`

## 6. Regression Validation

Teacher pages:

```bash
curl -i "$BASE_URL/teacher"
curl -i "$BASE_URL/teacher/results"
```

Dashboard:

```bash
curl -i "$BASE_URL/dashboard?result_id=$RESULT_ID"
curl -i "$BASE_URL/api/teacher/results/$RESULT_ID"
```

Legacy read APIs:

```bash
curl -i "$BASE_URL/api/latest-interaction-result"
curl -i "$BASE_URL/api/recent-interaction-results?limit=5"
```

Expected:

- all return `200`

## 7. Optional Script

After implementation, prefer running:

```bash
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" CLASSROOM_ID="classroom_101" bash scripts/validate_phase2_7_admin_console.sh
```

Expected key markers:

- `PHASE27_ADMIN_PAGE_200=true`
- `PHASE27_ADMIN_CLASSROOMS_PAGE_200=true`
- `PHASE27_ADMIN_TEACHERS_PAGE_200=true`
- `PHASE27_ADMIN_RESULTS_PAGE_200=true`
- `PHASE27_ADMIN_OVERVIEW_API_200=true`
- `PHASE27_ADMIN_CLASSROOMS_API_200=true`
- `PHASE27_ADMIN_TEACHERS_API_200=true`
- `PHASE27_ADMIN_RESULTS_API_200=true`
- `PHASE27_ADMIN_RESULTS_INVALID_STATUS_400=true`
- `PHASE27_TEACHER_PAGE_200=true`
- `PHASE27_TEACHER_RESULTS_PAGE_200=true`
- `PHASE27_DASHBOARD_DEEPLINK_200=true`
- `PHASE27_PHASE25_DETAIL_200=true`
- `PHASE27_LEGACY_LATEST_200=true`
- `PHASE27_LEGACY_RECENT_200=true`

## 8. Expected Final Report

The executor should report:

- modified files
- admin APIs implemented
- admin pages implemented
- page fullness confirmation
- static validation result
- server validation results
- browser validation notes
- Phase 2.6 regression
- Phase 2.5 regression
- Phase 1/2 regression
- unresolved risks
