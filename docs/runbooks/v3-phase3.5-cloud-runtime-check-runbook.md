# V3 Phase 3.5 Runbook: Cloud Runtime Check

## Purpose

This runbook prepares manual cloud runtime verification for Phase 3.5 classroom video playback and local analysis result integration.

The runtime check is intentionally read-only. It does not start, restart, or reconfigure services.

## What Phase 3.5 Reuses

- `POST /api/interaction-results`
- `/dashboard`
- `/teacher/results`
- `/teacher/reports`
- `/admin/ingestion`
- `/uploads`
- `/root/video_project/uploads`

The intended local-to-cloud demo path is:

1. Put a demo MP4 under `/root/video_project/uploads`.
2. Upload V1.1 JSON through `POST /api/interaction-results`.
3. Set `video.video_url` to a value such as `/uploads/phase35_demo_classroom_101.mp4`.
4. Open `/dashboard?result_id=<result_id>`.
5. Open `/teacher/reports?result_id=<result_id>`.
6. Check `/admin/ingestion`.

## Run the Read-Only Check

On the cloud server:

```bash
cd /root/video_project_src
bash scripts/check_phase3_5_cloud_runtime.sh
```

The script prints markers such as:

```text
PHASE35A_CLOUD_PROJECT_PRESENT=true
PHASE35A_PORT_8011_LISTENING=true
PHASE35A_HEALTH_OK=true
PHASE35A_UPLOADS_STATIC_OK=true
PHASE35A_CLOUD_RUNTIME_READY=true
```

## If Runtime Is Not Ready

If `PHASE35A_CLOUD_RUNTIME_READY=false` because the service is not running, the user may manually start the PostgreSQL runtime service in a separate terminal:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Do not put this command inside the check script. It is a manual operator action.

Expected startup log shape:

```text
CLOUD_PORT=8011
CLOUD_DB_BACKEND=postgres
Uvicorn running on http://0.0.0.0:8011
Mounted video uploads directory at /uploads: /root/video_project/uploads
```

## Optional Systemd Guidance

If a systemd service is later used, verify that it loads the PostgreSQL runtime environment rather than the SQLite/default runtime environment.

Recommended manual checks:

```bash
systemctl status classroom-cloud-backend.service --no-pager
journalctl -u classroom-cloud-backend.service -n 20 --no-pager
```

The runtime check script may inspect systemd state but must not run `systemctl start`, `systemctl restart`, or edit unit files.

## Demo Video Naming Guidance

Recommended demo MP4 path:

```text
/root/video_project/uploads/phase35_demo_classroom_101.mp4
```

Recommended JSON field:

```json
{
  "video": {
    "video_url": "/uploads/phase35_demo_classroom_101.mp4"
  }
}
```

Do not use a 576 MB full raw video as the default competition demo asset. Prefer a short, browser-playable MP4 clip for fast page loading.

## Boundaries

This phase does not:

- Add a new upload API.
- Run database migrations.
- Rewrite dashboard pages.
- Modify local analyzer core algorithms.
- Modify Raspberry Pi code.
- Start or restart services automatically.
- Print secrets or full database URLs.

