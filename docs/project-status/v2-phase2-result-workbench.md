# V2 Phase 2 Result Workbench

## 1. Current Branch

```text
chore/cloud-src-bootstrap
```

## 2. Goal

Build the V2 Phase 2 teacher result workbench on top of the verified Phase 1 baseline.

Phase 1 baseline preserved:

- `POST /api/interaction-results`
- raw JSON persistence
- PostgreSQL indexing
- SQLite/file fallback code
- existing recent/latest/dashboard routes

## 3. Modified Files

- `cloud_backend/repository_interface.py`
- `cloud_backend/storage.py`
- `cloud_backend/postgres_repository.py`
- `cloud_backend/auth.py`
- `cloud_backend/main.py`
- `cloud_backend/dashboard_v11.py`
- `scripts/setup_postgres_schema.sh`
- `scripts/validate_phase2_result_workbench.sh`
- `docs/project-status/v2-phase2-result-workbench.md`

## 4. Read-Only Discovery

- Backend entry file: `cloud_backend/main.py`
- Teacher API file: `cloud_backend/auth.py`
- Dashboard file: `cloud_backend/dashboard_v11.py`
- PostgreSQL repository/query logic: `cloud_backend/postgres_repository.py`
- PostgreSQL schema setup script: `scripts/setup_postgres_schema.sh`
- Phase 1 final status document: `docs/project-status/v2-phase1-iteration-01.md`
- Phase 2 spec document: `docs/specs/v2-phase2-result-workbench-spec.md`
- Phase 2 task document: `docs/tasks/v2-phase2-result-workbench-tasks.md`

## 5. Database Changes

`analysis_results` Phase 2 compatible fields:

- `classroom_name TEXT`
- `lesson_title TEXT`
- `status TEXT NOT NULL DEFAULT 'raw'`
- `updated_at TIMESTAMPTZ`

Compatibility behavior:

- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` is used.
- `analysis_results.classroom_id` is relaxed with `DROP NOT NULL` so missing classroom values do not break old/future records.
- existing rows are backfilled with `status='raw'`.
- `updated_at` is backfilled from `created_at` or `now()`.
- PostgreSQL repository also lazily ensures these fields before Phase 2 reads/writes.

Operator command to apply schema explicitly:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
export CLOUD_DATABASE_URL='postgresql://classroom_user:classroom_pass@127.0.0.1:5432/classroom_cloud'
bash scripts/setup_postgres_schema.sh
```

## 6. API Changes

Existing API enhanced:

- `GET /api/recent-interaction-results?limit=5&classroom_id=classroom_101&status=raw`

New Phase 2 APIs:

- `GET /api/teacher/results/recent`
- `GET /api/teacher/results/recent?limit=5`
- `GET /api/teacher/results/recent?classroom_id=classroom_101`
- `GET /api/teacher/results/recent?status=raw`
- `GET /api/teacher/classrooms`
- `GET /api/teacher/results/{result_id}`
- `PATCH /api/teacher/results/{result_id}/status`

Status values:

- `raw`
- `reviewed`
- `archived`

Error behavior:

- invalid status returns `400`
- missing result returns `404`
- result detail does not fallback to sample data

## 7. Dashboard Changes

`/dashboard` now includes:

- classroom filter
- status filter
- limit selector: `10`, `20`, `50`
- refresh button
- result list with status and action buttons
- detail panel loaded from `GET /api/teacher/results/{result_id}`
- reviewed/archived buttons using `PATCH /api/teacher/results/{result_id}/status`
- empty-state row when filters return no records
- visible error message when detail/status API calls fail
- Vue + ECharts visual analytics section
- score trend line chart
- status distribution pie chart
- classroom statistics bar chart
- event distribution bar chart
- classroom filter is now a dynamic dropdown populated from `/api/teacher/classrooms`

The existing V1.1 summary, question event, stage, zone, and timeline sections remain in place.

Implementation note:

- The current repository has no standalone Vue/Vite frontend project.
- Vue and ECharts are loaded from CDN inside `cloud_backend/dashboard_v11.py` to avoid introducing a build pipeline or rewriting the existing dashboard.
- Chart data is loaded from the existing Phase 2 APIs:
  - `/api/teacher/results/recent?limit=50`
  - `/api/teacher/classrooms`
  - `/api/teacher/results/{result_id}`
- The classroom dropdown is also populated from `/api/teacher/classrooms`.

## 8. Static Validation

Executed from SSHFS workspace:

```powershell
$env:PYTHONPYCACHEPREFIX="$env:TEMP\codex_pycache"
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py
```

Result:

- passed

## 9. Operator Curl Validation

These commands must be run on the Linux server while the cloud backend is running in PostgreSQL mode.

Start service:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Run Phase 2 validation:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
bash scripts/validate_phase2_result_workbench.sh
```

Expected key results:

- recent default returns `200`
- recent `limit=5` returns `200`
- classroom filter returns `200`
- status filter returns `200`
- classrooms returns `200`
- detail for `cls_20260417_101_001` returns `200`
- status update to `reviewed` returns `200`
- invalid status returns `400`
- missing result returns `404`
- dashboard returns `200`
- dashboard HTML contains the Vue + ECharts section and all four chart markers

Actual operator results captured on 2026-04-28:

```text
GET /api/teacher/results/recent?limit=5
HTTP/1.1 200 OK
items includes cls_20260417_101_001 with status=raw
```

```text
GET /api/teacher/results/cls_20260417_101_001
HTTP/1.1 200 OK
result includes summary, events, raw_path, status=raw
```

```text
PATCH /api/teacher/results/cls_20260417_101_001/status
body: {"status":"reviewed"}
HTTP/1.1 200 OK
result.status=reviewed
updated_at=2026-04-28T11:20:03.213315+08:00
```

```text
GET /api/teacher/results/recent?status=reviewed
HTTP/1.1 200 OK
fallback_to_sample=false
items includes cls_20260417_101_001 with status=reviewed
```

```text
PATCH /api/teacher/results/cls_20260417_101_001/status
body: {"status":"bad_status"}
HTTP/1.1 400 Bad Request
message=status must be raw, reviewed, or archived
```

Earlier route log also confirmed:

```text
GET /api/teacher/results/recent HTTP/1.1 200 OK
GET /api/teacher/results/recent?limit=5 HTTP/1.1 200 OK
GET /api/teacher/results/recent?classroom_id=classroom_101 HTTP/1.1 200 OK
GET /api/teacher/results/recent?status=raw HTTP/1.1 200 OK
GET /api/teacher/classrooms HTTP/1.1 200 OK
GET /dashboard?classroom_id=classroom_101&status=reviewed&limit=10 HTTP/1.1 200 OK
```

Chart marker validation was added to `scripts/validate_phase2_result_workbench.sh`:

```text
DASHBOARD_VUE_ECHARTS_MARKER=true
DASHBOARD_SCORE_TREND_CHART=true
DASHBOARD_STATUS_DISTRIBUTION_CHART=true
DASHBOARD_CLASSROOM_STAT_CHART=true
DASHBOARD_EVENT_DISTRIBUTION_CHART=true
```

## 10. Phase 1 Regression Commands

Run on the Linux server:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
bash scripts/upload_real_result.sh
bash scripts/validate_postgres.sh
curl -i "http://127.0.0.1:8011/api/recent-interaction-results?limit=5&classroom_id=classroom_101"
curl -i "http://127.0.0.1:8011/dashboard?classroom_id=classroom_101&limit=5"
```

Expected key results:

- upload returns `HTTP_STATUS=200`
- raw JSON path is returned in `saved_path`
- PostgreSQL `analysis_results` contains the uploaded `analysis_id`
- recent returns `fallback_to_sample=false`
- dashboard displays the real uploaded result

## 11. Dashboard Browser Validation

Operator should open:

```text
http://<server-ip>:8011/dashboard?classroom_id=classroom_101&limit=10
```

Expected:

- page loads with HTTP `200`
- classroom filter is visible
- classroom filter is a dropdown populated from real classroom aggregate data
- status filter is visible
- limit selector is visible
- Visual Analytics section is visible
- Score Trend line chart is visible
- Status Distribution pie chart is visible
- Classroom Statistics bar chart is visible
- Event Distribution bar chart is visible
- result list shows `cls_20260417_101_001`
- detail button loads detail into the page
- reviewed button changes status to `reviewed`
- archived button changes status to `archived`
- refreshing preserves the updated status from PostgreSQL

Screenshot note:

- Operator should capture the dashboard after opening:

```text
http://<server-ip>:8011/dashboard?classroom_id=classroom_101&status=reviewed&limit=10
```

- Expected screenshot content: filters, four ECharts panels, result list, detail panel, and reviewed/archived buttons.

## 12. Known Issues

- Runtime curl/browser validation must be executed by the operator on the Linux server because this workspace is accessed through SSHFS.
- The Phase 2 spec/task files are present but display mojibake in this SSHFS view; implementation followed the identifiable route, schema, dashboard, and validation requirements.
- Status update buttons currently call unauthenticated Phase 2 workbench APIs to match the provided curl examples and avoid adding a complex permission system in this phase.
- During operator validation, `GET /api/teacher/results/recent?status=reviewed` initially fell back to raw file results when PostgreSQL had no reviewed row. This was corrected so filtered PostgreSQL queries return an empty list instead of file fallback when `status` or `classroom_id` filters are present and no database row matches.
- Operator PATCH validation initially returned `422` because the shell command split `Content-Type: application/json` across lines. Validation succeeded with the short single-line form: `curl -i -XPATCH ... -H 'Content-Type:application/json' -d @/tmp/status-reviewed.json`.
- Vue and ECharts are loaded through public CDNs. If the operator browser cannot access the CDN URLs, the dashboard still serves but chart rendering will fail with a visible chart loading error. A future deployment hardening pass should vendor these static assets locally if offline operation is required.

## 13. Next Suggestions

- Run `scripts/validate_phase2_result_workbench.sh` on the server and paste the output into this document.
- Add systemd/runtime hardening after Phase 2 validation, as a separate deployment iteration.
- Rotate `CLOUD_JWT_SECRET` and admin/teacher validation passwords before any production exposure.
