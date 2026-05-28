# V3 Phase 3.17 Spec: Frontend Sample Scope And Legacy Data Isolation

## Goal

Phase 3.17 makes the cloud frontend demo-safe by applying one consistent presentation scope across the dashboard, teacher pages, report center, trend pages, and admin pages.

Final sample:

```text
analysis_id=phase314_asr_full_classroom_sav_20200908_17
dashboard=/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17
```

The sample must remain the default full-classroom ASR demo with video, ASR transcript summary, question candidates, visual response alignment, activity timeline, and source boundary notes.

## Problem

The frontend can mix different sample scopes:

- Final ASR-enhanced full classroom sample.
- Historical SAV full classroom uploads from earlier phases.
- Playback or smoke-test demo clips derived from the same SAV classroom.
- Old test records such as `video_video` records that may point to stale video paths and all-zero metrics.
- Optional demo or seed data.

This creates misleading duplicates, all-zero metrics, missing videos, and inconsistent data-source wording.

## Non-Goals

This phase does not:

- Delete database rows.
- Rewrite raw uploaded JSON.
- Fabricate attention, student count, teaching stage, or interaction scores.
- Modify core vision algorithms.
- Modify ASR algorithms.
- Modify local analyzer code.
- Modify Raspberry Pi code.
- Modify upload endpoints.
- Add database migration unless a later phase explicitly requires it.
- Commit git changes.

## Presentation Scope Contract

Every frontend-facing result should expose additive scope fields while keeping raw payload unchanged:

```json
{
  "record_kind": "competition_final",
  "display_badge": "最终完整课堂 ASR 样本",
  "frontend_visible": true,
  "report_eligible": true,
  "trend_eligible": true,
  "metric_profile": "asr_full_classroom",
  "is_demo_data": false,
  "is_historical": false,
  "dataset_source": "SAV external public classroom video",
  "note": "...",
  "metrics": []
}
```

Pages may mirror `presentation_scope.metrics` as `display_metrics` for compact metric lines.

## Record Kinds

Use these kinds:

```text
competition_final
historical_version
smoke_test
legacy_test_data
demo_data
standard_classroom
```

Expected behavior:

- `competition_final`: visible by default, report eligible, trend eligible.
- `historical_version`: hidden from default report/trend lists; visible only in explicit all/history/debug contexts with a historical badge.
- `smoke_test`: hidden from formal report/trend views; if visible, labeled as smoke test/demo.
- `legacy_test_data`: hidden from default teacher/admin frontstage lists; if visible, labeled as old test data.
- `demo_data`: visible only when demo/all filter is explicitly selected and labeled.
- `standard_classroom`: normal uploaded classroom data with consistent source口径 and usable metrics.

## Final Sample Display

For `phase314_asr_full_classroom_sav_20200908_17`, keep and emphasize:

- Complete classroom video.
- `transcript_segment_count=764`.
- `question_event_count=35`.
- `interaction_alignment_count=35`.
- `response_detected_count=16`.
- Response success rate around `45.7%`.
- Classroom activity curve when nonzero.
- Hand-raise events when present.
- SAV external public classroom source note.
- Not Raspberry Pi captured.
- Not self-captured.
- Local offline faster-whisper ASR note.
- No speaker diarization, therefore question events are teacher-question candidates only.

Do not show these as primary conclusions for the same sample:

- `attention_score=0`.
- `avg_attention_ratio=0`.
- `estimated_student_count=0`.
- All-zero teaching stage distribution chart.
- `audio=false` as a user-facing conclusion.
- `interaction_score=0` as a formal teaching quality score.
- High-risk conclusion caused only by unavailable visual metrics.

## Report Center

Default teacher report center must:

- Include `phase314_asr_full_classroom_sav_20200908_17`.
- Exclude `phase37_full_classroom_sav_20200908_17`.
- Exclude `phase35_local_imported_sav_full_classroom_20200908_17`.
- Exclude old `video_video` or stale-video test records.
- Exclude `cls_20260417_101_001` / `video_20260417_001` from default competition report/trend views, or expose it only with an explicit legacy visual-only label.
- Avoid showing multiple versions of the same classroom as separate formal reports.
- Label demo/all/history records if they are exposed by explicit filters.

## Teacher And Admin Pages

The same scope must apply to:

```text
/teacher
/teacher/results
/teacher/reports
/teacher/trends
/admin
/admin/results
/admin/trends
```

Default real-data views should not use historical, smoke-test, or legacy-test records to compute headline counts, rankings, risk lessons, or trends unless the page explicitly labels that broader scope.

## Dashboard

The dashboard must keep the core demo experience:

- Video area remains present and playable.
- ASR summary remains visible.
- Question candidates and visual response alignment remain visible.
- Activity timeline remains visible when available.
- Low-confidence/unavailable metrics remain hidden from the main display for the final SAV ASR sample.
- SAV source and ASR no-speaker-diarization notes remain visible.

## Validation Markers

Phase 3.17 validation should emit:

```text
PHASE317_DASHBOARD_REACHABLE=true
PHASE317_DASHBOARD_VIDEO_PRESENT=true
PHASE317_DASHBOARD_ASR_METRICS_VISIBLE=true
PHASE317_TEACHER_REPORTS_PHASE314_PRESENT=true
PHASE317_TEACHER_REPORTS_PHASE37_HIDDEN=true
PHASE317_TEACHER_REPORTS_PHASE35_HIDDEN=true
PHASE317_TEACHER_REPORTS_LEGACY_VIDEO_VIDEO_HIDDEN=true
PHASE317_TEACHER_REPORTS_DEFAULT_SCOPE_OK=true
PHASE317_PHASE314_REPORT_DETAIL_SCOPE_OK=true
PHASE317_PHASE314_REPORT_NO_ATTENTION_ZERO=true
PHASE317_PHASE314_REPORT_NO_STAGE_ZERO_CHART=true
PHASE317_PHASE314_REPORT_NO_HIGH_RISK_OVERCLAIM=true
PHASE317_TEACHER_HOME_SCOPE_OK=true
PHASE317_TEACHER_RESULTS_SCOPE_OK=true
PHASE317_TEACHER_TRENDS_SCOPE_OK=true
PHASE317_ADMIN_RESULTS_SCOPE_OK=true
PHASE317_ADMIN_TRENDS_SCOPE_OK=true
PHASE317_DEMO_DATA_LABELED=true
PHASE317_HISTORY_DATA_LABELED_OR_FILTERED=true
PHASE317_LEGACY_TEST_DATA_FILTERED=true
PHASE317_NO_FAKE_ATTENTION=true
PHASE317_NO_FAKE_STUDENT_COUNT=true
PHASE317_NO_DB_DELETE=true
PHASE317_FRONTEND_SAMPLE_SCOPE_READY=true
```
