# V3 Phase 3.15 Spec: Dashboard ASR Display

## Goal

Phase 3.15 exposes Phase 3.14 ASR-enhanced classroom fields in the cloud teacher dashboard without changing upload storage, database schema, local algorithms, or Raspberry Pi code.

Final ASR dashboard sample:

```text
analysis_id=phase314_asr_full_classroom_sav_20200908_17
/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17
```

## Non-Goals

This phase does not:

- Modify local analyzer code.
- Modify Raspberry Pi code.
- Modify core ASR or vision algorithms.
- Modify `POST /api/interaction-results`.
- Modify `POST /api/interaction-results/with-video`.
- Add database migration.
- Rewrite dashboard.
- Claim precise teacher identity recognition.

## Data Sources

The display payload reads optional fields from raw JSON:

- `audio`
- `transcript`
- `teacher.question_events`
- `interaction_alignment`
- `asr_quality`
- `evidence_summary`

## `asr_display`

Teacher detail response may expose an additive `asr_display` object:

```json
{
  "transcript_present": true,
  "transcript_segment_count": 764,
  "asr_engine": "faster-whisper",
  "question_event_count": 35,
  "alignment_count": 35,
  "response_detected_count": 16,
  "response_success_rate": 0.4571,
  "speaker_diarization": false,
  "teacher_identity_confidence": "low_without_diarization",
  "snippets": [],
  "question_events": [],
  "note": "..."
}
```

`snippets` and `question_events` are capped preview lists. The dashboard must not place all transcript segments into the first screen.

## Dashboard Display

Add a lightweight section:

```text
课堂语音转写与提问候选
```

It should show:

- Transcript status.
- Transcript segment count.
- Question candidate count.
- Response detected count.
- Response success rate.
- ASR engine when available.
- First few transcript snippets.
- First few question candidates with response status.

## Boundary Note

The dashboard must display:

```text
提问事件基于本地 ASR 转写、规则检测与视觉响应对齐生成；当前未进行说话人分离，因此作为教师提问候选事件展示，不做精准教师身份判断。
```

If transcript is missing, it should show:

```text
当前样本未提供课堂转写，语音相关指标仅作结构展示。
```

## Compatibility

Phase 3.8 source notes must remain visible. The SAV ASR sample remains an external public classroom video processed locally and uploaded to the cloud.
