# V2 Phase 2.7 Tasks: Admin Console and Platform Overview

## Principles

- Build admin presentation views only.
- Do not implement CRUD management.
- Do not implement formal permissions.
- Do not add core database tables.
- Keep pages visually complete and competition-ready.
- Reuse `/dashboard?result_id=xxx` for single-session detail.
- Runtime validation must run on Linux server because the workspace is SSHFS.

## Task 1: Baseline Review

Read:

- `docs/specs/v2-phase2.7-admin-console-spec.md`
- `docs/project-status/v2-phase2.6-teacher-home.md`
- `cloud_backend/main.py`
- `cloud_backend/auth.py`
- `cloud_backend/postgres_repository.py`
- `cloud_backend/teacher_pages.py`
- `cloud_backend/dashboard_v11.py`

Confirm:

- Phase 2.6 teacher routes work.
- Phase 2.5 dashboard deep link works.
- repository can query `analysis_results`, `sessions`, `classrooms`, and `users`.

## Task 2: Add Admin Repository Aggregation Methods

Owner file:

- `cloud_backend/postgres_repository.py`

Add methods:

```text
get_admin_overview()
get_admin_classrooms(q=None, teacher_id=None, limit=50, offset=0)
get_admin_teachers(q=None, limit=50, offset=0)
get_admin_results(classroom_id=None, teacher_id=None, status=None, days=30, limit=20, offset=0)
```

Requirements:

- use existing tables only
- tolerate missing teacher mappings
- derive `has_video` and `video_status` through existing Phase 2.5 mapping
- return empty-safe structures

Validation:

- methods work with empty or partial data
- no core table is added

## Task 3: Add Admin APIs

Owner file:

- `cloud_backend/auth.py` or a new router module if cleaner

Add:

```text
GET /api/admin/overview
GET /api/admin/classrooms
GET /api/admin/teachers
GET /api/admin/results
```

Behavior:

- no strict auth in Phase 2.7
- use demo admin context when no token exists
- invalid status returns `400`
- limit max is `100`
- days supports `7`, `30`, `all`, or consistent clamping

Validation:

- each API returns required keys
- bad status returns `400`

## Task 4: Add Admin Page Routes

Owner files:

- `cloud_backend/main.py`
- new `cloud_backend/admin_pages.py` recommended

Add:

```text
GET /admin
GET /admin/classrooms
GET /admin/teachers
GET /admin/results
```

Pages should use server-rendered HTML with embedded JavaScript.

Validation:

- each route returns `200`
- each page includes Admin Console navigation markers

## Task 5: Build Shared Admin Page Shell

Owner file:

- `cloud_backend/admin_pages.py`

Create a shared layout style for:

- platform name
- Admin Console marker
- navigation links
- Teacher Console link
- data update label
- common card/table/badge styles

Validation:

- all admin pages look consistent
- all admin pages include a `/teacher` link

## Task 6: Build `/admin` Platform Overview

Owner file:

- `cloud_backend/admin_pages.py`

Data:

- fetch `/api/admin/overview`

Required modules:

- platform status hero
- pipeline status
- core metric cards
- data ingestion status
- status distribution
- latest results
- quick links

Interactions:

- latest result -> `/dashboard?result_id=xxx`
- status distribution -> `/admin/results?status=...`
- quick links -> admin pages

Validation:

- page is visually complete and not table-only

## Task 7: Build `/admin/classrooms`

Owner file:

- `cloud_backend/admin_pages.py`

Data:

- fetch `/api/admin/classrooms`

Required modules:

- overview metric cards
- search/filter controls
- classroom list
- classroom ranking or active-classroom summary
- view results action

Interactions:

- search/filter updates query and list
- view results -> `/admin/results?classroom_id=xxx`

Validation:

- page contains overview/list/supporting module

## Task 8: Build `/admin/teachers`

Owner file:

- `cloud_backend/admin_pages.py`

Data:

- fetch `/api/admin/teachers`

Required modules:

- overview metric cards
- search controls
- teacher list
- teacher classroom count ranking
- teacher average feedback ranking
- view results action

Interactions:

- search updates query and list
- view results -> `/admin/results?teacher_id=xxx`

Validation:

- page contains overview/list/supporting module

## Task 9: Build `/admin/results`

Owner file:

- `cloud_backend/admin_pages.py`

Data:

- fetch `/api/admin/classrooms`
- fetch `/api/admin/teachers`
- fetch `/api/admin/results?...filters`

Required modules:

- result overview cards
- status distribution
- filters
- all-platform result list
- high-score / low-attention tips
- view analysis action

Interactions:

- filters update URL and records
- view analysis -> `/dashboard?result_id=xxx`

Validation:

- page contains overview/filter/list/supporting module

## Task 10: Add Phase 2.7 Validation Script

Owner file:

- `scripts/validate_phase2_7_admin_console.sh`

Validate:

- `/admin`
- `/admin/classrooms`
- `/admin/teachers`
- `/admin/results`
- `/api/admin/overview`
- `/api/admin/classrooms`
- `/api/admin/teachers`
- `/api/admin/results`
- `/api/admin/results?status=bad_status`
- `/teacher`
- `/teacher/results`
- `/dashboard?result_id=...`
- Phase 2.5 detail API
- Phase 1/2 latest/recent APIs

Emit clear true/false markers.

## Task 11: Regression Validation

Confirm:

- Phase 2.6 teacher pages still work
- Phase 2.5 dashboard still works
- Phase 2.5 charts still render
- Phase 1/2 latest/recent APIs still work
- raw JSON remains unchanged

## Task 12: Update Documentation

Update:

- `docs/project-status/v2-phase2.7-admin-console.md`
- `docs/runbooks/v2-phase2.7-validation-runbook.md`

Final report must include:

- modified files
- admin API summary
- admin page summary
- page fullness notes
- static validation result
- server validation commands
- runtime validation result or pending instructions
- regression status
- known risks
