# V3 Phase 3.3 Spec: Cloud Closeout

## 1. Goal

Close out Phase 3.3 cloud teacher question guidance display with runtime validation, status documentation, and a scoped git commit.

## 2. Closeout Scope

Expected Phase 3.3 cloud files:

- `cloud_backend/postgres_repository.py`
- `cloud_backend/dashboard_v11.py`
- `cloud_backend/teacher_pages.py`
- `samples/phase3_3_question_guidance_result.json`
- `scripts/validate_phase3_3_cloud_question_guidance.sh`
- `docs/specs/v3-phase3.3-cloud-question-guidance-spec.md`
- `docs/tasks/v3-phase3.3-cloud-question-guidance-tasks.md`
- `docs/prompts/v3-phase3.3-cloud-question-guidance-cli-prompt.md`
- `docs/runbooks/v3-phase3.3-cloud-question-guidance-validation-runbook.md`
- `docs/project-status/v3-phase3.3-cloud-question-guidance.md`
- `docs/specs/v3-phase3.3-cloud-closeout-spec.md`
- `docs/tasks/v3-phase3.3-cloud-closeout-tasks.md`
- `docs/prompts/v3-phase3.3-cloud-closeout-cli-prompt.md`

If additional Phase 3.3 cloud files exist, explain why they belong before staging.

## 3. Required Validation

Static validation:

```bash
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py cloud_backend/ui_style.py
```

Runtime validation:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_3_cloud_question_guidance.sh
```

The user has already reported successful runtime markers:

```text
PHASE33_CLOUD_UPLOAD_OK=true
PHASE33_RAW_QUESTION_FIELDS_PRESERVED=true
PHASE33_TEACHER_LOGIN_OK=true
PHASE33_DETAIL_QUESTION_FIELDS_PRESENT=true
PHASE33_DASHBOARD_OK=true
PHASE33_REPORTS_OK=true
PHASE33_REGRESSION_OK=true
```

If these markers are not already written in the status document, update it. If rerunning validation is possible, rerun and record the fresh output.

## 4. Status Document Requirements

Update `docs/project-status/v3-phase3.3-cloud-question-guidance.md` with:

- Upload API unchanged.
- No new mandatory API.
- No DB migration.
- raw JSON preserves `teacher_question_events` and `question_guidance_summary`.
- detail API exposes Phase 3.3 fields.
- `/dashboard` and `/teacher/reports` display Phase 3.3 guidance data.
- Actual runtime markers listed above.

## 5. Git Closeout Rules

- Do not use `git add .`.
- Do not stage historical dirty files.
- Do not revert unrelated changes.
- Stage only Phase 3.3 cloud files.
- If sample files are ignored but required for validation, use `git add -f` for those specific files only.

Suggested commit message:

```text
feat(cloud): display phase 3.3 question guidance
```

## 6. Acceptance Criteria

- Runtime validation markers are true.
- Status document no longer says runtime pending.
- API route and DB boundaries remain unchanged.
- Commit contains only Phase 3.3 cloud scope.
