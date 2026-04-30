# V2 Phase 2.5 Polish Tasks: Competition Demo Readiness

## Principles

- Polish only. Do not expand into admin, login, or Phase 3.
- Do not change raw JSON.
- Do not add core database tables.
- Do not add a full video upload API.
- Keep existing teacher APIs stable.
- Use `/root/video_project/uploads` as the canonical demo video directory.
- Support demo `video.mp4` playback through static serving.

## Task 1: Confirm Demo Video Location

Check runtime-accessible video folders:

```text
/root/video_project/uploads
/root/video_project/upload
```

Expected primary file:

```text
/root/video_project/uploads/video.mp4
```

Validation:

- document which folder exists.
- document whether `video.mp4` exists.
- avoid committing video files into source Git.

## Task 1.5: Prepare Browser-Compatible Demo Video

Owner file:

- create `scripts/prepare_demo_video.sh` if useful
- update `docs/runbooks/v2-phase2.5-validation-runbook.md`

If `/root/video_project/uploads/video.mp4` cannot be opened by the browser, transcode it into a browser-compatible MP4.

Recommended output:

```text
/root/video_project/uploads/demo_classroom_101.mp4
```

Recommended codec/container:

```text
MP4 container
H.264 video
AAC audio when audio exists
yuv420p pixel format
faststart enabled
```

Recommended command:

```bash
ffmpeg -y \
  -i /root/video_project/uploads/video.mp4 \
  -c:v libx264 \
  -preset veryfast \
  -crf 23 \
  -pix_fmt yuv420p \
  -c:a aac \
  -b:a 128k \
  -movflags +faststart \
  /root/video_project/uploads/demo_classroom_101.mp4
```

If the input has no audio stream, use a safe variant that does not fail on missing audio.

Validation:

- browser can open `/uploads/demo_classroom_101.mp4`.
- original `video.mp4` remains untouched.
- generated demo video is not committed into source Git.

## Task 2: Add Static Video Serving

Owner file:

- `cloud_backend/main.py`

Add read-only static serving for the configured video directory.

Recommended behavior:

- read `CLOUD_VIDEO_UPLOAD_DIR`
- default to `/root/video_project/uploads`
- mount existing directory at `/uploads`
- do not fail app startup if the directory does not exist

Validation:

- server can return `/uploads/video.mp4`
- dashboard can use `/uploads/video.mp4`

## Task 3: Bind Demo Video to Detail Fallback

Owner file:

- `cloud_backend/postgres_repository.py`

Enhance `_display_video` fallback behavior:

- if payload has `video.video_url`, use it.
- else if payload has `video_url`, use it.
- else if source has `video_url`, use it.
- else if configured upload dir contains `demo_classroom_101.mp4`, return `/uploads/demo_classroom_101.mp4`.
- else if configured upload dir contains browser-playable `video.mp4`, return `/uploads/video.mp4`.
- else optionally use the latest supported video in upload dir.
- else keep existing pending/missing state.

Supported extensions:

```text
.mp4
.webm
.mov
.ogg
```

Validation:

- demo detail returns `video.status = playable`
- demo detail returns `video.video_url = /uploads/video.mp4` when applicable

## Task 4: Remove Main-Page Debug Clutter

Owner file:

- `cloud_backend/dashboard_v11.py`

Do not keep these sections as always-visible main content:

- `Raw Detail Snapshot`
- old text-only `Teacher Question Events`
- old text-only `Stage Distribution`
- old text-only `Zone Summary`
- old text-only `Timeline Curves`

Recommended:

- move raw JSON/detail snapshot into a collapsed `Debug / Raw Data` details block, or
- hide it behind a small toggle.

Validation:

- main dashboard no longer shows `No result selected` while visual detail is selected.
- old text-only sections do not appear as primary content.

## Task 5: Strengthen First Screen Layout

Owner file:

- `cloud_backend/dashboard_v11.py`

Polish layout so first screen emphasizes:

- platform title
- teacher console marker
- pipeline status
- selected classroom session
- video area
- score cards
- feedback summary
- four chart panels

The result list may remain, but it should feel secondary to the selected classroom analysis.

Validation:

- browser screenshot shows the analysis center, not primarily a table/debug panel.

## Task 6: Improve Chart Readability

Owner file:

- `cloud_backend/dashboard_v11.py`

Improve:

- stage donut chart labels and zero-value handling
- chart empty states
- legends
- card sizing
- sparse/extreme data readability

Validation:

- question-only stage distribution does not create messy overlapping labels.
- empty data does not crash or render confusing charts.

## Task 7: Improve Event and Video Interaction

Owner file:

- `cloud_backend/dashboard_v11.py`

Ensure:

- event list is compact and scrollable.
- event selected state is visible.
- event click jumps playable video to `start_sec`.
- missing video does not break event click.

Validation:

- click a question event and verify video current time changes when video is playable.

## Task 8: Update Validation Script

Owner file:

- `scripts/validate_phase2_5_teacher_analysis_center.sh`

Add checks for:

- `/uploads/video.mp4` is served when present.
- `/uploads/demo_classroom_101.mp4` is served when present.
- detail video status is playable when demo video exists.
- detail video URL points to `/uploads/demo_classroom_101.mp4`, `/uploads/video.mp4`, or discovered upload video.
- dashboard no longer exposes always-visible `No result selected` debug text in main content.

Validation:

- script emits clear markers.

## Task 9: Update Documentation

Update:

- `docs/project-status/v2-phase2.5-teacher-analysis-center.md`
- `docs/runbooks/v2-phase2.5-validation-runbook.md`

Record:

- video folder used
- static video route
- demo video URL
- browser validation result
- remaining risks

## Task 10: Final Regression

Run on server:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
API_BASE_URL="http://127.0.0.1:8011" \
RESULT_ID="cls_20260417_101_001" \
CLASSROOM_ID="classroom_101" \
bash scripts/validate_phase2_5_teacher_analysis_center.sh
```

Optional write regression:

```bash
RUN_UPLOAD_REGRESSION=1 \
API_BASE_URL="http://127.0.0.1:8011" \
RESULT_ID="cls_20260417_101_001" \
CLASSROOM_ID="classroom_101" \
bash scripts/validate_phase2_5_teacher_analysis_center.sh
```

Final report must include:

- modified files
- video static route status
- demo video detail result
- dashboard screenshot notes
- API validation result
- remaining risks
