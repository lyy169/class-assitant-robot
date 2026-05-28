# V3 Phase 3.15 Runbook: Dashboard ASR Display

## Purpose

Validate that the cloud dashboard displays Phase 3.14 ASR-enhanced fields for:

```text
phase314_asr_full_classroom_sav_20200908_17
```

## Static Validation

Run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/dashboard_v11.py
bash -n scripts/validate_phase3_15_dashboard_asr_display.sh
```

## Runtime Validation

If the cloud service is running old code, restart it manually first. This runbook does not start or restart the service automatically.

Then run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_15_dashboard_asr_display.sh
```

## Expected Markers

```text
PHASE315_DETAIL_API_OK=true
PHASE315_ASR_DISPLAY_PRESENT=true
PHASE315_TRANSCRIPT_SUMMARY_PRESENT=true
PHASE315_TRANSCRIPT_SEGMENT_COUNT=764
PHASE315_QUESTION_EVENTS_VISIBLE_IN_API=true
PHASE315_QUESTION_EVENT_COUNT=35
PHASE315_RESPONSE_ALIGNMENT_VISIBLE_IN_API=true
PHASE315_RESPONSE_DETECTED_COUNT=16
PHASE315_SPEAKER_DIARIZATION_FALSE=true
PHASE315_DASHBOARD_REACHABLE=true
PHASE315_DASHBOARD_ASR_SECTION_PRESENT=true
PHASE315_DASHBOARD_QUESTION_CANDIDATES_PRESENT=true
PHASE315_DASHBOARD_ASR_BOUNDARY_NOTE_PRESENT=true
PHASE315_NO_TEACHER_IDENTITY_OVERCLAIM=true
PHASE315_VIDEO_STILL_PLAYABLE=true
PHASE315_SAV_SOURCE_NOTE_STILL_PRESENT=true
PHASE315_DASHBOARD_ASR_DISPLAY_OK=true
```

## Browser Check

Open:

```text
http://<server>:8011/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17
```

Verify:

- The video still plays.
- `课堂语音转写与提问候选` section is visible.
- Transcript count and question candidate count are visible.
- Typical question candidates list shows time, text, and response status.
- Boundary note states no speaker diarization and no precise teacher identity judgment.
- Phase 3.8 SAV source note remains visible.
