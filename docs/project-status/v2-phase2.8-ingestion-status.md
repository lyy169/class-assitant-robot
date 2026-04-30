# V2 Phase 2.8 Three-Side Ingestion Status

## 1. Status

Cloud/server-side implementation completed in SSHFS workspace on 2026-04-29.

This phase implements the cloud visibility layer only:

```text
Raspberry Pi Capture -> Local Analysis -> Cloud Storage -> Teacher Feedback
```

Raspberry Pi capture-side and local YOLO/analyzer-side runtime work are not implemented in this repository. Their contracts remain documented and must be validated on their target machines.

## 2. Modified Files

- `cloud_backend/postgres_repository.py`
- `cloud_backend/auth.py`
- `cloud_backend/main.py`
- `cloud_backend/admin_pages.py`
- `scripts/validate_phase2_8_ingestion_status.sh`
- `docs/project-status/v2-phase2.8-ingestion-status.md`
- `docs/runbooks/v2-phase2.8-three-side-validation-runbook.md`

## 3. Added API

### `GET /api/admin/ingestion`

Parameters:

- `classroom_id`
- `device_id`
- `source_host`
- `days`
- `limit`

Returns:

- `success`
- `filters`
- `overview`
- `pipeline`
- `devices`
- `recent_ingestions`
- `video_summary`
- `validation_hints`

The API is read-only and uses demo admin context consistent with Phase 2.7.

## 4. Added Page

### `GET /admin/ingestion`

The page includes:

- Admin Console navigation
- three-side ingestion hero
- visual pipeline:
  `Raspberry Pi Capture -> Local Analysis -> Cloud Storage -> Teacher Feedback`
- metric cards
- filters for classroom, device, source host, days, and limit
- device / analyzer status list
- recent ingestion records
- video readiness summary
- validation / data quality hints

The existing admin navigation now includes `Ingestion Status`.

## 5. Data Inference Rules

No database tables or columns were added.

No raw JSON structure was modified.

Cloud inference uses existing data:

- `analysis_results.payload_json`
- `analysis_results.classroom_id`
- `analysis_results.analysis_id`
- `analysis_results.created_at`
- existing indexed fields

Device id priority:

1. `payload_json.capture.device_id`
2. `payload_json.video.device_id`
3. `payload_json.source.source_host`
4. `unknown`

Device name priority:

1. `payload_json.capture.device_name`
2. inferred `device_id`
3. `unknown device`

Source host priority:

1. `payload_json.source.source_host`
2. `payload_json.upload.source_host`
3. `unknown`

Capture time priority:

1. `payload_json.capture.captured_at`
2. `payload_json.time.start_time`
3. `analysis_results.created_at`

Upload time priority:

1. `payload_json.upload.uploaded_at`
2. `analysis_results.created_at`
3. `payload_json.time.generated_at`

Video status:

- `video.video_url` exists -> `playable`
- `video.raw_video_path` or `capture.video_path` exists -> `pending`
- otherwise -> `missing`

Freshness:

- latest upload within 24 hours -> `online`
- within 7 days -> `stale`
- older than 7 days -> `offline`
- no parseable time -> `unknown`

These are inferred statuses, not true heartbeat statuses.

## 6. Compatibility

Older payloads without `source`, `capture`, `video`, or `upload` are supported.

Missing metadata produces:

- `unknown`
- `missing`
- `pending`
- validation hints

The page and API remain available even when metadata is partial.

## 7. Validation Script

Added:

```bash
scripts/validate_phase2_8_ingestion_status.sh
```

The script checks:

- `/admin/ingestion`
- `/api/admin/ingestion`
- required ingestion API keys
- ingestion page markers
- Phase 2.7 admin regression
- Phase 2.6 teacher regression
- Phase 2.5 dashboard regression
- Phase 1/2 latest/recent API regression

## 8. Static Validation Result

Executed in SSHFS workspace:

```powershell
$env:PYTHONPYCACHEPREFIX="$env:TEMP\codex_pycache"
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py
```

Result:

- `PASS`

Additional HTML generation check:

- `/admin/ingestion` HTML generated successfully
- required ingestion markers exist
- no residual `{{` or `${{` JavaScript template escapes

## 9. Server Runtime Validation Commands

Restart service:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
ENV_FILE=/root/video_project_src/cloud_backend/.env.postgres.runtime bash scripts/deploy_cloud_backend.sh
```

Run cloud Phase 2.8 validation:

```bash
cd /root/video_project_src
source /root/venv/bin/activate
API_BASE_URL="http://127.0.0.1:8011" RESULT_ID="cls_20260417_101_001" CLASSROOM_ID="classroom_101" bash scripts/validate_phase2_8_ingestion_status.sh
```

## 10. Browser Validation URL

Open:

```text
http://<server-ip>:8011/admin/ingestion
```

Expected:

- Admin Console navigation is visible
- pipeline visual section is visible
- metric cards render
- filters are visible
- device/analyzer status list renders or shows safe empty state
- recent ingestion records render or show safe empty state
- video readiness summary is visible
- validation hints are visible
- records can open `/dashboard?result_id=...`

## 11. Regression Notes

Preserved:

- Phase 1 upload/read flow
- Phase 2 teacher APIs
- Phase 2.5 `/dashboard`
- Phase 2.6 `/teacher` and `/teacher/results`
- Phase 2.7 `/admin`, `/admin/classrooms`, `/admin/teachers`, `/admin/results`
- raw JSON persistence
- PostgreSQL schema boundaries

## 12. Remaining Work / Risks

- Runtime validation must be run on the Linux server.
- Raspberry Pi metadata generation must be validated on the Raspberry Pi device.
- Local analyzer metadata merge and video format capability audit must be validated in the local analyzer project.
- Freshness is inferred from upload/created time and is not a real device heartbeat.
- Old payloads will show partial metadata hints until the local analyzer starts uploading `capture`, `video`, and `upload` blocks.
