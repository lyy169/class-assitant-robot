# V3 Phase 3.15b Dashboard ASR Consistency Status

## Status

Prepared cloud-side ASR consistency hotfix. Runtime validation should be run after the operator manually restarts or refreshes the cloud backend service.

Target sample:

```text
analysis_id=phase314_asr_full_classroom_sav_20200908_17
```

## Scope

This round only adjusts cloud display mapping and dashboard/admin/teacher wording. It does not modify raw JSON, upload APIs, database schema, local analyzer code, Raspberry Pi code, or dashboard structure.

## Fixes

- Overrides display summary for ASR-enhanced samples when transcript and question candidates are present.
- Prevents legacy "no clear question event" and "question transcript unavailable" wording from surfacing on the target dashboard.
- Updates SAV display scope to state that classroom transcript comes from local offline ASR while Raspberry Pi voice trigger and speaker diarization are not connected.
- Keeps attention, heat, and stage values unchanged when they are all zero, and adds low-confidence empty-state wording instead of showing a blank-looking chart.
- Uses ASR question candidates as dashboard event distribution inputs for the target sample.
- Adds an external SAV ASR data-quality note to trends, reports, admin results, and ingestion records.
- Changes admin ingestion pipeline wording from Raspberry Pi-only capture to "采集端或外部样本".
- Fixes the `analysis_version` Vue template rendering issue.

## Current Known Data Quality

- `attention_curve` is all zero.
- `heat_curve` is all zero.
- `stage_distribution` sums to zero.
- `activity_curve` contains non-zero values.
- ASR transcript and interaction evidence are present: 764 transcript segments, 35 question candidates, 16 detected responses.

## Validation

Static validation commands:

```bash
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/dashboard_v11.py cloud_backend/admin_pages.py cloud_backend/teacher_pages.py
bash -n scripts/validate_phase3_15b_dashboard_asr_consistency.sh
```

Runtime validation command after manual service restart:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_15b_dashboard_asr_consistency.sh
```

Runtime validation is expected to confirm all `PHASE315B_*` markers.

Observed from SSHFS CLI:

- `python -B -m py_compile ...` was blocked by `[WinError 5]` while trying to access `cloud_backend/__pycache__`.
- Equivalent no-project-write Python `compile()` syntax check passed for `postgres_repository.py`, `dashboard_v11.py`, `admin_pages.py`, and `teacher_pages.py`.
- Local `bash -n` was blocked because Windows Bash/WSL/Git Bash could not start in this environment; run the exact `bash -n` command directly on the cloud server.
- Source scan confirms the removed dashboard-facing legacy strings are no longer present in cloud display source files.

## Closeout Notes

- No fake attention/heat/stage data was generated.
- No database migration was added.
- No upload endpoint was changed.
- No git commit was made.
