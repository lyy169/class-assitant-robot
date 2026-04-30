# V2 Phase 2.5 Teacher Classroom Analysis Center

## 1. Current Status

Phase 2.5 is complete and ready to freeze as a stable deliverable.

Implementation and polish were completed in the SSHFS workspace on 2026-04-28. The teacher-facing `/dashboard` now serves as the Phase 2.5 classroom analysis center. No further Phase 2.5 feature expansion is planned.

Runtime validation must still be executed on the Linux server when a final deployment snapshot is needed because this workspace is mounted through SSHFS. The latest provided server validation had the API and dashboard marker checks passing after the dashboard f-string fix. Upload write regression is optional because it writes new data.

## 2. Modified Files

- `cloud_backend/postgres_repository.py`
- `cloud_backend/config.py`
- `cloud_backend/main.py`
- `cloud_backend/dashboard_v11.py`
- `scripts/validate_phase2_5_teacher_analysis_center.sh`
- `docs/runbooks/v2-phase2.5-validation-runbook.md`
- `docs/project-status/v2-phase2.5-teacher-analysis-center.md`

## 3. Backend Detail Structure

`GET /api/teacher/results/{result_id}` now returns a unified display structure assembled from `analysis_results` and `payload_json`.

Implemented fields:

- `video`: `status`, `video_id`, `video_url`, `thumbnail_url`, `duration_seconds`, `captured_at`, `device_id`, `raw_video_path`
- `summary`: score and teaching feedback fields
- `timeline`: `attention_curve`, `activity_curve`, `heat_curve`, `window_size_seconds`
- `stage_distribution`: exposition, question, discussion, summary, management ratios
- `zones`: front, middle, back attention/activity ratios
- `events`: normalized event list with `event_id`, `event_type`, `question_type`, `start_sec`, `end_sec`, `text`, `raw_event`
- `raw_path`
- `raw_payload`

Compatibility rules:

- Video state is `playable` when a `video_url` exists.
- Video state is `pending` when source/video metadata exists but no playable URL exists.
- Video state is `missing` when no usable video metadata exists.
- Events are read from `events`, `issues`, `teacher.question_events`, or `question_events`.
- No raw JSON structure is modified.
- No core database table is added.

## 4. Dashboard Implementation

`/dashboard` remains the default teacher-facing page and is upgraded into a classroom analysis center.

Implemented visible areas:

- platform title
- `Teacher Console` marker
- `Capture -> Local Analysis -> Cloud` pipeline status
- filters for classroom, status, and limit
- key metric cards
- result list
- selected classroom detail
- video area with playable/pending/missing fallback
- teaching feedback summary
- key event list
- reviewed/archived status actions

Implemented classroom analysis charts with Vue + ECharts:

- Attention / Activity Timeline: reads `result.timeline.attention_curve` and `result.timeline.activity_curve`
- Teaching Stage Distribution: reads `result.stage_distribution`
- Front / Middle / Back Zone Performance: reads `result.zones`
- Event Distribution: reads normalized `result.events`

Interaction behavior:

- Page load fetches recent results and classroom list.
- First result is loaded as selected detail when available.
- Clicking `Detail` fetches unified detail and refreshes video, charts, events, summary, and raw snapshot.
- Clicking an event highlights it; if the video is playable, the player jumps to `start_sec`.
- Mark reviewed/archive updates status through the existing PATCH API; selected detail and the visible list status badge are synchronized without requiring full page reload for the detail panel.

## 5. Validation Added

New server-side validation script:

```bash
scripts/validate_phase2_5_teacher_analysis_center.sh
```

The script validates:

- teacher recent API
- classroom filter
- classrooms API
- unified detail fields
- video/events/timeline shape
- missing result 404
- reviewed status PATCH
- invalid status 400
- legacy latest/recent read APIs
- dashboard HTML markers

Stable dashboard markers checked:

- `data-marker="teacher-analysis-center"`
- `Teacher Console`
- `data-marker="data-pipeline-status"`
- `data-marker="video-area"`
- `data-marker="teaching-feedback-summary"`
- `data-marker="key-event-list"`
- `data-marker="attention-activity-chart"`
- `data-marker="stage-distribution-chart"`
- `data-marker="zone-performance-chart"`
- `data-marker="event-distribution-chart"`

## 6. Static Validation Result

Executed in SSHFS workspace:

```powershell
$env:PYTHONPYCACHEPREFIX="$env:TEMP\codex_pycache"
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py
```

Result:

- `PASS`

Follow-up after server validation:

- Server script reported all API checks passing but `/dashboard` returned `500`.
- Root cause: Vue class binding `:class="{active: ...}"` inside a Python f-string was not escaped, causing `NameError: active`.
- Fix: changed it to `:class="{{active: ...}}"` so Python emits a literal Vue object binding.
- Static Python compile was rerun after the fix and remains `PASS`.

Not executed locally:

- `bash -n scripts/validate_phase2_5_teacher_analysis_center.sh`

Reason:

- Windows/SSHFS shell returned WSL `E_ACCESSDENIED`; run this on the Linux server.

## 7. Server Runtime Validation Commands

Start service:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Run script:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
bash -n scripts/validate_phase2_5_teacher_analysis_center.sh
API_BASE_URL="http://127.0.0.1:8011" \
RESULT_ID="cls_20260417_101_001" \
CLASSROOM_ID="classroom_101" \
bash scripts/validate_phase2_5_teacher_analysis_center.sh
```

Optional upload regression:

```bash
RUN_UPLOAD_REGRESSION=1 \
API_BASE_URL="http://127.0.0.1:8011" \
RESULT_ID="cls_20260417_101_001" \
CLASSROOM_ID="classroom_101" \
bash scripts/validate_phase2_5_teacher_analysis_center.sh
```

## 8. Server Runtime Validation Result

Operator-run result on server after service restart:

- `PHASE25_RECENT_STATUS_200=true`
- `PHASE25_RECENT_FALLBACK_FALSE=true`
- `PHASE25_RECENT_CLASSROOM_STATUS_200=true`
- `PHASE25_CLASSROOMS_STATUS_200=true`
- `PHASE25_CLASSROOMS_SHAPE=true`
- `PHASE25_DETAIL_STATUS_200=true`
- `PHASE25_DETAIL_UNIFIED_STRUCTURE=true`
- `PHASE25_DETAIL_VIDEO_EVENTS_TIMELINE=true`
- `PHASE25_MISSING_DETAIL_404=true`
- `PHASE25_PATCH_REVIEWED_STATUS_200=true`
- `PHASE25_PATCH_REVIEWED_VALUE=true`
- `PHASE25_PATCH_INVALID_STATUS_400=true`
- `PHASE25_LEGACY_LATEST_STATUS_200=true`
- `PHASE25_LEGACY_RECENT_STATUS_200=true`
- `PHASE25_LEGACY_RECENT_FALLBACK_FALSE=true`
- `PHASE25_DASHBOARD_STATUS_200=true`
- `PHASE25_DASHBOARD_TEACHER_CENTER_MARKER=true`
- `PHASE25_DASHBOARD_TEACHER_CONSOLE=true`
- `PHASE25_DASHBOARD_PIPELINE_MARKER=true`
- `PHASE25_DASHBOARD_VIDEO_MARKER=true`
- `PHASE25_DASHBOARD_FEEDBACK_MARKER=true`
- `PHASE25_DASHBOARD_EVENT_LIST_MARKER=true`
- `PHASE25_DASHBOARD_ATTENTION_ACTIVITY_CHART=true`
- `PHASE25_DASHBOARD_STAGE_CHART=true`
- `PHASE25_DASHBOARD_ZONE_CHART=true`
- `PHASE25_DASHBOARD_EVENT_CHART=true`

Upload regression result:

- `PHASE25_UPLOAD_REGRESSION=skipped_set_RUN_UPLOAD_REGRESSION_1`

Reason:

- The command was split before `bash scripts/validate_phase2_5_teacher_analysis_center.sh`, so `RUN_UPLOAD_REGRESSION=1` was not passed into the validation script environment.

## 9. Browser Validation

Open:

```text
http://<server-ip>:8011/dashboard?classroom_id=classroom_101&limit=10
```

Expected:

- Teacher Console heading is visible.
- Capture -> Local Analysis -> Cloud pipeline status is visible.
- Filters and result list are visible.
- Selected classroom detail loads.
- Video area shows playable video, pending state, or missing state without crashing.
- Four classroom analysis charts render.
- Key event list and teaching feedback summary are visible.
- Detail button refreshes selected detail.
- Event click highlights the event and jumps video when playable.
- reviewed/archived buttons update status and keep detail synchronized.

## 10. Phase 1/2 Regression Status

Preserved APIs:

- `POST /api/interaction-results`
- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /api/teacher/results/recent`
- `GET /api/teacher/classrooms`
- `GET /api/teacher/results/{result_id}`
- `PATCH /api/teacher/results/{result_id}/status`

Runtime read regression passed for legacy latest/recent APIs. Upload write regression remains optional and not yet executed in the provided output.

## 11. Known Risks

- Vue and ECharts are still loaded from public CDNs, which is acceptable for the current public-network access model.
- Upload regression is optional in the validation script because it writes another result record/raw file.
- Browser video playback can still fail if the demo `video.mp4` codec/container is not browser-compatible. This is not a Phase 2.5 blocker. Later local-side output should provide H.264/AAC-compatible video, or Phase 2.8 should formalize video-session binding.

## 12. Phase 2.5 Polish Update

Implemented in SSHFS workspace after the core Phase 2.5 validation.

### Video Directory Confirmation

Checked from SSHFS:

- `X:\video_project\uploads`: exists
- `X:\video_project\uploads\video.mp4`: exists
- `X:\video_project\upload`: not found

Linux runtime canonical path:

```text
/root/video_project/uploads/video.mp4
```

The video file is outside `video_project_src` and is not committed into the source repository.

### Static Video Serving

Implemented:

- `CLOUD_VIDEO_UPLOAD_DIR` defaults to `/root/video_project/uploads`.
- FastAPI mounts the first existing video directory at `/uploads`.
- Singular fallback `/root/video_project/upload` is checked only for compatibility.
- Missing video directory does not fail app startup.

Expected runtime URL:

```text
/uploads/video.mp4
```

### Detail Video Fallback

`_display_video()` now preserves priority:

- `payload.video.video_url`
- `payload.video_url`
- `payload.source.video_url`
- `/root/video_project/uploads/video.mp4`
- latest supported video in uploads/upload directory
- existing pending/missing fallback

Supported discovered suffixes:

- `.mp4`
- `.webm`
- `.mov`
- `.ogg`

No raw JSON is modified and no video table/API is added.

### Dashboard Polish

Presentation changes:

- First-screen visual order is now hero then selected classroom analysis.
- Result list remains available but is visually secondary.
- Video area is larger and designed as the primary evidence panel.
- Teaching feedback summary now includes score cards for feedback, attention, and response.
- Old text sections and raw detail snapshot are moved into a collapsed `Debug / Raw Data` block.
- The always-visible `No result selected` conflict text was removed.

Chart readability changes:

- Attention/activity timeline has empty-state text, smoother visual styling, and fixed ratio axis.
- Stage donut filters zero-value slices and uses overlap-safe labels.
- Zone performance uses bounded ratio axis and value labels.
- Event distribution uses readable labels and empty-state text.

Event/video behavior:

- Event list remains compact and scrollable.
- Clicking an event highlights it.
- If video is playable, clicking an event jumps to `start_sec`.
- Missing/pending video states do not break event clicks.

### Polish Validation Additions

`scripts/validate_phase2_5_teacher_analysis_center.sh` now also checks:

- `PHASE25_UPLOADS_VIDEO_MP4_SERVED`
- `PHASE25_DETAIL_VIDEO_PLAYABLE`
- `PHASE25_DETAIL_VIDEO_URL_UPLOADS`
- `PHASE25_DASHBOARD_NO_RESULT_SELECTED_HIDDEN`
- `PHASE25_DASHBOARD_RAW_SNAPSHOT_NOT_PRIMARY`
- `PHASE25_DASHBOARD_DEBUG_COLLAPSE_MARKER`

### Polish Static Validation

Executed in SSHFS workspace:

```powershell
$env:PYTHONPYCACHEPREFIX="$env:TEMP\codex_pycache"
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py
```

Result:

- `PASS`

## 13. Final Acceptance Summary

Final Phase 2.5 scope completed:

- Unified teacher detail structure.
- Existing teacher APIs preserved.
- Existing Phase 1 read APIs preserved.
- `/dashboard` teacher classroom analysis center.
- Video/status area with static `/uploads` demo fallback.
- Teaching feedback summary.
- Four classroom charts.
- Compact event list with highlight and playable-video jump behavior.
- reviewed/archived status operation.
- Debug/raw data collapsed by default.
- Server validation script and runbook updated.

Final validation state:

- SSHFS static Python compile: `PASS`.
- Dashboard HTML construction check: `PASS` in prior polish validation.
- Server API/dashboard marker validation: previously passed after service restart.
- Server video/static route validation: `PASS`.
- Server detail playable video fallback validation: `PASS`.
- Browser visual validation: manual, use `/dashboard?classroom_id=classroom_101&limit=10`.

Phase 2.5 freeze decision:

- Freeze Phase 2.5 after one final server script run.
- Do not add admin console, login routing, video upload API, upload transcoding, `video_assets`, raw JSON redesign, or Phase 3 capabilities in this phase.

Recommended next phases:

- Phase 2.8: video-session binding and browser-compatible video production contract.
- Phase 3: admin console, trend analysis, formal video asset model, and broader platformization.

## 14. Final Server Validation Result

Operator-run result on the Linux server:

- `PHASE25_UPLOADS_VIDEO_MP4_SERVED=true`
- `PHASE25_RECENT_STATUS_200=true`
- `PHASE25_RECENT_FALLBACK_FALSE=true`
- `PHASE25_RECENT_CLASSROOM_STATUS_200=true`
- `PHASE25_CLASSROOMS_STATUS_200=true`
- `PHASE25_CLASSROOMS_SHAPE=true`
- `PHASE25_DETAIL_STATUS_200=true`
- `PHASE25_DETAIL_UNIFIED_STRUCTURE=true`
- `PHASE25_DETAIL_VIDEO_EVENTS_TIMELINE=true`
- `PHASE25_DETAIL_VIDEO_PLAYABLE=true`
- `PHASE25_DETAIL_VIDEO_URL_UPLOADS=true`
- `PHASE25_MISSING_DETAIL_404=true`
- `PHASE25_PATCH_REVIEWED_STATUS_200=true`
- `PHASE25_PATCH_REVIEWED_VALUE=true`
- `PHASE25_PATCH_INVALID_STATUS_400=true`
- `PHASE25_LEGACY_LATEST_STATUS_200=true`
- `PHASE25_LEGACY_RECENT_STATUS_200=true`
- `PHASE25_LEGACY_RECENT_FALLBACK_FALSE=true`
- `PHASE25_UPLOAD_REGRESSION=skipped_set_RUN_UPLOAD_REGRESSION_1`
- `PHASE25_DASHBOARD_STATUS_200=true`
- `PHASE25_DASHBOARD_TEACHER_CENTER_MARKER=true`
- `PHASE25_DASHBOARD_TEACHER_CONSOLE=true`
- `PHASE25_DASHBOARD_PIPELINE_MARKER=true`
- `PHASE25_DASHBOARD_VIDEO_MARKER=true`
- `PHASE25_DASHBOARD_FEEDBACK_MARKER=true`
- `PHASE25_DASHBOARD_EVENT_LIST_MARKER=true`
- `PHASE25_DASHBOARD_ATTENTION_ACTIVITY_CHART=true`
- `PHASE25_DASHBOARD_STAGE_CHART=true`
- `PHASE25_DASHBOARD_ZONE_CHART=true`
- `PHASE25_DASHBOARD_EVENT_CHART=true`
- `PHASE25_DASHBOARD_NO_RESULT_SELECTED_HIDDEN=true`
- `PHASE25_DASHBOARD_RAW_SNAPSHOT_NOT_PRIMARY=true`
- `PHASE25_DASHBOARD_DEBUG_COLLAPSE_MARKER=true`

Conclusion:

- Phase 2.5 runtime API validation: `PASS`
- Phase 2.5 dashboard marker validation: `PASS`
- Phase 1/2 read regression: `PASS`
- Optional upload write regression: skipped by design in this run
- Phase 2.5 status: frozen pending only browser visual acceptance
