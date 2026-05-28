# V3 Phase 3.8 CLI Prompt Summary

Implement cloud dashboard display-scope closeout for competition presentation.

Final sample:

```text
phase37_full_classroom_sav_20200908_17
```

Scope:

- Add non-breaking `display_scope` to teacher detail mapping if useful.
- Show dashboard source note for SAV external public classroom video.
- Mark the one-minute playback demo as smoke test, not final sample.
- Mark unsupported audio/transcript/question metrics as structural display only.
- Do not rewrite dashboard.
- Do not modify upload APIs.
- Do not add database migration.
- Do not modify Raspberry Pi/local analyzer algorithms.
- Do not commit git changes.

Validation:

- Add `scripts/validate_phase3_8_dashboard_display_scope.sh`.
- Static check with `py_compile` and `bash -n`.
- Runtime check after manual service restart.
