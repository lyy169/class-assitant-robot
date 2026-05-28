# V3 Phase 3.5 Tasks: Cloud Video Playback Integration Runtime Check

## 1. Documentation

- [ ] Add Phase 3.5 cloud video playback integration spec.
- [ ] Add Phase 3.5 runtime check task list.
- [ ] Add Phase 3.5 runtime check runbook.
- [ ] Add Phase 3.5 project status document.
- [ ] Add CLI prompt document if `docs/prompts` exists.

## 2. Runtime Check Script

- [ ] Add `scripts/check_phase3_5_cloud_runtime.sh`.
- [ ] Confirm the script is read-only.
- [ ] Confirm the script does not start or restart services.
- [ ] Confirm the script does not modify systemd.
- [ ] Confirm the script does not modify the database.
- [ ] Confirm the script does not print secrets or full database URLs.

## 3. Script Checks

- [ ] Check current directory and project presence.
- [ ] Check runtime env files and service example presence.
- [ ] Print only non-sensitive runtime settings.
- [ ] Print only database type: `postgres`, `sqlite`, or `unknown`.
- [ ] Check ports `8011` and `8010`.
- [ ] Check for `uvicorn cloud_backend.main:app`.
- [ ] Check `classroom-cloud-backend.service` state if systemd is available.
- [ ] Check `/root/video_project/uploads`.
- [ ] Count `mp4`, `webm`, `mov`, and `ogg` files.
- [ ] Check `video.mp4`.
- [ ] If `8011` is listening, check `/health`, recent API, `/uploads/video.mp4`, `/dashboard`, `/teacher/results`, `/teacher/reports`, and `/admin/ingestion`.

## 4. Markers

The script must output:

```text
PHASE35A_CLOUD_PROJECT_PRESENT=true/false
PHASE35A_POSTGRES_RUNTIME_ENV_PRESENT=true/false
PHASE35A_RUNTIME_ENV_PRESENT=true/false
PHASE35A_SERVICE_EXAMPLE_PRESENT=true/false
PHASE35A_DB_BACKEND=postgres/sqlite/file/unknown
PHASE35A_PORT_8011_LISTENING=true/false
PHASE35A_PORT_8010_LISTENING=true/false
PHASE35A_SERVICE_PROCESS_PRESENT=true/false
PHASE35A_SYSTEMD_SERVICE_STATE=active/inactive/failed/missing/unknown
PHASE35A_UPLOAD_DIR_PRESENT=true/false
PHASE35A_UPLOAD_VIDEO_PRESENT=true/false
PHASE35A_UPLOAD_VIDEO_COUNT=<number>
PHASE35A_HEALTH_OK=true/false
PHASE35A_RECENT_API_OK=true/false
PHASE35A_UPLOADS_STATIC_OK=true/false
PHASE35A_DASHBOARD_REACHABLE=true/false
PHASE35A_TEACHER_RESULTS_REACHABLE=true/false
PHASE35A_TEACHER_REPORTS_REACHABLE=true/false
PHASE35A_ADMIN_INGESTION_REACHABLE=true/false
PHASE35A_CLOUD_RUNTIME_READY=true/false
```

## 5. Validation

- [ ] Run:

```bash
bash -n scripts/check_phase3_5_cloud_runtime.sh
```

- [ ] Do not run commands that start or restart the service during Phase 3.5a preparation.

## 6. Git Boundary

- [ ] Do not run `git add .`.
- [ ] Do not commit in this phase unless separately requested.
- [ ] Do not stage or commit historical dirty files.

