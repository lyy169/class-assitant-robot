# V2 Phase 2.5 Spec: Teacher Classroom Analysis Center

## 1. Background

This project is a competition-oriented intelligent classroom behavior analysis and teaching feedback platform.

The full system has three sides:

```text
Raspberry Pi capture side
  -> local analysis side with YOLO and session assembly
  -> cloud backend
  -> teacher/admin web dashboard
```

Phase 1 has completed the data loop:

- analysis result upload
- raw JSON persistence
- PostgreSQL indexing
- basic teacher query API

Phase 2 has completed the result workbench:

- result list
- classroom/status/limit filters
- detail API
- reviewed/archived status update
- dashboard page with basic charts

Phase 2.5 upgrades the current `/dashboard` into a teacher-facing classroom analysis center.

## 2. Product Position

The final product direction is:

```text
Intelligent Classroom Behavior Analysis and Teaching Feedback Platform
```

For Phase 2.5:

- `/dashboard` is treated as the default teacher console.
- Full login role routing is not implemented in this phase.
- Admin pages are not implemented in this phase.
- The main goal is to clearly explain one analyzed classroom session through video, charts, events, and feedback.

Competition presentation matters. The page should be visually stronger than a plain admin table, but every chart must be driven by real result data or safe fallback states.

## 3. Goals

Phase 2.5 must provide:

- classroom result list with filters
- selected classroom analysis detail
- classroom video area
- attention/activity timeline chart
- teaching stage distribution chart
- front/middle/back zone performance chart
- event distribution chart
- key event list
- event-to-video time jump when video is playable
- teaching feedback summary
- reviewed/archived status update
- graceful fallback when video or fields are missing

## 4. Non-Goals

Do not implement in Phase 2.5:

- full login role routing
- admin console
- independent Vue/Vite frontend rewrite
- permission system redesign
- raw JSON structure changes
- PostgreSQL replacement
- core database table normalization
- new video asset management system
- AI teaching recommendation engine

## 5. User Workflow

Phase 2.5 workflow:

```text
Teacher opens /dashboard
  -> filters classroom results by classroom/status/limit
  -> selects one classroom result
  -> views classroom video, charts, events, and summary
  -> clicks an event to jump to the video time when possible
  -> marks result as reviewed or archived
```

The final product will later use:

```text
/login
  -> teacher console
  -> admin console
```

But Phase 2.5 keeps `/dashboard` as a default teacher view.

## 6. Data Design

Phase 2.5 does not add core database tables.

Current storage strategy remains:

```text
analysis_results structured fields
payload_json deep detail data
raw JSON immutable source
```

The detail API should expose a unified display structure assembled from existing database fields and `payload_json`.

### 6.1 Unified Display Structure

Expected shape:

```json
{
  "result_id": "cls_20260417_101_001",
  "analysis_id": "cls_20260417_101_001",
  "classroom_id": "classroom_101",
  "classroom_name": "Classroom 101",
  "teacher_name": "",
  "lesson_title": "Untitled Lesson",
  "status": "raw",
  "created_at": "2026-04-28T10:00:00+08:00",
  "updated_at": "2026-04-28T10:00:00+08:00",
  "video": {
    "status": "missing",
    "video_id": "",
    "video_url": "",
    "thumbnail_url": "",
    "duration_seconds": 0,
    "captured_at": "",
    "device_id": ""
  },
  "summary": {
    "feedback_score": 0,
    "attention_score": 0,
    "response_score": 0,
    "teacher_question_count": 0,
    "avg_attention_ratio": 0,
    "response_success_rate": 0,
    "summary_text": ""
  },
  "timeline": {
    "window_size_seconds": 30,
    "attention_curve": [],
    "activity_curve": [],
    "heat_curve": []
  },
  "stage_distribution": {
    "exposition_ratio": 0,
    "question_ratio": 0,
    "discussion_ratio": 0,
    "summary_ratio": 0,
    "management_ratio": 0
  },
  "zones": {
    "front": {"avg_attention_ratio": 0, "active_ratio": 0},
    "middle": {"avg_attention_ratio": 0, "active_ratio": 0},
    "back": {"avg_attention_ratio": 0, "active_ratio": 0}
  },
  "events": [],
  "raw_path": "",
  "raw_payload": {}
}
```

Fields may be empty, but the dashboard must not crash when fields are missing.

### 6.2 Compatibility Mapping

The display layer should support these fallbacks:

```text
result_id
  result_id -> analysis_id

score
  feedback_score -> score -> overall_score

created_at
  created_at -> generated_at -> timestamp

events
  events -> issues -> teacher.question_events -> question_events

stage_distribution
  stage_distribution -> teacher.stage_distribution

zones
  zones -> students.zones

video_url
  video.video_url -> video_url -> source.video_url

duration_seconds
  video.duration_seconds -> time.duration_seconds
```

### 6.3 Video States

Video is part of the standard display structure, but it is optional.

Supported states:

```text
playable
  video_url exists and can be loaded by the browser

pending
  video_id, raw_video_path, or source_path exists, but no playable URL exists

missing
  no video evidence exists in the result
```

Dashboard behavior:

- `playable`: render video player.
- `pending`: render captured/pending-sync state.
- `missing`: render no-video fallback.

## 7. API Design

Phase 2.5 should reuse existing teacher APIs.

### 7.1 Recent Results

```http
GET /api/teacher/results/recent?limit=10&classroom_id=classroom_101&status=raw
```

Used for:

- result list
- classroom/status/limit filtering
- top summary cards
- status distribution

This endpoint should remain lightweight and should not return full visualization payloads.

### 7.2 Classrooms

```http
GET /api/teacher/classrooms
```

Used for classroom filter options.

### 7.3 Result Detail

```http
GET /api/teacher/results/{result_id}
```

This is the core Phase 2.5 API.

It should return:

- unified display structure
- video object
- summary
- timeline
- stage_distribution
- zones
- events
- raw_path
- raw_payload

Detail lookup must not fallback to another result. Missing result returns `404`.

### 7.4 Status Update

```http
PATCH /api/teacher/results/{result_id}/status
```

Allowed statuses:

- `raw`
- `reviewed`
- `archived`

Invalid status returns `400`. Missing result returns `404`.

### 7.5 Video API

No new video management API is required in Phase 2.5.

If `result.video.video_url` exists, the dashboard should use it directly. If it does not exist, the dashboard should show a fallback state.

Formal video asset APIs are reserved for Phase 2.8 or Phase 3.

## 8. Fallback Rules

The existing fallback rules remain important:

- recent results without filters may fallback to file/sample data.
- recent results with `classroom_id` or `status` filters must not fallback to unrelated file/sample records.
- detail lookup must not fallback to another result.
- dashboard must handle missing optional fields without breaking.

## 9. Page Design

`/dashboard` becomes the teacher classroom analysis center.

Recommended page structure:

```text
Top brand area
  - Intelligent Classroom Behavior Analysis and Teaching Feedback Platform
  - Teacher Console marker
  - data pipeline status: Capture -> Local Analysis -> Cloud

Filter and summary area
  - classroom filter
  - status filter
  - limit selector
  - refresh
  - metric cards

Main content
  - classroom result list
  - selected classroom analysis detail

Detail area
  - basic session info
  - video player or fallback
  - score cards
  - attention/activity timeline
  - stage distribution
  - zone performance
  - event distribution
  - key event list
  - teaching feedback summary
  - reviewed/archived actions
```

## 10. Charts

### 10.1 Attention and Activity Timeline

Chart type: ECharts line chart.

Data:

- `timeline.attention_curve`
- `timeline.activity_curve`
- `timeline.window_size_seconds`

The X axis should be generated from curve index and `window_size_seconds`.

### 10.2 Teaching Stage Distribution

Chart type: ECharts donut/pie chart.

Data:

- `stage_distribution.exposition_ratio`
- `stage_distribution.question_ratio`
- `stage_distribution.discussion_ratio`
- `stage_distribution.summary_ratio`
- `stage_distribution.management_ratio`

### 10.3 Zone Performance

Chart type: ECharts grouped bar chart.

Data:

- front/middle/back `avg_attention_ratio`
- front/middle/back `active_ratio`

### 10.4 Event Distribution

Chart type: ECharts bar chart or rose/pie chart.

Data:

- aggregate `events[].event_type`

Clicking an event type may filter or highlight event list items if low-risk.

## 11. Interactions

Required interactions:

- changing classroom/status/limit refreshes list and charts.
- selecting a result refreshes detail and charts.
- clicking a key event jumps playable video to `start_sec`.
- if video is not playable, clicking event highlights the event only.
- reviewed/archived updates status and refreshes list/detail state.
- API errors are visible but do not blank the entire page.

## 12. Validation Criteria

API validation:

- recent default returns `200`.
- classrooms returns `200`.
- detail existing result returns `200`.
- detail missing result returns `404`.
- status update returns `200`.
- invalid status returns `400`.
- dashboard returns `200`.

Detail structure validation:

- `result.video` exists.
- `result.summary` exists.
- `result.timeline` exists.
- `result.stage_distribution` exists.
- `result.zones` exists.
- `result.events` exists.

Dashboard validation:

- teacher console marker visible.
- data pipeline status visible.
- filters visible.
- result list visible.
- video area visible.
- four required charts visible.
- key event list visible.
- feedback summary visible.
- reviewed/archived actions visible.
- missing video state does not crash.

Regression validation:

- `POST /api/interaction-results` still works.
- raw JSON still persists.
- PostgreSQL indexing still works.
- latest/recent legacy APIs still work.
- Phase 2 status update still works.

## 13. Future Upgrade Direction

Do not normalize data in Phase 2.5. After visualization stabilizes, Phase 3 may extract stable structures into:

- `video_assets`
- `analysis_events`
- `timeline_points`
- `devices`

This avoids premature database redesign and lets real visualization usage guide later schema decisions.
