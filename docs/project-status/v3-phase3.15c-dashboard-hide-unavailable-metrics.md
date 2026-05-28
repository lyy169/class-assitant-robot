# V3 Phase 3.15c Dashboard Hide Unavailable Metrics Status

## Status

Cloud-side display hotfix prepared. Runtime validation should be run after the operator manually restarts or refreshes the backend service.

Target sample:

```text
phase314_asr_full_classroom_sav_20200908_17
```

## Goal

For the ASR-enhanced SAV full-classroom sample, the dashboard should focus on evidence-backed classroom signals and stop presenting unavailable visual metrics as primary teaching conclusions.

## Hidden From Main Dashboard For ASR SAV Sample

- Attention KPI and attention curve.
- Average attention ratio.
- Estimated student count.
- Teaching stage distribution chart.
- Region attention bars.
- Phase 3.2 score breakdown and enhanced issue cards as primary display.
- Main-display evidence fields such as `audio_present=false`, `detected_student_count_avg=0`, and `keyframe_count=0`.

## Kept And Emphasized

- Complete classroom video.
- ASR transcript summary: 764 transcript segments.
- Teacher question candidates: 35.
- Visual response alignment: 35.
- Detected responses: 16.
- Response rate: about 45.7%.
- Classroom activity curve.
- Hand-raise events: 101.
- SAV external public classroom video source note.
- Non-Raspberry-Pi / non-self-captured boundary.
- No-speaker-diarization boundary note.

## Implementation Notes

- Added additive `display_flags` in teacher detail mapping.
- Dashboard uses `asr_trusted_metrics_only` to switch to trusted evidence mode.
- No attention, student count, or stage values are fabricated.
- No ASR rule-based teaching stage distribution is generated.
- Existing non-ASR samples keep the previous dashboard modules.

## Validation

Static validation requested:

```bash
python -B -m py_compile cloud_backend/dashboard_v11.py cloud_backend/postgres_repository.py
bash -n scripts/validate_phase3_15c_dashboard_hide_unavailable_metrics.sh
```

Runtime validation after manual service restart:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_15c_dashboard_hide_unavailable_metrics.sh
```

Expected final marker:

```text
PHASE315C_DASHBOARD_TRUSTED_METRICS_ONLY_OK=true
```

## Static Validation Notes

- Equivalent no-project-write Python `compile()` syntax check passed for `cloud_backend/dashboard_v11.py` and `cloud_backend/postgres_repository.py` from the SSHFS CLI.
- Local `bash -n` could not start because Windows Bash/WSL returned `E_ACCESSDENIED`; run the exact `bash -n` command directly on the cloud server.
- Runtime validation was not run by CLI because code changes require the operator to manually restart or refresh the backend service first.

## Boundaries

- Did not modify raw JSON.
- Did not modify local analyzer code.
- Did not modify Raspberry Pi code.
- Did not modify upload APIs.
- Did not modify database schema.
- Did not commit git changes.
