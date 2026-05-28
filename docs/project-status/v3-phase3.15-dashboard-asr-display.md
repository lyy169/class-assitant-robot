# V3 Phase 3.15 Dashboard ASR Display Status

## Status

Runtime validation passed.

This round:

- Added additive `asr_display` field in teacher detail mapping.
- Added dashboard section for ASR transcript summary, question candidates, and response alignment.
- Added ASR boundary note for no speaker diarization and no precise teacher identity judgment.
- Preserved Phase 3.8 SAV source display notes.
- Added validation script and SDD docs.
- Did not modify database schema.
- Did not modify upload endpoints.
- Did not modify local analyzer or Raspberry Pi code.
- Did not rewrite dashboard.
- Service restart was handled manually by the operator before runtime validation.
- Did not commit git changes.

## Target Sample

```text
analysis_id=phase314_asr_full_classroom_sav_20200908_17
```

Expected ASR facts from Phase 3.14:

- Transcript segments: 764.
- Teacher question candidates: 35.
- Interaction alignment entries: 35.
- Response detected count: 16.
- Speaker diarization: false.
- No teacher identity overclaim.

## Static Validation

Commands requested:

```bash
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/dashboard_v11.py
bash -n scripts/validate_phase3_15_dashboard_asr_display.sh
```

Result:

```text
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/dashboard_v11.py: passed on cloud server
bash -n scripts/validate_phase3_15_dashboard_asr_display.sh: passed
python -B -m py_compile cloud_backend/postgres_repository.py cloud_backend/dashboard_v11.py: blocked in SSHFS CLI by [WinError 5] writing cloud_backend/__pycache__
equivalent no-project-write py_compile check for postgres_repository.py and dashboard_v11.py: passed
text whitespace scan for Phase 3.15 files: passed
```

Note:

- The exact `python -B -m py_compile ...` command should be rerun directly on the cloud server if strict command parity is required.
- Runtime validation was run after the operator manually restarted or refreshed the cloud service.

## Runtime Validation

Command run by operator:

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_15_dashboard_asr_display.sh
```

Result:

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

## Closeout

Phase 3.15 confirms that the cloud dashboard can display the Phase 3.14 ASR-enhanced full-classroom sample with transcript summary, teacher question candidates, visual response alignment, and explicit no-speaker-diarization boundary wording. Video playback and Phase 3.8 SAV source notes remain intact.
