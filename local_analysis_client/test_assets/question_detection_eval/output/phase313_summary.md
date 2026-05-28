# Phase 3.13 ASR Question Events And Alignment Summary

## Result

- transcript_segment_count: 150
- question_event_count: 66
- alignment_count: 66
- response_detected_count: 0
- response_success_rate: 0.0

## Boundary

`question_events` 是基于 ASR 文本规则和视觉响应对齐生成的教师提问候选事件。

当前没有说话人分离，因此只输出提问候选，不做教师身份归属判断。所有事件均标记为 `teacher_candidate`，并带有 `speaker_confidence=low_without_diarization`。

本阶段没有上传云端。Phase 3.14 才会上传 ASR 增强版 payload。

## Outputs

- payload: `C:\Users\lyy\Desktop\gradu\ultralytics-8.3.163\test_assets\question_detection_eval\output\phase313_asr_enriched_full_classroom_sav_20200908_17.json`
- question_events.csv: `C:\Users\lyy\Desktop\gradu\ultralytics-8.3.163\test_assets\question_detection_eval\output\question_events.csv`
- interaction_alignment.csv: `C:\Users\lyy\Desktop\gradu\ultralytics-8.3.163\test_assets\question_detection_eval\output\interaction_alignment.csv`
