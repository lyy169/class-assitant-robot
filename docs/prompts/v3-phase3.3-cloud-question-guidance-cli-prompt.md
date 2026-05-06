# CLI Prompt: V3 Phase 3.3 Cloud Teacher Question Guidance

You are responsible for Phase 3.3 cloud-side teacher question guidance compatibility and display.

## Working Directory

```text
/root/video_project_src
```

## Read First

```text
docs/specs/v3-phase3.3-cloud-question-guidance-spec.md
docs/tasks/v3-phase3.3-cloud-question-guidance-tasks.md
```

## Goal

Consume optional `teacher_question_events` and `question_guidance_summary` fields from uploaded classroom feedback JSON and display teacher questioning as teaching-guidance evidence in dashboard/reports.

## Boundaries

- Do not rewrite upload API.
- Do not add mandatory API routes.
- Do not migrate database.
- Do not modify local analyzer or Raspberry Pi code.
- Do not assume question fields always exist.
- Do not run `git add .`.
- Do not commit unless explicitly requested.

## Required Behavior

- Preserve raw JSON question fields.
- Expose question fields in detail API when present.
- Add dashboard question guidance block.
- Add report teaching-guidance analysis.
- Degrade safely for old data.
- Label demo data when source/status indicates demo.

## Validation

Add:

```text
scripts/validate_phase3_3_cloud_question_guidance.sh
```

Expected markers:

```text
PHASE33_CLOUD_UPLOAD_OK=true
PHASE33_RAW_QUESTION_FIELDS_PRESERVED=true
PHASE33_DETAIL_QUESTION_FIELDS_PRESENT=true
PHASE33_DASHBOARD_OK=true
PHASE33_REPORTS_OK=true
```

Create/update:

```text
samples/phase3_3_question_guidance_result.json
docs/runbooks/v3-phase3.3-cloud-question-guidance-validation-runbook.md
docs/project-status/v3-phase3.3-cloud-question-guidance.md
```

## Final Output

Report:

- modified files
- API unchanged
- DB unchanged
- displayed fields
- validation commands/results
- `git status --short`
- no git commit
