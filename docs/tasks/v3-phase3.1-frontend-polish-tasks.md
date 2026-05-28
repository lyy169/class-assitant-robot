# V3 Phase 3.1 Tasks: Frontend Dashboard Polish

## Task 0: Documentation

Create and maintain:

- `docs/specs/v3-phase3.1-frontend-polish-spec.md`
- `docs/tasks/v3-phase3.1-frontend-polish-tasks.md`
- `docs/runbooks/v3-phase3.1-validation-runbook.md`
- `docs/project-status/v3-phase3.1-frontend-polish.md`

## Task 1: Shared Visual Tokens

Add a lightweight shared style layer for:

- color tokens
- page shell
- cards
- metrics
- filters
- buttons
- badges
- empty states
- chart containers

## Task 2: Login Page

Polish `/login` as the Chinese product entry.

Must keep:

- username/password login
- teacher demo login
- admin demo login
- real auth API usage

## Task 3: Teacher Shell

Polish teacher navigation:

- 教学首页
- 课堂记录
- 课堂分析
- 趋势洞察
- 报告中心

Keep user identity and logout.

## Task 4: Teacher Home

Make `/teacher` a teaching feedback workbench:

- key metrics
- recent analyses
- action reminders
- classroom overview
- quick report/trend entry

## Task 5: Dashboard

Make `/dashboard` a single-classroom evidence dashboard:

- classroom info and score band
- video evidence state
- teaching feedback summary
- four charts
- key events
- debug/raw data collapsed

## Task 6: Trends And Reports

Polish:

- `/teacher/trends`
- `/teacher/reports`
- `/teacher/reports?result_id=...`

Keep Phase 3.0 APIs unchanged.

## Task 7: Admin Pages

Polish admin shell and key pages:

- `/admin`
- `/admin/trends`
- `/admin/ingestion`

Keep existing admin APIs unchanged.

## Task 8: Validation

Add:

```text
scripts/validate_phase3_1_frontend_polish.sh
```

Validate:

- login page
- teacher/admin login
- teacher pages
- admin pages
- teacher cannot access admin
- Phase 3.0 APIs still work
- AI unconfigured does not block reports

## Task 9: Git Closeout

Before commit:

- run `git status --short`
- stage only Phase 3.1 files explicitly
- inspect `git diff --cached --name-only`
- never run `git add .`
