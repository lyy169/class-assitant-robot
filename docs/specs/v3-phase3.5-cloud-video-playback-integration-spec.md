# V3 Phase 3.5 Spec: Cloud Video Playback Integration

## 1. Phase Goal

Phase 3.5 prepares cloud-side runtime compatibility for classroom video playback and local analysis result integration.

The target demonstration flow is:

1. Local analyzer generates a V1.1 classroom analysis JSON with `video.video_url`.
2. A demo MP4 is placed under `/root/video_project/uploads`.
3. The JSON is uploaded through the existing `POST /api/interaction-results`.
4. `/dashboard?result_id=<result_id>` displays the classroom video and analysis result together.
5. `/teacher/reports?result_id=<result_id>` displays the teaching report.
6. `/admin/ingestion` shows ingestion status and video playability signals.

## 2. Non-Goals

This phase does not:

- Add a new upload API.
- Run a database migration.
- Rewrite `/dashboard`.
- Modify the local analyzer core algorithm.
- Modify the Raspberry Pi side.
- Use a 576 MB full raw video as the default competition demo asset.
- Change authentication, role, or permission models.

## 3. Reused Cloud Capabilities

Phase 3.5 reuses existing cloud capabilities:

- `POST /api/interaction-results`
- `/dashboard`
- `/teacher/results`
- `/teacher/reports`
- `/admin/ingestion`
- `/uploads`
- `/root/video_project/uploads`

Existing code support already identified:

- `dashboard_v11.py` includes a video player with `controls`.
- `postgres_repository.py` extracts `video.video_url`, top-level `video_url`, and `source.video_url`.
- `schemas_v11.py` allows extra JSON fields.
- `main.py` mounts `/uploads` when the runtime video directory exists.

## 4. Runtime Configuration

The formal cloud demonstration runtime should use:

```text
cloud_backend/.env.postgres.runtime
```

Expected non-sensitive runtime shape:

```text
CLOUD_PORT=8011
CLOUD_DB_BACKEND=postgres
CLOUD_VIDEO_UPLOAD_DIR=/root/video_project/uploads
```

Database URLs, passwords, tokens, and API keys must not be printed in validation logs.

## 5. Runtime Check Scope

Phase 3.5a prepares a manual runtime check script:

```text
scripts/check_phase3_5_cloud_runtime.sh
```

The script is read-only. It may inspect files, ports, processes, systemd state, HTTP status codes, and upload directory contents.

It must not:

- Start services.
- Restart services.
- Modify systemd units.
- Modify databases.
- Print secrets.
- Commit git changes.

## 6. Acceptance Criteria

Cloud runtime is considered ready when:

- Project directory exists.
- `cloud_backend/.env.postgres.runtime` exists.
- Port `8011` is listening.
- `/health` returns OK.
- `/api/recent-interaction-results?limit=1` is reachable.
- `/root/video_project/uploads` exists.
- `/uploads/video.mp4` or another uploaded video is reachable.
- `/dashboard` is reachable.

Pages protected by login may return `302` to `/login`; that still counts as route reachable for this runtime check.

