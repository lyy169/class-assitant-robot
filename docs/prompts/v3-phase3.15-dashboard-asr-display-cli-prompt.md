# V3 Phase 3.15 CLI Prompt Summary

Implement cloud-only dashboard display for Phase 3.14 ASR enhanced fields.

Target:

```text
phase314_asr_full_classroom_sav_20200908_17
```

Scope:

- Add additive `asr_display` to teacher detail mapping.
- Show ASR transcript summary.
- Show teacher question candidate stats.
- Show visual response alignment stats.
- Show typical question candidate events.
- Show boundary note: no speaker diarization, therefore candidate events only and no precise teacher identity judgment.

Do not:

- Modify local analyzer code.
- Modify Raspberry Pi code.
- Modify database schema.
- Modify upload endpoint storage logic.
- Rewrite dashboard.
- Commit git changes.

Validation:

- Add `scripts/validate_phase3_15_dashboard_asr_display.sh`.
- Run static checks.
- Run runtime validation only after manual service restart.
