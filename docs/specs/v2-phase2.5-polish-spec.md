# V2 Phase 2.5 Polish Spec: Competition Demo Readiness

## 1. Purpose

Phase 2.5 core implementation has delivered the teacher classroom analysis center, unified detail structure, four classroom charts, video fallback area, and validation script.

The current page is functionally usable, but screenshots show it still has a debug/workbench feel:

- old text-only sections remain visible below the new analysis center
- raw detail snapshot can show `No result selected` while the visual detail is already selected
- first screen does not yet strongly emphasize the competition story
- video playback needs a stable demo path

This polish phase prepares the page for competition presentation without expanding scope into Phase 2.6 or Phase 3.

## 2. Goals

Polish goals:

- make `/dashboard` look like a competition-ready teacher analysis product
- keep the page focused on one classroom session
- make video playback work with the demo video copied to the runtime video folder
- remove or fold away debug-looking old text sections
- improve chart readability and empty/extreme data handling
- keep existing APIs and Phase 1/2 behavior stable

## 3. Non-Goals

Do not implement:

- full login/role routing
- admin console
- new video upload API
- video transcoding
- video database tables
- device management
- independent Vue/Vite frontend rewrite
- AI report generation
- raw JSON schema changes

## 4. Demo Video Decision

The user has copied a demo file named:

```text
video.mp4
```

into the running project video folder under `video_project`.

The expected runtime default should be:

```text
/root/video_project/uploads/video.mp4
```

The SSHFS workspace currently shows:

```text
X:\video_project\uploads
```

Implementation must prefer the plural directory:

```text
/root/video_project/uploads
```

For robustness, the executor may also check a singular fallback:

```text
/root/video_project/upload
```

but the canonical path for this project should be `uploads`.

## 5. Static Video Exposure

Phase 2.5 polish should not add a full video upload API.

Instead, expose a read-only static video route from the FastAPI cloud backend.

Recommended behavior:

```text
CLOUD_VIDEO_UPLOAD_DIR defaults to /root/video_project/uploads
FastAPI mounts it at /uploads when the directory exists
video.mp4 becomes available as /uploads/video.mp4
```

The dashboard should use:

```json
"video_url": "/uploads/video.mp4"
```

for the demo result when no explicit video URL exists in `payload_json`.

## 5.1 Demo Video Browser Compatibility

If the copied demo video cannot be opened directly in the browser, treat it as a media encoding/container compatibility issue.

For competition demo stability, prepare a browser-compatible MP4:

```text
container: MP4
video codec: H.264
audio codec: AAC
pixel format: yuv420p
fast start: enabled
```

Recommended output file:

```text
/root/video_project/uploads/demo_classroom_101.mp4
```

Recommended `video_url`:

```text
/uploads/demo_classroom_101.mp4
```

The original copied file should be preserved. Transcoding should be an explicit offline preparation step, not a per-request backend operation.

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

If the input has no audio stream, the executor should use an ffmpeg variant that does not fail on missing audio.

## 6. Demo Video Binding

For competition demonstration, the selected demo result should become playable when:

- no explicit `payload.video.video_url` exists
- no explicit `payload.video_url` exists
- a demo video exists at the configured video upload directory

Recommended fallback mapping:

```text
if payload has video_url:
  use payload video_url
else if /uploads/demo_classroom_101.mp4 exists:
  use /uploads/demo_classroom_101.mp4 as demo video_url
else if /uploads/video.mp4 exists and is browser playable:
  use /uploads/video.mp4 as demo video_url
else if latest video file exists in upload dir:
  use latest video file as demo video_url
else:
  keep pending/missing state
```

This fallback is for demo readiness and should be documented clearly. It must not modify raw JSON.

## 7. Page Polish Requirements

### 7.1 Hide Debug-Looking Old Sections

The following old sections should not remain as always-visible main content:

- `Raw Detail Snapshot`
- old `Teacher Question Events`
- old text-only `Stage Distribution`
- old text-only `Zone Summary`
- old text-only `Timeline Curves`

Recommended handling:

- move them into a collapsed `Debug / Raw Data` details panel, or
- hide them behind a small toggle for developer validation.

They should not compete with the main classroom analysis center.

### 7.2 First Screen Priority

The first screen should prioritize:

- platform title and teacher console marker
- Capture -> Local Analysis -> Cloud pipeline
- selected classroom video or video status
- key classroom score cards
- teaching feedback summary
- four classroom analysis charts

The result list should remain available, but it should not dominate the visual hierarchy.

### 7.3 Selected Detail Consistency

There must not be conflicting states where the chart area shows a selected result while another visible panel says `No result selected`.

If raw detail is kept:

- it must update when selected detail updates, or
- it must be hidden/collapsed by default.

### 7.4 Chart Readability

Charts should handle extreme and sparse data:

- hide or de-emphasize zero-value stage slices
- avoid overlapping pie/donut labels
- keep legends readable
- show empty states when data arrays are empty
- keep chart cards visually balanced

### 7.5 Event List Readability

The event list should be compact, scrollable, and visually connected to video playback.

Each event should show:

- event id
- event type
- start time
- concise text

Clicking an event should:

- jump the video when playable
- highlight the event even when video is missing

## 8. Validation Criteria

Server validation:

- `/uploads/video.mp4` returns `200` or valid partial/static response
- `GET /api/teacher/results/{result_id}` returns `video.status=playable` for demo result when demo file exists
- `video.video_url` is `/uploads/video.mp4` or a valid discovered video URL
- `/dashboard` returns `200`
- dashboard HTML contains video area marker
- dashboard no longer shows always-visible `No result selected` raw panel under selected charts

Browser validation:

- dashboard loads
- video player is visible for demo result
- video can play
- clicking an event jumps to event time
- old raw/text sections are collapsed or hidden
- four charts remain visible and readable
- reviewed/archive actions still work

Regression:

- existing teacher APIs still work
- existing Phase 1 upload/read APIs still work
- raw JSON is unchanged
- no new core database table is required

## 9. Future Work

Formal video upload from the local analysis side should be designed later.

Future phase may add:

- `POST /api/videos/upload`
- `video_assets` table
- session-video binding
- device upload status
- administrator video/data ingestion monitoring

This polish phase only proves the demo playback path and improves presentation quality.
