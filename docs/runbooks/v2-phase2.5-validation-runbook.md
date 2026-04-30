# V2 Phase 2.5 Validation Runbook

## Purpose

Validate the Teacher Classroom Analysis Center after Phase 2.5 implementation.

This runbook is designed for the Linux runtime server where the cloud backend is running in PostgreSQL mode.

## 1. Start Service

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Adjust the port in the commands below if the service uses a port other than `8011`.

```bash
BASE_URL="http://127.0.0.1:8011"
RESULT_ID="cls_20260417_101_001"
CLASSROOM_ID="classroom_101"
```

Phase 2.5 polish uses the runtime video directory below by default:

```bash
VIDEO_UPLOAD_DIR="${CLOUD_VIDEO_UPLOAD_DIR:-/root/video_project/uploads}"
ls -lh "$VIDEO_UPLOAD_DIR/video.mp4"
```

Expected:

- `video.mp4` exists for the competition demo.
- the file is outside `/root/video_project_src` and should not be committed into source control.

## 2. API Validation

Recommended one-command validation:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" \
RESULT_ID="cls_20260417_101_001" \
CLASSROOM_ID="classroom_101" \
bash scripts/validate_phase2_5_teacher_analysis_center.sh
```

Optional upload regression, only when you intentionally want to write another real result:

```bash
RUN_UPLOAD_REGRESSION=1 \
API_BASE_URL="http://127.0.0.1:8011" \
RESULT_ID="cls_20260417_101_001" \
CLASSROOM_ID="classroom_101" \
bash scripts/validate_phase2_5_teacher_analysis_center.sh
```

### Health

```bash
curl -i "$BASE_URL/health"
```

Expected:

- `HTTP/1.1 200`
- body contains `status`

### Recent Results

```bash
curl -i "$BASE_URL/api/teacher/results/recent?limit=10"
curl -i "$BASE_URL/api/teacher/results/recent?classroom_id=$CLASSROOM_ID&limit=10"
curl -i "$BASE_URL/api/teacher/results/recent?status=raw&limit=10"
```

Expected:

- `HTTP/1.1 200`
- response contains `items`
- filtered queries must not fallback to unrelated sample/file records

### Classrooms

```bash
curl -i "$BASE_URL/api/teacher/classrooms"
```

Expected:

- `HTTP/1.1 200`
- response contains `items`

### Detail

```bash
curl -s "$BASE_URL/api/teacher/results/$RESULT_ID" | tee /tmp/phase25-detail.json
```

Expected fields:

```text
result.video
result.summary
result.timeline
result.stage_distribution
result.zones
result.events
result.raw_path
```

Polish video checks:

```bash
curl -I "$BASE_URL/uploads/video.mp4"
python - <<'PY'
import json
with open('/tmp/phase25-detail.json', 'r', encoding='utf-8') as f:
    payload = json.load(f)
video = payload['result']['video']
print('VIDEO_STATUS=' + str(video.get('status')))
print('VIDEO_URL=' + str(video.get('video_url')))
PY
```

Expected when `/root/video_project/uploads/video.mp4` exists:

- `/uploads/video.mp4` returns `200` or a valid static-file response.
- `VIDEO_STATUS=playable`
- `VIDEO_URL=/uploads/video.mp4`

Note:

- Browser playback depends on video codec/container compatibility.
- If `/uploads/video.mp4` is served and detail returns `playable`, but the browser still cannot play it, treat that as a later local-side encoding contract or Phase 2.8 video binding issue, not a Phase 2.5 blocker.

### Missing Detail

```bash
curl -i "$BASE_URL/api/teacher/results/not-existing-result"
```

Expected:

- `HTTP/1.1 404`

### Status Update

```bash
printf '{"status":"reviewed"}' > /tmp/phase25-status-reviewed.json
curl -i -XPATCH "$BASE_URL/api/teacher/results/$RESULT_ID/status" \
  -H 'Content-Type:application/json' \
  -d @/tmp/phase25-status-reviewed.json
```

Expected:

- `HTTP/1.1 200`
- returned result status is `reviewed`

Invalid status:

```bash
printf '{"status":"bad_status"}' > /tmp/phase25-status-invalid.json
curl -i -XPATCH "$BASE_URL/api/teacher/results/$RESULT_ID/status" \
  -H 'Content-Type:application/json' \
  -d @/tmp/phase25-status-invalid.json
```

Expected:

- `HTTP/1.1 400`

## 3. Dashboard HTML Marker Validation

```bash
curl -s "$BASE_URL/dashboard?classroom_id=$CLASSROOM_ID&limit=10" > /tmp/phase25-dashboard.html
```

Expected markers:

```bash
grep -q "Teacher Console" /tmp/phase25-dashboard.html && echo TEACHER_CONSOLE_MARKER=true
grep -q "Capture" /tmp/phase25-dashboard.html && echo DATA_PIPELINE_MARKER=true
grep -q "video" /tmp/phase25-dashboard.html && echo VIDEO_AREA_MARKER=true
grep -q "attention" /tmp/phase25-dashboard.html && echo ATTENTION_TIMELINE_MARKER=true
grep -q "stage" /tmp/phase25-dashboard.html && echo STAGE_DISTRIBUTION_MARKER=true
grep -q "zone" /tmp/phase25-dashboard.html && echo ZONE_PERFORMANCE_MARKER=true
grep -q "event" /tmp/phase25-dashboard.html && echo EVENT_DISTRIBUTION_MARKER=true
! grep -q "No result selected" /tmp/phase25-dashboard.html && echo NO_RESULT_SELECTED_CONFLICT_HIDDEN=true
! grep -q "Raw Detail Snapshot" /tmp/phase25-dashboard.html && echo RAW_SNAPSHOT_NOT_PRIMARY=true
grep -q 'data-marker="debug-raw-data"' /tmp/phase25-dashboard.html && echo DEBUG_RAW_COLLAPSED_MARKER=true
```

The final validation script may use stronger, stable marker ids instead of loose text checks.

## 4. Browser Validation

Open:

```text
http://<server-ip>:8011/dashboard?classroom_id=classroom_101&limit=10
```

Expected:

- page loads.
- teacher console marker is visible.
- data pipeline status is visible.
- filters are visible.
- result list is visible.
- selecting a result loads detail.
- video area is visible.
- demo video player is visible when `/root/video_project/uploads/video.mp4` exists.
- no-video fallback is graceful when no playable URL exists.
- attention/activity timeline chart is visible.
- stage distribution chart is visible.
- zone performance chart is visible.
- event distribution chart is visible.
- key event list is visible.
- teaching feedback summary is visible.
- reviewed/archived buttons work.
- old raw/text sections are collapsed under `Debug / Raw Data`.
- the page does not show an always-visible `No result selected` raw snapshot conflict.
- if the video file is not browser-compatible, the page should still remain usable and charts/events/feedback should render.

Event-video behavior:

- if video is playable, clicking an event with `start_sec` jumps the player.
- if video is missing or pending, clicking an event does not break the page.

## 5. Phase 1/2 Regression

Run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
bash scripts/upload_real_result.sh
bash scripts/validate_postgres.sh
curl -i "$BASE_URL/api/latest-interaction-result"
curl -i "$BASE_URL/api/recent-interaction-results?limit=5"
```

Expected:

- upload returns success.
- raw JSON path is returned.
- PostgreSQL contains the uploaded analysis result.
- latest/recent legacy APIs still return `200`.

## 6. Final Report Requirements

The executor should report:

- modified files
- API validation results
- dashboard marker validation results
- browser validation notes
- Phase 1/2 regression results
- unresolved risks

## 7. Phase 2.5 Freeze Criteria

Phase 2.5 can be frozen when:

- static Python compile passes.
- `scripts/validate_phase2_5_teacher_analysis_center.sh` passes the API and dashboard marker checks on the Linux server.
- Phase 1/2 read regression markers pass.
- upload regression is either explicitly run with `RUN_UPLOAD_REGRESSION=1` or documented as skipped because it writes new data.
- browser manual validation confirms the dashboard focuses on the classroom analysis center and debug/raw sections are collapsed.

Do not block freeze only because the provided demo MP4 cannot play in a browser, as long as `/uploads/video.mp4` is statically served and the detail API exposes the expected video URL. Codec compatibility is deferred to the local video output contract or Phase 2.8.
