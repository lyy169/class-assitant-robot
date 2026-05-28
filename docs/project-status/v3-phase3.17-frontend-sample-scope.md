# Phase 3.17 Frontend Sample Scope Status

## Goal

Phase 3.17 closes the frontend presentation scope for competition demo usage. The final dashboard sample is:

- `analysis_id=phase314_asr_full_classroom_sav_20200908_17`
- `/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17`

This is the ASR-enhanced full-classroom SAV sample. It must be labeled as an external public SAV classroom video processed by the local analyzer and uploaded to cloud. It is not Raspberry Pi capture and not self-captured data.

## Scope Rules

- `phase314_asr_full_classroom_sav_20200908_17` remains visible as the final ASR-enhanced full-classroom sample.
- `phase37_full_classroom_sav_20200908_17` is a historical phase sample and is hidden from default teacher/admin/report/trend lists.
- `phase35_local_imported_sav_full_classroom_20200908_17` is a playback smoke test and is hidden from default formal lists.
- `cls_20260430_classroom_101_d4b91cf9c0bf4e68bfcb5e12933d30ee` and `cls_20260429_classroom_101_c993e071203b44e1bef1db1586181503` are legacy test records and are hidden from default formal lists.
- `cls_20260417_101_001` / `video_20260417_001` is legacy visual-only data for this competition frontend口径 and should be hidden from default formal lists or explicitly labeled outside the default demo path.
- Demo records must be labeled as demo data when included via demo/all filters.

## Display Policy

The final ASR sample displays trusted evidence only:

- Full classroom video evidence.
- ASR transcript segment count: `764`.
- Teacher question candidates: `35`.
- Visual response alignment: `35`.
- Detected responses: `16`.
- Response rate: about `45.7%`.
- Activity curve and hand-raise events when present.

Unavailable fields are not promoted in the main frontend:

- Attention score `0`.
- Average attention `0`.
- Student count `0`.
- All-zero stage distribution.
- `audio=false` and other debug-only evidence fields.

## Current Implementation

- Added/continued `presentation_scope` classification in the PostgreSQL repository.
- Default teacher and admin lists use frontend/report/trend eligibility filters.
- Report detail for the final ASR sample uses ASR evidence narrative instead of high-risk low-attention rule output.
- Dashboard route respects explicit `result_id` for the server-rendered hero data.
- Frontend metric grids skip null/unavailable average metrics rather than rendering them as `0`.
- Added validation script: `scripts/validate_phase3_17_frontend_sample_scope.sh`.

## Non-Goals

- No database deletion.
- No video re-upload.
- No core visual algorithm changes.
- No local analyzer changes.
- No Raspberry Pi changes.
- No git commit in this phase.

## Runtime Spot Check

Browser check on `2026-05-10` confirmed the final dashboard page is reachable after teacher demo login, the video element is present, and ASR values `764 / 35 / 16` are visible. A follow-up check found that `/teacher/reports` still showed `cls_20260417_101_001` / `video_20260417_001` as `standard_classroom` with `risk_level=high`; the repository scope now classifies that record as legacy test/visual-only data so it is filtered from default formal frontend lists.

## Validation

Run:

```bash
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/dashboard_v11.py cloud_backend/main.py
bash -n scripts/validate_phase3_17_frontend_sample_scope.sh
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_17_frontend_sample_scope.sh
```

The expected final marker is:

```text
PHASE317_FRONTEND_SAMPLE_SCOPE_READY=true
```

Current preparation status:

- Local no-write Python `compile()` check passed for `cloud_backend/postgres_repository.py`, `cloud_backend/teacher_pages.py`, `cloud_backend/admin_pages.py`, `cloud_backend/dashboard_v11.py`, and `cloud_backend/main.py`.
- `bash -n scripts/validate_phase3_17_frontend_sample_scope.sh` passed via Git Bash.
- Runtime validation still requires restarting/reloading the cloud backend service on the server.
