# V2 Phase 2.7 Spec: Admin Console and Platform Overview

## 1. Background

Phase 2.5 delivered the teacher classroom analysis detail center.

Phase 2.6 delivered the teacher home and classroom records center.

Phase 2.7 adds an administrator-facing platform view so the system presents as a complete classroom analytics platform rather than a single-teacher demo.

This phase is competition-oriented. Admin pages must be visually complete and presentation-ready.

## 2. Stage Goal

Phase 2.7 builds:

- admin platform overview
- classroom overview
- teacher overview
- all classroom results view
- lightweight system/data ingestion status

The goal is to let an administrator understand:

- how many teachers/classes/results exist
- how results are distributed by status
- which classes and teachers are active
- when data was last uploaded
- how to jump from global data into a single classroom analysis detail

## 3. Permission Boundary

Phase 2.7 does not implement the formal permission system.

Current behavior:

```text
/admin routes are accessible as demo admin context
pages show Admin Console
APIs expose platform aggregate data for demo/admin presentation
```

Formal login, role routing, strict permission isolation, and related database design are reserved for Phase 2.9.

## 4. Routes

Add:

```text
GET /admin
GET /admin/classrooms
GET /admin/teachers
GET /admin/results
```

Reuse:

```text
GET /dashboard?result_id=xxx
GET /teacher
```

## 5. User Workflow

### 5.1 Platform Overview Flow

```text
Admin opens /admin
  -> reviews platform metrics and data ingestion state
  -> checks recent classroom analyses
  -> opens /dashboard?result_id=xxx for detail
```

### 5.2 Classroom Flow

```text
Admin opens /admin/classrooms
  -> reviews all classrooms
  -> sees teacher binding, result count, average scores, latest result
  -> opens /admin/results?classroom_id=xxx
```

### 5.3 Teacher Flow

```text
Admin opens /admin/teachers
  -> reviews all teachers
  -> sees classroom count, result count, average score, latest result
  -> opens /admin/results?teacher_id=xxx
```

### 5.4 All Results Flow

```text
Admin opens /admin/results
  -> filters by classroom, teacher, status, and time range
  -> reviews all platform classroom results
  -> opens /dashboard?result_id=xxx
```

## 6. Page Modules

All admin pages must include unified Admin Console navigation:

```text
Platform name
Admin Console marker
links: Platform Overview, Classrooms, Teachers, Classroom Data, Teacher Console
Demo Admin / data update label
```

Pages must be visually complete. A page with only filters and a table is not acceptable for Phase 2.7.

Each admin page must include:

- top overview/explanation area
- metric cards or overview summary
- main list/table
- supporting summary/ranking/status/tips module

### 6.1 `/admin`

Required modules:

- platform status hero
- Capture -> Local Analysis -> Cloud -> Teacher Feedback pipeline
- core metric cards
- data ingestion status
- result status distribution
- recent classroom analyses
- quick links

### 6.2 `/admin/classrooms`

Required modules:

- classroom overview metric cards
- classroom search/filter
- classroom list
- classroom performance ranking or recent active classrooms
- action: view classroom results

Each classroom item should show:

- classroom id
- classroom name
- teacher name
- result count
- average feedback/attention/response score
- raw/reviewed/archived counts
- latest result time
- results URL

### 6.3 `/admin/teachers`

Required modules:

- teacher overview metric cards
- teacher search/filter
- teacher list
- teacher classroom count ranking
- teacher average feedback score ranking
- action: view teacher results

Each teacher item should show:

- teacher id
- teacher name
- username
- classroom count
- result count
- average feedback/attention/response score
- latest result time
- results URL

### 6.4 `/admin/results`

Required modules:

- result overview metric cards
- status distribution
- filters
- all-platform result list
- high-score / low-attention tips
- action: view analysis detail

Each result item should show:

- result id
- classroom
- teacher
- lesson
- generated/created time
- feedback/attention/response score
- status
- video availability
- detail URL

## 7. Data Model and Database Design

Phase 2.7 does not add core database tables.

Reuse existing tables:

- `users`
- `classrooms`
- `sessions`
- `analysis_results`

Admin view is global:

```text
teacher view = filtered by teacher context
admin view = all visible platform data
```

If teacher mappings are incomplete:

- use `classrooms.teacher_user_id` when available
- fallback to `Demo Teacher` or `Unknown Teacher`
- never fail the page because teacher mapping is missing

### 7.1 Admin Overview Aggregates

Compute:

- teacher_count
- classroom_count
- result_count
- recent_result_count
- today_result_count
- raw_count
- reviewed_count
- archived_count
- avg_feedback_score
- avg_attention_score
- avg_response_score
- latest_upload_at
- latest_raw_path
- latest_analysis_id
- latest_results
- status_distribution
- system_status

### 7.2 Classroom Aggregates

Compute:

- classroom_count
- active_classroom_count
- avg_feedback_score
- latest_result_at
- classroom items with score and status counts

### 7.3 Teacher Aggregates

Compute:

- teacher_count
- teachers_with_classrooms
- teachers_with_results
- avg_feedback_score
- teacher items with classroom/result counts and score averages

### 7.4 Admin Result Items

Each item should include:

- result_id
- analysis_id
- classroom_id
- classroom_name
- teacher_id
- teacher_name
- lesson_title
- generated_at
- created_at
- feedback_score
- attention_score
- response_score
- status
- has_video
- video_status
- detail_url

## 8. API Design

### 8.1 Admin Overview

```http
GET /api/admin/overview
```

Required response keys:

- success
- admin
- metrics
- system_status
- status_distribution
- latest_results
- quick_links

### 8.2 Admin Classrooms

```http
GET /api/admin/classrooms
```

Parameters:

- `q`
- `teacher_id`
- `limit`
- `offset`

Required response keys:

- success
- overview
- items
- total

### 8.3 Admin Teachers

```http
GET /api/admin/teachers
```

Parameters:

- `q`
- `limit`
- `offset`

Required response keys:

- success
- overview
- items
- total

### 8.4 Admin Results

```http
GET /api/admin/results
```

Parameters:

- `classroom_id`
- `teacher_id`
- `status`
- `days`
- `limit`
- `offset`

Required response keys:

- success
- filters
- overview
- items
- total

Invalid status returns `400`.

`limit` must be bounded to a maximum of `100`.

`days` should support `7`, `30`, and `all` or consistent clamping.

## 9. Frontend Interaction

Use server-rendered HTML with embedded JavaScript, consistent with Phase 2.5 and Phase 2.6.

Do not introduce an independent Vue/Vite frontend.

### 9.1 `/admin`

On load:

```text
fetch /api/admin/overview
render metrics, system status, distribution, latest results, quick links
```

Interactions:

- recent result -> `/dashboard?result_id=xxx`
- status distribution -> `/admin/results?status=raw`
- quick links -> admin pages
- teacher console link -> `/teacher`

### 9.2 `/admin/classrooms`

On load:

```text
fetch /api/admin/classrooms
```

Interactions:

- search/filter refreshes list and URL
- view results -> `/admin/results?classroom_id=xxx`

### 9.3 `/admin/teachers`

On load:

```text
fetch /api/admin/teachers
```

Interactions:

- search refreshes list and URL
- view results -> `/admin/results?teacher_id=xxx`

### 9.4 `/admin/results`

On load:

```text
fetch /api/admin/classrooms
fetch /api/admin/teachers
fetch /api/admin/results?...filters
```

Interactions:

- filters update URL and refresh records
- view analysis -> `/dashboard?result_id=xxx`

## 10. Validation Criteria

Pages:

- `/admin` returns `200`
- `/admin/classrooms` returns `200`
- `/admin/teachers` returns `200`
- `/admin/results` returns `200`
- all admin pages include Admin Console navigation
- all admin pages include overview/metric/list/supporting modules

APIs:

- `/api/admin/overview` returns required keys
- `/api/admin/classrooms` returns required keys
- `/api/admin/teachers` returns required keys
- `/api/admin/results` returns required keys
- `/api/admin/results?status=bad_status` returns `400`

Workflow:

- `/admin` recent result opens dashboard detail
- `/admin` status distribution opens filtered results
- `/admin/classrooms` item opens filtered results
- `/admin/teachers` item opens filtered results
- `/admin/results` item opens dashboard detail
- admin navigation can open `/teacher`

Regression:

- Phase 2.6 `/teacher` and `/teacher/results` still work
- Phase 2.5 `/dashboard` and detail API still work
- Phase 1/2 latest/recent APIs still work
- raw JSON remains unchanged

## 11. Risks

- Admin console can easily expand into a full CRUD backend.
- Strict permissions are not implemented yet.
- Teacher mappings may be incomplete.
- Pages can become table-only if presentation constraints are ignored.
- Runtime validation must run on the Linux server.

## 12. Non-Goals

Do not implement:

- full login
- role routing
- strict permission isolation
- create/edit/delete teachers
- create/edit/delete classrooms
- password reset
- delete classroom results
- device management
- video upload management
- schedule management
- audit logs
- system configuration center
- AI analysis
- trend prediction
- report export
- core database table additions
- raw JSON changes
- independent frontend rewrite

## 13. Future Phases

- Phase 2.8: device and video ingestion status
- Phase 2.9: unified login, role routing, permission system, auth database design
- Phase 3: trends, reports, intelligent feedback
