# V2 Phase 2.5 Tasks: Teacher Classroom Analysis Center

## Principles

- Do not break Phase 1 upload, raw persistence, or PostgreSQL indexing.
- Do not rewrite raw JSON.
- Do not add core database tables in this phase.
- Do not introduce a full login/permission redesign.
- Keep `/dashboard` as the default teacher console for Phase 2.5.
- Prefer enhancing existing teacher APIs over adding new endpoints.
- Every implementation step must have a validation step.

## Task 1: Confirm Current Baseline

Read and confirm:

- `cloud_backend/main.py`
- `cloud_backend/auth.py`
- `cloud_backend/postgres_repository.py`
- `cloud_backend/dashboard_v11.py`
- `docs/specs/v2-phase2.5-workbench-spec.md`
- `docs/project-status/v2-phase2-result-workbench.md`

Validation:

- Confirm existing Phase 2 APIs and dashboard markers before editing.
- Record any mismatch in the Phase 2.5 project status document.

## Task 2: Add Unified Detail Display Mapping

Owner files:

- `cloud_backend/postgres_repository.py`
- `cloud_backend/auth.py`
- optional helper module if the code becomes too large

Implement a unified display structure for `GET /api/teacher/results/{result_id}`:

- result identity
- classroom and lesson metadata
- status timestamps
- video object with `playable`, `pending`, or `missing`
- summary
- timeline
- stage_distribution
- zones
- unified events
- raw_path
- raw_payload

Compatibility mapping:

- `result_id -> analysis_id`
- `feedback_score -> score -> overall_score`
- `created_at -> generated_at -> timestamp`
- `events -> issues -> teacher.question_events -> question_events`
- `stage_distribution -> teacher.stage_distribution`
- `zones -> students.zones`
- `video.video_url -> video_url -> source.video_url`
- `video.duration_seconds -> time.duration_seconds`

Validation:

- Existing detail result returns `200`.
- Detail response contains `video`, `summary`, `timeline`, `stage_distribution`, `zones`, `events`.
- Missing result returns `404`.

## Task 3: Preserve Recent/Classrooms/Status API Behavior

Owner files:

- `cloud_backend/auth.py`
- `cloud_backend/postgres_repository.py`

Keep existing APIs:

- `GET /api/teacher/results/recent`
- `GET /api/teacher/classrooms`
- `PATCH /api/teacher/results/{result_id}/status`

Ensure:

- recent remains lightweight.
- classroom/status/limit filters still work.
- filtered recent queries do not fallback to unrelated file/sample rows.
- status values remain `raw`, `reviewed`, `archived`.

Validation:

- recent default returns `200`.
- recent with `classroom_id` returns `200`.
- recent with `status` returns `200`.
- classrooms returns `200`.
- status update to `reviewed` returns `200`.
- invalid status returns `400`.

## Task 4: Upgrade Dashboard Layout

Owner file:

- `cloud_backend/dashboard_v11.py`

Convert `/dashboard` into a teacher classroom analysis center.

Required visible areas:

- platform title
- teacher console marker
- Capture -> Local Analysis -> Cloud data pipeline status
- filters
- summary metric cards
- classroom result list
- selected classroom analysis detail
- video area
- four chart panels
- key event list
- teaching feedback summary
- reviewed/archived actions

Do not create a separate Vue/Vite frontend in this phase.

Validation:

- `/dashboard` returns `200`.
- dashboard HTML contains stable markers for all required areas.

## Task 5: Implement Video Area and Event Jump

Owner file:

- `cloud_backend/dashboard_v11.py`

Behavior:

- if `result.video.status == "playable"` and `video_url` exists, render a video player.
- if `result.video.status == "pending"`, render captured/pending-sync state.
- if `result.video.status == "missing"`, render no-video fallback.
- clicking an event with `start_sec` jumps the video to that time when the video is playable.
- without playable video, clicking an event highlights the event only.

Validation:

- playable video URL renders a player.
- missing video state does not throw JavaScript errors.
- event click does not break when video is unavailable.

## Task 6: Replace Generic Charts With Classroom Analysis Charts

Owner file:

- `cloud_backend/dashboard_v11.py`

Implement the four required ECharts:

1. Attention/activity timeline
   - source: `timeline.attention_curve`, `timeline.activity_curve`
   - X axis generated from `window_size_seconds`

2. Teaching stage distribution
   - source: `stage_distribution`
   - chart: donut/pie

3. Zone performance
   - source: `zones.front/middle/back`
   - chart: grouped bar
   - series: attention and activity

4. Event distribution
   - source: unified `events`
   - chart: bar or rose/pie

Validation:

- all four chart containers exist.
- all four charts render with real or empty-safe data.
- selecting another result refreshes all four charts.
- API failure shows a visible error without blanking the page.

## Task 7: Implement Detail Selection and State Sync

Owner file:

- `cloud_backend/dashboard_v11.py`

Behavior:

- result list item has a clear "view analysis" action.
- selecting a result loads `GET /api/teacher/results/{result_id}`.
- detail area refreshes video, charts, events, summary, and status.
- status update refreshes list and current detail state.

Validation:

- clicking a result changes the detail panel.
- reviewed/archived updates persist after refresh.
- list and detail show the same current status.

## Task 8: Update Validation Script

Owner files:

- existing validation script if present, preferably `scripts/validate_phase2_result_workbench.sh`
- or create a Phase 2.5 validation script if needed

Add checks for:

- dashboard HTML marker for teacher console.
- dashboard HTML marker for data pipeline status.
- video area marker.
- attention/activity timeline chart marker.
- stage distribution chart marker.
- zone performance chart marker.
- event distribution chart marker.
- detail JSON contains unified fields.

Validation:

- script reports clear `true/false` markers.
- script does not require browser automation.

## Task 9: Regression Validation

Run or document server-side validation for:

- `POST /api/interaction-results`
- raw JSON file persistence
- PostgreSQL indexing
- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /api/teacher/results/recent`
- `GET /api/teacher/results/{result_id}`
- `PATCH /api/teacher/results/{result_id}/status`
- `GET /dashboard`

If the SSHFS workspace cannot run runtime checks, document which checks must be run on the Linux server.

## Task 10: Update Documentation

Update:

- `docs/specs/v2-phase2.5-workbench-spec.md`
- `docs/tasks/v2-phase2.5-result-workbench-tasks.md`
- `docs/runbooks/v2-phase2.5-validation-runbook.md`
- `docs/project-status/v2-phase2.5-teacher-analysis-center.md`

Final implementation report must include:

- modified files
- chart implementation summary
- API validation results
- dashboard validation results
- Phase 1/2 regression results
- remaining risks
