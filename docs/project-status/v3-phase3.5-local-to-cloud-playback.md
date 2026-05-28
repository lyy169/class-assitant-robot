# V3 Phase 3.5c Local-to-Cloud Playback Status

## Status

Runtime send and cloud playback validation passed.

Closeout state as of 2026-05-08:

- Staging package copied by operator: yes.
- Video copied to runtime upload directory by send script: yes.
- JSON posted to `POST /api/interaction-results` by send script: yes.
- Cloud detail API exposes playable video metadata: yes.
- Dashboard video area is present: yes.
- Service started or restarted by this phase tooling: no.
- Systemd modified: no.
- Database schema modified: no.
- Git commit executed: no.

## Goal

Validate that the local analyzer export package can be sent to the cloud runtime and displayed as classroom video plus analysis in `/dashboard`.

## Prepared Files

- `docs/runbooks/v3-phase3.5-local-to-cloud-playback-runbook.md`
- `docs/project-status/v3-phase3.5-local-to-cloud-playback.md`
- `docs/prompts/v3-phase3.5-local-to-cloud-playback-cli-prompt.md`
- `scripts/phase3_5_send_local_package_to_cloud.sh`
- `scripts/validate_phase3_5_local_to_cloud_playback.sh`

## Package Source

Local package path:

```text
C:\Users\lyy\Desktop\gradu\phase35_cloud_upload_package\phase35_local_imported_sav_full_classroom_20200908_17
```

Expected cloud staging directory:

```text
/root/video_project_src/cloud_backend/data/phase35_local_to_cloud_package/phase35_local_imported_sav_full_classroom_20200908_17
```

The staging directory is runtime data and is not part of git.

## Runtime Video Target

```text
/root/video_project/uploads/phase35_demo_classroom_101.mp4
```

Expected JSON video URL:

```text
/uploads/phase35_demo_classroom_101.mp4
```

Expected result id:

```text
phase35_local_imported_sav_full_classroom_20200908_17
```

## Scripts

Send script:

```text
scripts/phase3_5_send_local_package_to_cloud.sh
```

Validation script:

```text
scripts/validate_phase3_5_local_to_cloud_playback.sh
```

## Manual Steps Completed

1. The local package was copied to the cloud staging directory.
2. The send script was run:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
bash scripts/phase3_5_send_local_package_to_cloud.sh
```

3. Playback validation was run:

```bash
bash scripts/validate_phase3_5_local_to_cloud_playback.sh
```

## Runtime Validation

Send script result:

```text
PHASE35C_STAGING_DIR_PRESENT=true
PHASE35C_PACKAGE_JSON_PRESENT=true
PHASE35C_DEMO_VIDEO_PRESENT=true
PHASE35C_UPLOAD_JSON_PRESENT=true
PHASE35C_UPLOAD_JSON_VIDEO_URL_OK=true
PHASE35C_UPLOAD_JSON_SOURCE_MARKED=true
PHASE35C_UPLOAD_JSON_NOT_PI_CAPTURE=true
PHASE35C_UPLOAD_JSON_NOT_OWN_CAPTURE=true
PHASE35C_VIDEO_TARGET_DIR_PRESENT=true
PHASE35C_VIDEO_COPIED=true
PHASE35C_VIDEO_EXISTING_REUSED=false
PHASE35C_VIDEO_URL_STATIC_OK=true
PHASE35C_CLOUD_UPLOAD_HTTP_OK=true
PHASE35C_CLOUD_UPLOAD_SUCCESS=true
PHASE35C_CLOUD_UPLOAD_SAVED_PATH_PRESENT=true
PHASE35C_LOCAL_TO_CLOUD_SEND_OK=true
```

Playback validation result:

```text
PHASE35C_HEALTH_OK=true
PHASE35C_STATIC_VIDEO_OK=true
PHASE35C_TEACHER_LOGIN_OK=true
PHASE35C_TEACHER_DETAIL_OK=true
PHASE35C_DETAIL_VIDEO_PLAYABLE=true
PHASE35C_DETAIL_VIDEO_URL_OK=true
PHASE35C_DASHBOARD_OK=true
PHASE35C_DASHBOARD_VIDEO_AREA_PRESENT=true
PHASE35C_REPORTS_OK=true
PHASE35C_ADMIN_LOGIN_OK=true
PHASE35C_ADMIN_INGESTION_PAGE_OK=true
PHASE35C_ADMIN_INGESTION_API_OK=true
PHASE35C_ADMIN_VIDEO_STATUS_VISIBLE=true
PHASE35C_CLOUD_VIDEO_PLAYBACK_INTEGRATION_OK=true
```

## Browser Acceptance

Operator confirmed the related video can be viewed in classroom analysis:

```text
http://<server>:8011/dashboard?result_id=phase35_local_imported_sav_full_classroom_20200908_17
```

## Known Issue / Follow-up

The classroom analysis page can display the related video, but some analysis data appears questionable during manual review. This is recorded as a data quality or field-mapping follow-up and is not treated as a Phase 3.5c playback integration blocker.

Recommended next phase scope:

- Inspect the uploaded raw JSON against the teacher detail API response.
- Verify whether questionable values originate from the local analyzer export, cloud compatibility mapping, or dashboard display formatting.
- Avoid changing the playback integration path unless the investigation proves video metadata mapping is involved.

## Boundaries

This phase does not:

- Add a new API.
- Run a database migration.
- Rewrite dashboard.
- Modify the local analyzer core algorithm.
- Modify Raspberry Pi code.
- Mark SAV as Raspberry Pi capture or self-captured footage.
- Commit git changes.

## Static Validation

Commands:

```bash
bash -n scripts/phase3_5_send_local_package_to_cloud.sh
bash -n scripts/validate_phase3_5_local_to_cloud_playback.sh
```

Result:

```text
passed
```

Notes:

- `bash -n scripts/phase3_5_send_local_package_to_cloud.sh`: passed.
- `bash -n scripts/validate_phase3_5_local_to_cloud_playback.sh`: passed.
- Text whitespace scan for Phase 3.5c files: passed.
- Forbidden action scan for service restart, git add/commit, and database DDL/DML in Phase 3.5c scripts: no matches.
