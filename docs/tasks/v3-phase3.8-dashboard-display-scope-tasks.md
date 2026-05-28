# V3 Phase 3.8 Tasks: Dashboard Display Scope Closeout

## Task 1: Add Detail Display Scope

- Add non-breaking `display_scope` to workbench detail mapping.
- Derive source label from `source_dataset`, `capture`, and top-level payload fields.
- Derive final sample/demo sample flags from top-level, `capture`, and `video` fields.
- Preserve raw JSON unchanged.

Acceptance:

- `/api/teacher/results/phase37_full_classroom_sav_20200908_17` exposes either `display_scope.source_label` or raw `source_dataset=SAV`.
- Detail API exposes `is_pi_capture=false`, `is_own_capture=false`, and `is_final_dashboard_sample=true`.

## Task 2: Add Dashboard Scope Notes

- Add a source note for the final SAV full-classroom sample.
- Add a smoke test note for the one-minute demo clip.
- Add an unsupported metrics note for missing audio/transcript/question evidence.
- Keep existing metric modules visible.
- Do not redesign or reorder the dashboard.

Acceptance:

- Dashboard HTML contains the SAV external public video note.
- Dashboard includes data-quality notes near evidence, question guidance, confidence, and stage display.
- Dashboard no longer uses a misleading fixed “Raspberry Pi capture” pipeline label for external samples.

## Task 3: Add Validation Script

- Add `scripts/validate_phase3_8_dashboard_display_scope.sh`.
- Validate health, teacher login, final detail API, dashboard HTML, demo scope support, unsupported metric notes, and SAV-50 boundary.

Required final marker:

```text
PHASE38_DASHBOARD_DISPLAY_SCOPE_OK=true
```

## Task 4: Document Closeout

- Add spec, tasks, runbook, status, and prompt docs.
- Record static/runtime validation status.
- State that the final dashboard sample is the full-classroom Phase 3.7 sample, not the one-minute demo clip.
