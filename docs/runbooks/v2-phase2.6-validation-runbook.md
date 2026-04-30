# V2 Phase 2.6 Validation Runbook

## Purpose

Validate Teacher Home and Classroom Records after Phase 2.6 implementation.

Run this on the Linux runtime server, not only through the SSHFS workspace.

## 1. Start Service

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Default variables:

```bash
BASE_URL="http://127.0.0.1:8011"
RESULT_ID="cls_20260417_101_001"
CLASSROOM_ID="classroom_101"
```

## 2. Static Validation

From the SSHFS workspace or server:

```bash
python -m py_compile \
  cloud_backend/repository_interface.py \
  cloud_backend/storage.py \
  cloud_backend/postgres_repository.py \
  cloud_backend/auth.py \
  cloud_backend/main.py \
  cloud_backend/dashboard_v11.py \
  cloud_backend/teacher_pages.py
```

## 2.5 One-Command Runtime Validation

Recommended server-side validation:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" \
RESULT_ID="cls_20260417_101_001" \
CLASSROOM_ID="classroom_101" \
bash scripts/validate_phase2_6_teacher_home.sh
```

The script emits `PHASE26_*` true/false markers for pages, APIs, dashboard deep-link, Phase 2.5 regression, and Phase 1/2 read regression.

The script also checks that served teacher pages do not contain residual JavaScript template escapes such as `${{...}}` or `{{...}}`, because those can pass HTTP marker validation while still breaking browser-side rendering.

## 3. Page Validation

```bash
curl -i "$BASE_URL/teacher"
curl -i "$BASE_URL/teacher/results"
curl -i "$BASE_URL/dashboard?result_id=$RESULT_ID"
```

Expected:

- all return `200`
- pages include Teacher Console navigation
- browser console has no JavaScript syntax error from `${{...}}` or `{{...}}` template remnants
- `/dashboard?result_id=$RESULT_ID` loads the requested analysis result
- `/dashboard?result_id=not_existing` should not crash; it should show an error in the dashboard detail area while keeping the recent list available

## 4. API Validation

### Overview

```bash
curl -s "$BASE_URL/api/teacher/overview" | tee /tmp/phase26-overview.json
```

Expected keys:

```text
success
teacher
metrics
latest_results
classroom_summaries
todo_items
```

### Teacher Results

```bash
curl -s "$BASE_URL/api/teacher/results?limit=20" | tee /tmp/phase26-results.json
curl -i "$BASE_URL/api/teacher/results?classroom_id=$CLASSROOM_ID&limit=20"
curl -i "$BASE_URL/api/teacher/results?status=raw&limit=20"
curl -i "$BASE_URL/api/teacher/results?days=7&limit=20"
```

Expected:

- return `200`
- response contains `items`, `filters`, `total`

Invalid status:

```bash
curl -i "$BASE_URL/api/teacher/results?status=bad_status"
```

Expected:

- `400`

## 5. Workflow Browser Validation

Open:

```text
http://<server-ip>:8011/teacher
```

Expected:

- welcome/status overview is visible
- metric cards visible
- recent classroom analyses visible
- classroom overview visible
- todo items visible
- clicking a latest result opens `/dashboard?result_id=...`
- clicking a classroom card opens `/teacher/results?classroom_id=...`

Open:

```text
http://<server-ip>:8011/teacher/results
```

Expected:

- filters visible
- record list visible
- status badges visible
- video indicator visible
- changing filters refreshes records
- view analysis opens `/dashboard?result_id=...`

## 6. Phase 2.5 Regression

```bash
curl -i "$BASE_URL/dashboard"
curl -i "$BASE_URL/api/teacher/results/$RESULT_ID"
curl -i "$BASE_URL/api/teacher/results/recent?limit=10"
```

Expected:

- all return `200`
- four Phase 2.5 chart markers remain in dashboard HTML:
- `attention-activity-chart`
- `stage-distribution-chart`
- `zone-performance-chart`
- `event-distribution-chart`
- charts render in the browser after Vue and ECharts load
- detail unified structure remains available

## 7. Phase 1/2 Regression

```bash
curl -i "$BASE_URL/api/latest-interaction-result"
curl -i "$BASE_URL/api/recent-interaction-results?limit=5"
```

Expected:

- both return `200`

Upload regression is optional because it writes data:

```bash
RUN_UPLOAD_REGRESSION=1 bash scripts/validate_phase2_5_teacher_analysis_center.sh
```

## 8. Expected Final Report

The executor should report:

- modified files
- `/teacher` validation result
- `/teacher/results` validation result
- overview API result
- teacher results API result
- dashboard deep-link result
- Phase 2.5 regression result
- Phase 1/2 regression result
- browser validation notes
- unresolved risks
