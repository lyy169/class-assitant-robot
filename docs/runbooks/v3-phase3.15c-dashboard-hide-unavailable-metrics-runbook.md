# V3 Phase 3.15c Dashboard Hide Unavailable Metrics Runbook

## Purpose

Validate that the ASR-enhanced SAV dashboard hides unavailable attention, student count, and stage-distribution metrics while emphasizing video, ASR transcript, question candidates, response alignment, and activity evidence.

## Preconditions

- Run from `/root/video_project_src`.
- Cloud backend code has been deployed or service has been manually restarted after the hotfix.
- Target sample exists:

```text
phase314_asr_full_classroom_sav_20200908_17
```

## Static Checks

```bash
source /root/venv/bin/activate
python -B -m py_compile cloud_backend/dashboard_v11.py cloud_backend/postgres_repository.py
bash -n scripts/validate_phase3_15c_dashboard_hide_unavailable_metrics.sh
```

## Runtime Validation

```bash
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_15c_dashboard_hide_unavailable_metrics.sh
```

Expected:

```text
PHASE315C_DASHBOARD_TRUSTED_METRICS_ONLY_OK=true
```

## Manual Browser Check

Open:

```text
http://8.148.205.228:8011/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17
```

Confirm the main dashboard shows:

- Video evidence.
- ASR transcript count.
- Question candidates.
- Response alignment and detected response count.
- Activity timeline with question markers.
- Event distribution with question candidates.
- Source and no-speaker-diarization boundary notes.

Confirm the main dashboard does not show:

- Attention score as a KPI.
- Average attention rate.
- Estimated student count.
- Teaching stage distribution chart.
- Region attention legend/bar.
- Phase 3.2 score breakdown as a primary module.

## Boundaries

Do not fabricate attention scores, student counts, or stage distributions. Do not modify database schema, upload endpoints, local analyzer code, or Raspberry Pi code.
