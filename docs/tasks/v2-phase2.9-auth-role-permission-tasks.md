# V2 Phase 2.9 Tasks: Auth, Role Routing, And Permission Boundary

## Principles

- Do not use `git add .`.
- Do not mix historical dirty files into Phase 2.9 commits.
- Do not protect `POST /api/interaction-results` in this phase.
- Do not modify Raspberry Pi or local analyzer projects.
- Keep implementation compatible with Phase 2.5-2.8.1.

## Task 1: Read SDD And Git Boundary

Read:

- `docs/specs/v2-phase2.9-auth-role-permission-spec.md`
- `docs/tasks/v2-phase2.9-auth-role-permission-tasks.md`
- `docs/runbooks/v2-phase2.9-auth-validation-runbook.md`
- `docs/project-status/v2-phase2.9-auth-role-permission.md`
- `docs/project-status/git-working-tree-boundary-after-phase2.8.1.md`

## Task 2: Auth Schema Script

Add:

```text
scripts/setup_phase2_9_auth_schema.sh
```

It should:

- create `users`
- create `teacher_classrooms`
- create useful indexes
- seed `admin / admin123`
- seed `teacher / teacher123`
- bind teacher to `classroom_101`

Do not create:

- `admins`
- `teachers`
- `classrooms`
- `permissions`
- `login_sessions`

## Task 3: Security Helpers

Check or update:

```text
cloud_backend/security.py
```

Required helpers:

- hash password
- verify password
- create JWT
- decode JWT

Use hashed passwords only.

## Task 4: Repository Auth Methods

Update:

```text
cloud_backend/postgres_repository.py
cloud_backend/repository_interface.py
```

Add methods as needed:

- get user by username
- get user by id
- update last login
- get teacher classroom ids
- check result visibility for user

## Task 5: Auth API

Update:

```text
cloud_backend/auth.py
```

Implement:

```text
POST /api/auth/login
GET /api/auth/me
POST /api/auth/logout
```

Use HttpOnly cookie:

```text
auth_token
```

## Task 6: Auth Dependencies

Implement reusable dependencies/helpers:

- get current user
- require login
- require admin
- require teacher
- require teacher or admin

Use them consistently in page and API routes.

## Task 7: Login And Root Pages

Update:

```text
cloud_backend/main.py
```

Add:

```text
GET /
GET /login
```

Rules:

- `/` redirects by auth state and role
- `/login` renders login page or redirects if already logged in

## Task 8: Protect Teacher Pages

Update:

```text
cloud_backend/teacher_pages.py
```

Protect:

- `/teacher`
- `/teacher/results`

Show user identity and logout action.

## Task 9: Protect Admin Pages

Update:

```text
cloud_backend/admin_pages.py
```

Protect:

- `/admin`
- `/admin/classrooms`
- `/admin/teachers`
- `/admin/results`
- `/admin/ingestion`

Admin only.

Show user identity and logout action.

## Task 10: Protect Dashboard

Update:

```text
cloud_backend/dashboard_v11.py`
```

Protect:

```text
/dashboard?result_id=...
```

Rules:

- require login
- admin can view all
- teacher can view only results in bound classrooms

## Task 11: Protect APIs

Update API routes in:

```text
cloud_backend/auth.py
```

or existing router files.

Rules:

- `/api/admin/*` admin only
- `/api/teacher/*` teacher/admin
- teacher results filtered by `teacher_classrooms`
- upload API remains open

## Task 12: Validation Script

Add:

```text
scripts/validate_phase2_9_auth.sh
```

Validate:

- `/login` returns 200
- unauthenticated `/teacher` redirects to login or returns 401/403
- unauthenticated `/admin` redirects to login or returns 401/403
- teacher login succeeds
- teacher can access `/teacher`
- teacher cannot access `/admin`
- admin login succeeds
- admin can access `/admin`
- `/api/auth/me` works
- logout clears session
- teacher sees only bound classroom data
- admin APIs reject teacher
- `POST /api/interaction-results` remains usable without login
- Phase 2.8.1 ingestion page works after admin login

## Task 13: Project Status

Update:

```text
docs/project-status/v2-phase2.9-auth-role-permission.md
```

Record:

- modified files
- database tables
- seed users
- APIs
- pages
- validation result
- upload API compatibility
- remaining risks

## Task 14: Regression

Confirm:

- Phase 2.5 dashboard after login
- Phase 2.6 teacher pages after login
- Phase 2.7 admin pages after admin login
- Phase 2.8 ingestion after admin login
- Phase 2.8.1 standardized video metadata remains visible

