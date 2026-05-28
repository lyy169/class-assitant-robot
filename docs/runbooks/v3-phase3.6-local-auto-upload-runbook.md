# V3 Phase 3.6a Runbook: Local Auto Upload To Cloud

## Purpose

Use this runbook to validate the cloud-side multipart endpoint:

```text
POST /api/interaction-results/with-video
```

The endpoint accepts a video file and analysis JSON in one request, saves the video, injects `video.video_url`, and reuses the existing raw JSON and PostgreSQL persistence path.

## Preconditions

- Cloud backend code has been updated.
- The running service has been restarted manually by the operator after code deployment.
- PostgreSQL runtime config is used for formal validation.
- Phase 3.5 one-minute staging package exists:

```text
/root/video_project_src/cloud_backend/data/phase35_local_to_cloud_package/phase35_local_imported_sav_full_classroom_20200908_17
```

Required files:

```text
phase35_cloud_upload_result.json
phase35_demo_classroom_101.mp4
package.json
```

## Important Boundary

The Phase 3.5 one-minute video is only an interface smoke test. It is not the final full classroom sample.

The final competition dashboard sample must be produced in Phase 3.7 with:

- Same-source full classroom video.
- Same-source full classroom analysis JSON.
- No artificial composition of 50 SAV clips as one complete classroom.

## Static Validation

Run before runtime validation:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
python -B -m py_compile cloud_backend/main.py
bash -n scripts/validate_phase3_6_with_video_upload.sh
```

## Runtime Validation

After manually restarting the cloud backend service, run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_6_with_video_upload.sh
```

If `CLOUD_REQUIRE_API_KEY=true`, provide the API key through the environment without printing it:

```bash
CLOUD_API_KEY="<redacted>" API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_6_with_video_upload.sh
```

## Expected Markers

```text
PHASE36_WITH_VIDEO_ENDPOINT_PRESENT=true
PHASE36_HEALTH_OK=true
PHASE36_STAGING_PACKAGE_PRESENT=true
PHASE36_MULTIPART_UPLOAD_HTTP_OK=true
PHASE36_MULTIPART_UPLOAD_SUCCESS=true
PHASE36_CLOUD_VIDEO_SAVED=true
PHASE36_CLOUD_RAW_JSON_SAVED=true
PHASE36_RESPONSE_VIDEO_URL_PRESENT=true
PHASE36_STATIC_VIDEO_OK=true
PHASE36_TEACHER_DETAIL_OK=true
PHASE36_DETAIL_VIDEO_URL_MATCH=true
PHASE36_DASHBOARD_REACHABLE=true
PHASE36_NO_MANUAL_VIDEO_COPY_REQUIRED=true
PHASE36_DEMO_CLIP_NOT_FINAL_SAMPLE=true
PHASE36_LOCAL_AUTO_UPLOAD_CLOUD_READY=true
```

## Manual Browser Check

Use the `analysis_id` returned by the upload response. For the smoke package it should be:

```text
phase35_local_imported_sav_full_classroom_20200908_17
```

Open:

```text
http://<server>:8011/dashboard?result_id=phase35_local_imported_sav_full_classroom_20200908_17
```

Verify:

- The video area renders.
- The video URL is under `/uploads/`.
- The page remains a smoke test and is not treated as the final competition dashboard sample.
