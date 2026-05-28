# V3 Phase 3.8 Dashboard Display Scope Status

## Status

Runtime validation passed.

This round:

- Added non-breaking `display_scope` fields to teacher detail mapping.
- Added dashboard source/scope/data-quality notes.
- Added validation script.
- Added SDD docs and runbook.
- Did not modify upload endpoint storage logic.
- Did not add database migration.
- Did not modify Raspberry Pi or local analyzer code.
- Service restart was handled manually by the operator before runtime validation.
- Did not commit git changes.

## Final Dashboard Sample

```text
analysis_id=phase37_full_classroom_sav_20200908_17
```

This is the Phase 3.7 full-classroom same-source video and same-source analysis JSON sample.

It is not the Phase 3.5 one-minute playback demo clip.

## Display Notes Added

- Final sample source note: SAV external public classroom video, processed locally and uploaded to cloud, not Raspberry Pi self-capture.
- Smoke test note: one-minute playback demo is not the final full-classroom sample.
- Unsupported metric note: without audio trigger/transcript evidence, voice-related stage/question metrics are structural display only.

## Static Validation

Commands requested:

```bash
python -B -m py_compile cloud_backend/dashboard_v11.py cloud_backend/postgres_repository.py
bash -n scripts/validate_phase3_8_dashboard_display_scope.sh
```

Result:

```text
bash -n scripts/validate_phase3_8_dashboard_display_scope.sh: passed
python -B -m py_compile cloud_backend/dashboard_v11.py cloud_backend/postgres_repository.py: blocked in SSHFS CLI by [WinError 5] writing cloud_backend/__pycache__
equivalent no-project-write py_compile check for dashboard_v11.py and postgres_repository.py: passed
text whitespace scan for Phase 3.8 files: passed
```

Note:

- The exact `python -B -m py_compile ...` command should be rerun directly on the cloud server if strict command parity is required.
- The PostgreSQL repository file already contains historical schema hardening SQL; this phase did not add a migration or alter upload storage logic.

## Runtime Validation

Command run by operator after manual service restart:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_8_dashboard_display_scope.sh
```

Result:

```text
PHASE38_DETAIL_API_OK=true
PHASE38_DISPLAY_SCOPE_PRESENT=true
PHASE38_FINAL_SAMPLE_NOT_PI_CAPTURE=true
PHASE38_FINAL_SAMPLE_NOT_OWN_CAPTURE=true
PHASE38_FINAL_SAMPLE_SOURCE_NOTE_PRESENT=true
PHASE38_DEMO_CLIP_SCOPE_NOTE_SUPPORTED=true
PHASE38_UNSUPPORTED_METRICS_MARKED=true
PHASE38_NO_1MIN_VIDEO_FULL_CLASS_MISLEADING=true
PHASE38_NO_SAV50_MIXED_IN_DASHBOARD=true
PHASE38_DASHBOARD_REACHABLE=true
PHASE38_DASHBOARD_DISPLAY_SCOPE_OK=true
```

## Closeout

Phase 3.8 confirms that the final dashboard sample is presented as a Phase 3.7 full-classroom same-source SAV sample, not the Phase 3.5 one-minute playback smoke test. The dashboard now explicitly states that the sample is an external public classroom video processed locally and uploaded to cloud, and it marks unsupported voice/transcript/question metrics as structural display only.
