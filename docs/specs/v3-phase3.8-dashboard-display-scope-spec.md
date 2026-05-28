# V3 Phase 3.8 Spec: Dashboard Display Scope Closeout

## Goal

Phase 3.8 corrects the cloud dashboard display wording for competition presentation. The final dashboard sample must be accurate about source, capture boundary, and metric evidence level.

Final sample:

```text
analysis_id=phase37_full_classroom_sav_20200908_17
/dashboard?result_id=phase37_full_classroom_sav_20200908_17
```

## Background

Phase 3.6a added cloud multipart upload:

```text
POST /api/interaction-results/with-video
```

Phase 3.7 uploaded a same-source full-classroom video and same-source full analysis JSON. That sample is the final dashboard demonstration sample, not the earlier one-minute playback smoke test.

## Non-Goals

This phase does not:

- Rewrite dashboard.
- Redesign the UI.
- Modify core analysis algorithms.
- Modify Raspberry Pi code.
- Modify upload endpoint storage logic.
- Add database migration.
- Treat SAV as Raspberry Pi capture.
- Treat the one-minute demo clip as the final classroom sample.
- Treat 50 SAV slices as one complete classroom dashboard.

## Display Scope Rules

For a final dashboard sample where:

```text
is_final_dashboard_sample=true
source_dataset=SAV
is_pi_capture=false
is_own_capture=false
```

Dashboard must display:

```text
当前课堂样本来自 SAV 外部公开课堂视频，已由本地分析端处理并自动上传至云端；该样本用于完整课堂展示，不属于树莓派自采数据。
```

For a playback smoke test where:

```text
is_demo_playback_sample=true
```

or `sample_type` contains `cloud_playback_demo`, dashboard/detail scope must mark:

```text
该记录为播放链路 smoke test，不作为最终完整课堂分析展示样本。
```

For external SAV samples without audio/transcript/question evidence, dashboard must display:

```text
该外部视频样本未接入树莓派语音触发与课堂转写，语音相关教学阶段和教师提问指标仅作结构展示，不作为主要评价依据。
```

## Detail API Additive Field

The teacher detail API may expose a non-breaking `display_scope` object:

```json
{
  "source_label": "SAV 外部公开课堂视频",
  "analysis_scope": "完整课堂分析",
  "capture_label": "非树莓派采集 / 非自采",
  "is_final_dashboard_sample": true,
  "is_demo_playback_sample": false,
  "unsupported_metric_note": "..."
}
```

This is an additional display field only. It must not alter `raw_payload`.

## Acceptance

- Final sample dashboard states SAV external public classroom video.
- Final sample is not presented as Raspberry Pi capture or self-capture.
- Demo clip is explicitly scoped as smoke test if still present.
- Unsupported audio/transcript/question metrics are marked as structural display only.
- SAV-50 validation slices are not mixed into the single-classroom dashboard.
