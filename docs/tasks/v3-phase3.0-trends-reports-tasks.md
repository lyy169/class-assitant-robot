# V3 Phase 3.0 Tasks: Teaching Trends And Classroom Report Center

## Principles

- Do not use `git add .`.
- Do not mix historical dirty files into Phase 3.0 commits.
- Preserve Phase 2.9 auth and permission boundary.
- Default trend/report data source is `real`.
- Demo data must be explicitly marked and filterable.
- Rule report is mandatory; AI summary is optional.
- Do not modify Raspberry Pi or local analyzer projects.

## Task 1: Read SDD And Git Boundary

Read:

- `docs/specs/v3-phase3.0-trends-reports-spec.md`
- `docs/tasks/v3-phase3.0-trends-reports-tasks.md`
- `docs/runbooks/v3-phase3.0-validation-runbook.md`
- `docs/project-status/v3-phase3.0-trends-reports.md`
- `docs/project-status/git-working-tree-boundary-after-phase2.8.1.md`

## Task 2: Repository Aggregation

Update:

```text
cloud_backend/postgres_repository.py
cloud_backend/repository_interface.py
```

Add aggregation methods for:

- teacher trends
- teacher report list
- teacher report detail
- admin trends

Use existing `analysis_results` and `payload_json`.

Do not add trend/report tables.

## Task 3: Dataset Source Filter

Implement:

```text
data_source=real|demo|all
```

Default:

```text
real
```

Rules:

- missing `payload_json.dataset.source` -> real
- `demo` -> demo
- unknown values -> unknown, excluded from real

## Task 4: Rule Report Generator

Add a small helper if useful, for example:

```text
cloud_backend/reporting.py
```

It should generate:

- highlights
- risks
- recommendations
- risk_level

No AI required for this task.

## Task 5: Optional AI Summary Helper

Add optional AI helper if useful, for example:

```text
cloud_backend/ai_report.py
```

Requirements:

- controlled by environment variables
- supports not_configured status
- failures do not break report page
- accepts structured summary only
- does not cache output

Use existing project configuration style.

## Task 6: Teacher APIs

Add:

```text
GET /api/teacher/trends
GET /api/teacher/reports
GET /api/teacher/reports/detail
POST /api/teacher/reports/ai-summary
```

Rules:

- require Phase 2.9 auth
- teacher sees bound classrooms only
- admin can access all if using teacher APIs
- default `data_source=real`

## Task 7: Admin API

Add:

```text
GET /api/admin/trends
```

Rules:

- admin only
- supports `data_source`
- default `real`

## Task 8: Teacher Pages

Update:

```text
cloud_backend/teacher_pages.py
```

Add:

```text
/teacher/trends
/teacher/reports
```

Required:

- use existing user bar/logout
- preserve teacher home/results
- add navigation links
- use ECharts for trend visuals
- show data source warning for demo/all
- show insufficient real-data empty state

## Task 9: Admin Page

Update:

```text
cloud_backend/admin_pages.py
```

Add:

```text
/admin/trends
```

Required:

- use existing admin navigation
- use existing user bar/logout
- show global trend overview
- show classroom ranking
- show teacher activity ranking
- show risk lesson list

## Task 10: Demo Seed Script

Add:

```text
scripts/seed_phase3_demo_trend_data.sh
```

Support:

```text
--seed
--cleanup
```

Rules:

- upload through `POST /api/interaction-results`
- generate `demo_phase3_*` ids
- set `dataset.source=demo`
- cleanup only demo records

## Task 11: Validation Script

Add:

```text
scripts/validate_phase3_trends_reports.sh
```

Validate:

- teacher login
- `/teacher/trends`
- `/api/teacher/trends`
- `/teacher/reports`
- `/api/teacher/reports`
- `/api/teacher/reports/detail`
- admin login
- `/admin/trends`
- `/api/admin/trends`
- default `data_source=real`
- demo data seed/filter if available
- AI not configured does not break report detail
- Phase 2.9 auth regression
- Phase 2.8 ingestion regression

## Task 12: Project Status

Update:

```text
docs/project-status/v3-phase3.0-trends-reports.md
```

Record:

- modified files
- APIs
- pages
- data source filtering
- demo seed result
- AI summary status
- validation result
- residual risks

## Task 13: Regression

Confirm:

- `/login`
- `/teacher`
- `/teacher/results`
- `/admin`
- `/admin/ingestion`
- `/dashboard?result_id=...`
- `POST /api/interaction-results`

