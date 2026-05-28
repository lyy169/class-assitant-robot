# V3 Phase 3.5 Cloud Video Playback Integration Status

## Status

Phase 3.5a runtime check preparation is complete.

This phase only adds documentation and a read-only runtime check script. It does not start services, restart services, modify systemd, modify the database, or commit git changes.

## Goal

Prepare the cloud runtime for classroom video playback and local analysis result integration:

- Local analyzer generates V1.1 JSON with `video.video_url`.
- Demo MP4 is placed under `/root/video_project/uploads`.
- JSON is uploaded through `POST /api/interaction-results`.
- `/dashboard?result_id=<result_id>` displays video plus analysis.
- `/teacher/reports?result_id=<result_id>` displays report feedback.
- `/admin/ingestion` displays ingestion and video playability status.

## Non-Goals

- No new upload API.
- No database migration.
- No dashboard rewrite.
- No local analyzer core algorithm change.
- No Raspberry Pi change.
- No default use of a 576 MB full raw video for the competition demo.

## Prepared Files

- `docs/specs/v3-phase3.5-cloud-video-playback-integration-spec.md`
- `docs/tasks/v3-phase3.5-cloud-video-playback-integration-tasks.md`
- `docs/runbooks/v3-phase3.5-cloud-runtime-check-runbook.md`
- `docs/project-status/v3-phase3.5-cloud-video-playback-integration.md`
- `docs/prompts/v3-phase3.5-cloud-runtime-check-cli-prompt.md`
- `scripts/check_phase3_5_cloud_runtime.sh`

## Runtime Check Script

Script path:

```text
scripts/check_phase3_5_cloud_runtime.sh
```

The script checks:

- Project directory.
- PostgreSQL runtime env file.
- Runtime env file.
- Service example file.
- Non-sensitive runtime config.
- Database type only.
- Ports `8011` and `8010`.
- `uvicorn cloud_backend.main:app` process.
- `classroom-cloud-backend.service` state.
- `/root/video_project/uploads`.
- Video file counts.
- `video.mp4`.
- HTTP reachability if port `8011` is listening.

## Validation

Static script validation command:

```bash
bash -n scripts/check_phase3_5_cloud_runtime.sh
```

Result:

```text
passed
```

Notes:

- `bash -n scripts/check_phase3_5_cloud_runtime.sh` passed.
- The script body was not executed during Phase 3.5a preparation.
- No service start/restart command was run.

## Operator Notes

If `PHASE35A_CLOUD_RUNTIME_READY=false` because the service is not running, the user may manually start the cloud PostgreSQL runtime:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

The runtime check script must not execute the startup command automatically.

## Current Recommendation

For Phase 3.5 local-to-cloud demo:

- Place demo video at `/root/video_project/uploads/phase35_demo_classroom_101.mp4`.
- Set JSON field `video.video_url` to `/uploads/phase35_demo_classroom_101.mp4`.
- Upload JSON through the existing `POST /api/interaction-results`.
- Verify `/dashboard?result_id=<result_id>` and `/teacher/reports?result_id=<result_id>`.
