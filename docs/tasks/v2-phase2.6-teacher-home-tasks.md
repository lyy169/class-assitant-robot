# V2 Phase 2.6 Tasks: Teacher Home and Classroom Records

## Principles

- Build the teacher entry layer on top of Phase 2.5.
- Do not rewrite `/dashboard`; only add `result_id` deep-link support if missing.
- Do not add admin pages.
- Do not add full login role routing.
- Do not add core database tables.
- Do not modify raw JSON.
- Keep runtime validation server-side because the workspace is SSHFS.

## Task 1: Baseline Review

Read:

- `docs/specs/v2-phase2.6-teacher-home-spec.md`
- `docs/project-status/v2-phase2.5-teacher-analysis-center.md`
- `cloud_backend/main.py`
- `cloud_backend/auth.py`
- `cloud_backend/postgres_repository.py`
- `cloud_backend/dashboard_v11.py`

Confirm:

- Phase 2.5 dashboard still works.
- existing teacher APIs are available.
- PostgreSQL repository has access to `analysis_results`, `sessions`, `classrooms`, and `users` concepts.

## Task 2: Add Teacher Overview Repository Method

Owner file:

- `cloud_backend/postgres_repository.py`

Add a method similar to:

```text
get_teacher_overview(user_id: Optional[int] = None) -> dict
```

It should return:

- teacher
- metrics
- latest_results
- classroom_summaries
- todo_items

Use existing tables only.

If no auth user exists, return demo/default teacher context and aggregate visible/demo data.

Validation:

- method handles empty database safely.
- method handles missing classroom mappings safely.

## Task 3: Add Teacher Results Repository Method

Owner file:

- `cloud_backend/postgres_repository.py`

Add a method similar to:

```text
get_teacher_results(
    user_id: Optional[int] = None,
    classroom_id: Optional[str] = None,
    status: Optional[str] = None,
    days: Optional[int] = 30,
    limit: int = 20,
    offset: int = 0,
) -> dict
```

Return:

- filters
- items
- total

Each item must include:

- result_id
- analysis_id
- classroom_id
- classroom_name
- lesson_title
- recorded_at
- generated_at
- created_at
- duration_seconds
- feedback_score
- attention_score
- response_score
- status
- has_video
- video_status
- detail_url
- updated_at

Validation:

- status filter works.
- classroom filter works.
- days filter works.
- limit/offset work.
- no unrelated fallback for filtered PostgreSQL queries.

## Task 4: Add Teacher APIs

Owner file:

- `cloud_backend/auth.py`

Add:

```text
GET /api/teacher/overview
GET /api/teacher/results
```

Authentication behavior:

- If authorization header exists and is valid, use current user.
- If no authorization header exists, use demo/default teacher context.
- Do not force login in Phase 2.6.

Validation:

- overview returns required keys.
- results returns `items`, `filters`, `total`.
- invalid status returns `400`.
- invalid days/limit are clamped or rejected consistently.

## Task 5: Add Teacher Page Routes

Owner file:

- `cloud_backend/main.py`
- optional helper module if HTML becomes too large

Add:

```text
GET /teacher
GET /teacher/results
```

Pages should be server-rendered HTML with embedded JavaScript, consistent with Phase 2.5.

Validation:

- `/teacher` returns `200`.
- `/teacher/results` returns `200`.
- both include Teacher Console navigation markers.

## Task 6: Build `/teacher` Teacher Home UI

Owner file:

- route/template/helper chosen in Task 5

Must render:

- top navigation
- welcome/status overview
- metric cards
- recent classroom analyses
- todo items/teaching tips
- classroom overview cards
- button/link to `/teacher/results`

Data:

- fetch `/api/teacher/overview`

Validation:

- empty data renders friendly state.
- latest result links to `/dashboard?result_id=xxx`.
- classroom card links to `/teacher/results?classroom_id=xxx`.
- todo item links to its target URL.

## Task 7: Build `/teacher/results` Classroom Records UI

Owner file:

- route/template/helper chosen in Task 5

Must render:

- top navigation
- classroom/status/days filters
- records table or cards
- status badges
- video availability indicator
- empty state
- view analysis action

Data:

- fetch `/api/teacher/classrooms`
- fetch `/api/teacher/results?...`

Validation:

- filters update URL query.
- filters refresh records.
- view analysis opens `/dashboard?result_id=xxx`.

## Task 8: Support `/dashboard?result_id=xxx`

Owner file:

- `cloud_backend/dashboard_v11.py`
- `cloud_backend/main.py` if parameters need forwarding

Ensure:

- dashboard reads `result_id` from query string.
- when present, it loads that result first.
- if invalid, it shows a visible error and keeps recent list available.
- default behavior remains unchanged when no `result_id` is provided.

Validation:

- `/dashboard?result_id=cls_20260417_101_001` loads that result first.
- `/dashboard?result_id=not_existing` does not crash.

## Task 9: Add Phase 2.6 Validation Script

Owner file:

- `scripts/validate_phase2_6_teacher_home.sh`

Validate:

- `GET /teacher`
- `GET /teacher/results`
- `GET /api/teacher/overview`
- `GET /api/teacher/results`
- `GET /api/teacher/results?classroom_id=...`
- `GET /api/teacher/results?status=raw`
- `GET /api/teacher/results?days=7`
- invalid status returns `400`
- `GET /dashboard?result_id=...`
- Phase 2.5 detail API still works

Script should emit clear true/false markers.

## Task 10: Regression Validation

Confirm:

- Phase 2.5 dashboard still returns `200`
- four chart markers still exist
- status update still works
- legacy latest/recent APIs still work
- upload regression remains optional because it writes data

## Task 11: Update Documentation

Update:

- `docs/project-status/v2-phase2.6-teacher-home.md`
- `docs/runbooks/v2-phase2.6-validation-runbook.md`

Final report must include:

- modified files
- API implementation summary
- page implementation summary
- static validation result
- server validation commands
- runtime validation result or pending instructions
- Phase 2.5 regression result
- known risks
