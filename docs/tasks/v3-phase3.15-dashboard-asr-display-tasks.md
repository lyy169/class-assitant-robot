# V3 Phase 3.15 Tasks: Dashboard ASR Display

## Task 1: Detail API Mapping

- Add non-breaking `asr_display` to workbench detail mapping.
- Summarize transcript count, question candidate count, alignment count, response detected count, and response rate.
- Include first 8 transcript snippets.
- Include first 5 question candidates with response status.
- Preserve `raw_payload` unchanged.

Acceptance:

- Detail API returns `asr_display`.
- `transcript_segment_count > 0`.
- `question_event_count > 0`.
- `response_detected_count > 0`.
- `speaker_diarization=false`.

## Task 2: Dashboard Module

- Add a lightweight card titled `课堂语音转写与提问候选`.
- Display summary metrics.
- Display snippets and typical question candidates.
- Display boundary note for no speaker diarization and no precise teacher identity judgment.
- Preserve Phase 3.8 SAV source notes.

Acceptance:

- Dashboard HTML contains `课堂语音转写与提问候选`.
- Dashboard HTML contains `提问候选`.
- Dashboard HTML contains `未进行说话人分离` or equivalent boundary wording.
- Dashboard does not contain overclaim wording such as completed precise teacher identity recognition.

## Task 3: Validation Script

- Add `scripts/validate_phase3_15_dashboard_asr_display.sh`.
- Validate health, teacher login, ASR detail fields, dashboard HTML, video playability, and SAV source note.

Required final marker:

```text
PHASE315_DASHBOARD_ASR_DISPLAY_OK=true
```

## Task 4: Documentation

- Add spec, tasks, runbook, status, and prompt docs.
- Record static/runtime validation status.
- State that no database schema, upload endpoint, dashboard rewrite, local analyzer, or Raspberry Pi code was changed.
