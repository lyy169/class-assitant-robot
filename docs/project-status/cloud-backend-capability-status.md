# Cloud Backend Capability Status

## Current Confirmed Endpoints

`cloud_backend/` now provides:

- `GET /health`
- `POST /api/interaction-results`
- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /dashboard`

## What Each Capability Covers

### Ingestion Mainline

- `POST /api/interaction-results`
- validates the incoming JSON against classroom feedback schema `v1.1`
- applies minimal business checks such as `classroom_id` and `source_host`
- stores raw JSON under `cloud_backend/data/raw/YYYY-MM-DD/`

### Read-Back Capability

- `GET /api/latest-interaction-result`
  - returns the latest readable classroom interaction result
  - supports optional `classroom_id`
- `GET /api/recent-interaction-results`
  - returns recent results in reverse chronological order
  - supports `limit`
  - supports optional `classroom_id`
  - falls back to sample data when no raw result exists

### Teacher-Facing Display

- `GET /dashboard`
  - now acts as a minimal teacher results center instead of a single-result debug page
  - renders protocol-aligned summary, teacher question events, stage distribution, zone stats, and timeline curves

## Current Storage Behavior

- write path: raw JSON files under `cloud_backend/data/raw/`
- read path priority:
  1. latest matching raw JSON
  2. sample JSON under `cloud_backend/sample_data/`

## Current Teacher-Facing Modules

The dashboard currently shows:

- latest classroom overview card
- recent N result list
- `classroom_id` filter entry
- teacher question events
- stage distribution
- zone summary
- timeline curve summary
- short system note about future MP4 and video archive integration

## Current Data Model Progress

The codebase now has a lightweight summary layer for:

- `analysis_id`
- `classroom_id`
- `video_id`
- `source_host`
- `recorded_at`
- `generated_at`
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

This summary layer is still file-based and is not yet backed by a formal database.

## Remaining Gaps

- no dedicated result detail endpoint by `window_id` yet
- no pagination yet
- no trend aggregation API yet
- no database-backed query layer yet
- no teacher authentication layer yet
- MP4 upload and video browsing are still preserved assets outside the new dashboard mainline

## Boundary Judgment

This round makes `cloud_backend/` closer to a real teacher-facing cloud entry, but it is still:

- a low-risk results center
- backed by file storage
- intentionally separate from old Flask legacy code
