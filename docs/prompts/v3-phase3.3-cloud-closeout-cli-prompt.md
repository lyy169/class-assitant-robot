# CLI Prompt: V3 Phase 3.3 Cloud Closeout

You are responsible for closing out Phase 3.3 cloud teacher question guidance display.

## Working Directory

```text
/root/video_project_src
```

## Read First

```text
docs/specs/v3-phase3.3-cloud-closeout-spec.md
docs/tasks/v3-phase3.3-cloud-closeout-tasks.md
docs/project-status/v3-phase3.3-cloud-question-guidance.md
```

## Goal

Update the cloud Phase 3.3 status with actual runtime validation markers and create a scoped git commit without staging historical dirty files.

## User-Confirmed Runtime Markers

The user already validated cloud runtime successfully:

```text
PHASE33_CLOUD_UPLOAD_OK=true
PHASE33_RAW_QUESTION_FIELDS_PRESERVED=true
PHASE33_TEACHER_LOGIN_OK=true
PHASE33_DETAIL_QUESTION_FIELDS_PRESENT=true
PHASE33_DASHBOARD_OK=true
PHASE33_REPORTS_OK=true
PHASE33_REGRESSION_OK=true
```

Raw saved path:

```text
/root/video_project_src/cloud_backend/data/raw/2026-05-06/phase3_3_question_guidance_sample_001.json
```

## Boundaries

- Do not rewrite upload API.
- Do not add mandatory APIs.
- Do not migrate database.
- Do not modify local analyzer or Raspberry Pi code.
- Do not run `git add .`.
- Do not revert unrelated changes.
- Do not commit historical dirty files.

## Required Actions

1. Run `git status --short`.
2. Run static py_compile validation.
3. If service is running, rerun `scripts/validate_phase3_3_cloud_question_guidance.sh`; otherwise use the user-confirmed markers above and state that they were user-provided.
4. Update `docs/project-status/v3-phase3.3-cloud-question-guidance.md` so runtime validation is recorded as passed, not pending.
5. Stage only Phase 3.3 cloud files listed in closeout tasks.
6. Commit with:

```text
feat(cloud): display phase 3.3 question guidance
```

## Final Output

Report:

- static validation result
- runtime marker source: rerun or user-confirmed
- whether status doc was updated
- commit hash
- committed files
- remaining `git status --short`
- confirmation that no unrelated dirty files were committed
