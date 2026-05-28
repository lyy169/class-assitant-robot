# V3 Phase 3.15b Dashboard ASR Consistency Runbook

## Purpose

Validate that the ASR-enhanced full-classroom dashboard uses the Phase 3.14 transcript/question/alignment fields consistently and no longer shows legacy no-question/no-transcript wording.

Target result:

```text
phase314_asr_full_classroom_sav_20200908_17
```

## Preconditions

- Cloud backend is running on port `8011`.
- The Phase 3.14 ASR sample has already been uploaded.
- Operator has manually restarted or refreshed the backend after code changes.
- This runbook does not start, stop, or restart services.

## Static Checks

Run from `/root/video_project_src`:

```bash
source /root/venv/bin/activate
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/dashboard_v11.py cloud_backend/admin_pages.py cloud_backend/teacher_pages.py
bash -n scripts/validate_phase3_15b_dashboard_asr_consistency.sh
```

## Runtime Validation

Run from `/root/video_project_src` after manual service restart:

```bash
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_15b_dashboard_asr_consistency.sh
```

Expected final marker:

```text
PHASE315B_DASHBOARD_ASR_CONSISTENCY_OK=true
```

## Manual Browser Check

Open:

```text
http://8.148.205.228:8011/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17
```

Confirm:

- Summary says local ASR transcript was generated and shows 764/35/16.
- The page does not say no clear question event was identified.
- The page does not say teacher question transcript is unavailable.
- The scope note mentions no Raspberry Pi voice trigger and no speaker diarization, while confirming local offline ASR transcript.
- Activity curve remains visible.
- Attention/heat/stage zero values show low-confidence/empty-state wording.
- Event distribution contains question candidates.
- SAV sample is not described as Raspberry Pi capture or self-captured data.

## Boundaries

- Do not modify database structure.
- Do not modify upload endpoints.
- Do not modify local analyzer or Raspberry Pi code.
- Do not fabricate attention, heat, or stage data.
- Do not commit unless a later closeout task explicitly asks for it.
