# V3 Phase 3.6a Spec: Local Auto Upload To Cloud

## Phase Goal

Phase 3.6a closes the cloud-side upload gap between the local analyzer and cloud playback. The cloud must accept a single multipart package containing:

- `result_json`: classroom analysis JSON, preferably as a file field.
- `video_file`: classroom video file.

The cloud saves the video, injects `video.video_url`, then reuses the existing raw JSON persistence and PostgreSQL indexing path.

## Non-Goals

This phase does not:

- Add a database migration.
- Replace or break `POST /api/interaction-results`.
- Rewrite dashboard.
- Modify the local analyzer algorithm.
- Modify Raspberry Pi code.
- Solve final competition full-classroom data quality.
- Treat 50 SAV clips as one complete classroom dashboard.
- Use the 1-minute demo clip as the final competition sample.

## New Endpoint

```text
POST /api/interaction-results/with-video
Content-Type: multipart/form-data
```

Fields:

- `result_json`: JSON file field. A string field is also accepted by the implementation.
- `video_file`: `.mp4`, `.webm`, `.mov`, or `.ogg` video file.

Response fields:

- `success`
- `request_id`
- `saved_path`
- `video_url`
- `video_path`
- `analysis_id`

## Compatibility

The existing JSON-only endpoint remains available:

```text
POST /api/interaction-results
```

The new endpoint reuses:

- `InteractionResultPayload` validation.
- Business field validation for `classroom_id` and `source.source_host`.
- raw JSON save under `cloud_backend/data/raw/YYYY-MM-DD/`.
- active query repository save, including PostgreSQL when `CLOUD_DB_BACKEND=postgres`.
- existing `/uploads` static route.
- existing teacher detail API and `/dashboard` video rendering.

## Video Handling

Allowed suffixes:

```text
.mp4 .webm .mov .ogg
```

Video filename handling:

- Do not trust client paths.
- Normalize the original filename.
- Prefix with `analysis_id`.
- Do not overwrite existing files; append a short UUID when needed.
- Save under `settings.video_upload_dir`, normally `/root/video_project/uploads`.

Injected payload field:

```json
{
  "video": {
    "video_url": "/uploads/<safe_video_filename>"
  }
}
```

Existing `video.duration_seconds` is preserved if already present. The cloud does not infer duration.

## Smoke Test Boundary

The Phase 3.6 validation script can reuse the Phase 3.5 one-minute package:

```text
cloud_backend/data/phase35_local_to_cloud_package/phase35_local_imported_sav_full_classroom_20200908_17
```

This package is only an endpoint smoke test. It is not the final competition dashboard sample.

Phase 3.7 must use a same-source full-classroom video and same-source full analysis JSON for final dashboard acceptance.
