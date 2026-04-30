# V2 Phase 2.8.1 Tasks: Cloud Scripted Verification Support

## 1. Read Documents

Read:

- `docs/specs/v2-phase2.8.1-cloud-scripted-verification-spec.md`
- `docs/runbooks/v2-phase2.8.1-three-side-scripted-validation-runbook.md`
- `docs/project-status/v2-phase2.8.1-scripted-handoff-status.md`
- existing Phase 2.8 ingestion status docs

## 2. Check Ingestion Metadata Handling

Verify `/api/admin/ingestion` can tolerate:

- `video.standardized_video_path`
- `video.browser_compatible`
- `video.transcode_status`
- `video.transcode_error`

Add display fields only if the current page/API omits useful Phase 2.8.1 information.

## 3. Keep Scope Small

Do not add:

- database tables
- video upload endpoint
- video asset model
- auth system
- heartbeat

## 4. Validation Script

Confirm or lightly update:

```text
scripts/validate_phase2_8_ingestion_status.sh
```

It should validate:

- `/api/admin/ingestion`
- `/admin/ingestion`
- `/dashboard?result_id=<result_id>`
- Phase 2.5/2.6/2.7 regression

## 5. Status Update

Update:

```text
docs/project-status/v2-phase2.8.1-scripted-handoff-status.md
```

Record modified files, validation command, and remaining risks.

## 6. Acceptance Criteria

Pass when:

- uploaded Phase 2.8.1 result appears in ingestion API
- admin ingestion page opens
- dashboard for result opens
- old results still work
- no cloud scope expansion occurred

