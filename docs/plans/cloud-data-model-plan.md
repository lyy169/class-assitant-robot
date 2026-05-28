# Cloud Data Model Plan

## Goal

Move `cloud_backend/` from raw JSON landing to a teacher-facing query layer that can later be backed by a formal database without breaking the current ingestion mainline. The source-of-truth payload standard is classroom feedback JSON schema `v1.1`.

## Current Read / Write Model

Current write path:

- `POST /api/interaction-results`
- raw JSON stored under `cloud_backend/data/raw/YYYY-MM-DD/`

Current read path:

- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /dashboard`

Current read behavior:

1. prefer matching raw JSON files
2. fall back to sample JSON under `cloud_backend/sample_data/`
3. sort recent results in reverse chronological order
4. support basic `classroom_id` filtering on file-backed data

## Teacher-Facing Required Fields

These fields are currently the minimum needed to keep the dashboard readable and trustworthy:

- `schema_version`
- `analysis_id`
- `classroom_id`
- `video_id`
- `source.source_kind`
- `source.source_path`
- `source.source_host`
- `time.recorded_at`
- `time.generated_at`
- `time.duration_seconds`
- `summary.feedback_score`
- `summary.attention_score`
- `summary.response_score`
- `summary.teacher_question_count`
- `summary.avg_attention_ratio`
- `summary.response_success_rate`
- `summary.summary_text`
- `teacher.question_events`
- `teacher.stage_distribution`
- `students.estimated_student_count`
- `students.hand_raise_event_count`
- `students.zones`
- `timeline.window_size_seconds`
- `timeline.attention_curve`
- `timeline.heat_curve`
- `timeline.activity_curve`

## Current Summary Layer

This round introduces a lightweight summary shape for each result:

- `schema_version`
- `analysis_id`
- `classroom_id`
- `video_id`
- `source_kind`
- `source_path`
- `source_host`
- `recorded_at`
- `generated_at`
- `duration_seconds`
- `feedback_score`
- `attention_score`
- `response_score`
- `teacher_question_count`
- `avg_attention_ratio`
- `response_success_rate`
- `summary_text`
- `question_events`
- `stage_distribution`
- `estimated_student_count`
- `hand_raise_event_count`
- `zones`
- `window_size_seconds`
- `attention_curve`
- `heat_curve`
- `activity_curve`

This summary layer is intentionally storage-agnostic so it can survive a later move to SQLite or PostgreSQL.

## File Storage Limitations

Current file-backed querying is acceptable for low-risk prototyping, but it has clear limits:

- filtering scans files rather than indexed rows
- no pagination yet
- no result detail lookup by `analysis_id` yet
- no trend queries yet
- no efficient cross-classroom history queries yet
- sample fallback is useful for demos, but should not be the long-term teacher data source

## Suggested Future Entities

### InteractionResult

- id
- analysis_id
- classroom_id
- video_id
- source_host
- recorded_at
- generated_at
- duration_seconds
- feedback_score
- attention_score
- response_score
- teacher_question_count
- avg_attention_ratio
- response_success_rate
- summary_text
- raw_payload_path
- source_kind
- created_at

### InteractionMetric

- id
- interaction_result_id
- metric_key
- metric_value

### GridMetric

- id
- interaction_result_id
- grid_key
- metric_key
- metric_value

## Suggested Query Requirements

- latest result by classroom
- recent N results by classroom
- result detail by `window_id`
- trend over time for total interactions
- participation trend over time
- heat distribution trend for the same classroom

## Database Expansion Path

Recommended order:

1. keep raw JSON as the ingestion source of truth
2. preserve the repository abstraction for read queries
3. mirror accepted payloads into SQLite or PostgreSQL
4. move dashboard queries to the database without changing the teacher-facing route structure

## MP4 / Video Integration Boundary

MP4 upload and video browsing should not become part of this storage layer in the current round.

Instead:

- interaction results remain the primary teacher-facing data source
- MP4 and video records become linked supporting assets later
- future result detail pages can reference related video archive records by classroom and time window
